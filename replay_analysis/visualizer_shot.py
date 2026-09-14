#!/usr/bin/env python3
"""公式ビジュアライザ(ptcgvis.heroz.jp)の盤面を、手元の replay から指定ステップで PNG に撮る(標準ライブラリ+ headless Chrome)。

仕組み(2026-09-09 解読): Kaggle の Game History の「Open Visualizer」ボタンは、replay の `steps[0][0].visualize`
(各ステップの盤面配列)に `players[P].ramainingTime` と `[0].ps = TeamNames` を足したものを `json` フィールドで
`https://ptcgvis.heroz.jp/Visualizer/Replay/<EpisodeId>/<playerIndex>` に POST しているだけ。返ってくる HTML は
replay を埋め込んだ1枚もの(+ /js/gameVisualizer.js)。それを保存し、<base> を足して file:// から開き、
CDP(標準ライブラリの WebSocket 実装)で `#slideindex` を指定ステップに合わせて Page.captureScreenshot する。
Claude in Chrome 拡張のサイト権限は不要。運営回答(Strategy discussion 738657): ビジュアライザのスクショは Writeup に使ってよい。

使い方:
  python3 replay_analysis/visualizer_shot.py <replay.json> <playerIndex 0/1> <step 1..N> <out.png> [--win 1180,930] [--wait 14] [--after 8]
  step は 1 始まり(ビジュアライザの表示番号)。replay の visualize[k] は step k+1。
  例: python3 replay_analysis/visualizer_shot.py replay_analysis/eps55558557/ep102267456.json 1 98 docs/memo/figures/png/fig_board_t10.png
"""
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
VIS = "https://ptcgvis.heroz.jp"


def build_payload(rep):
    steps = rep["steps"]
    vis = steps[0][0].get("visualize")
    if not vis:
        raise SystemExit("この replay には steps[0][0].visualize が無い(ビジュアライザ用データ非対応)")
    for e in range(min(len(vis), len(steps))):
        for p in range(2):
            try:
                vis[e]["current"]["players"][p]["ramainingTime"] = steps[e][p]["observation"].get("remainingOverageTime")
            except Exception:
                pass
    vis[0]["ps"] = (rep.get("info") or {}).get("TeamNames") or ["Player 0", "Player 1"]
    return vis


def fetch_visualizer_html(payload, ep_id, player_index):
    data = urllib.parse.urlencode({"json": json.dumps(payload)}).encode()
    req = urllib.request.Request(f"{VIS}/Visualizer/Replay/{ep_id}/{player_index}", data=data,
                                 headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def localize(html, step):
    html = html.replace("<head>", f'<head><base href="{VIS}/">', 1)
    inject = f"""
<style>.leftColumn,.rightColumn,.footer,.leftFooter{{display:none !important}} canvas{{left:0 !important}}</style>
<script>window.__step={step};</script>
"""
    return html.replace("</body>", inject + "</body>", 1)


class CDP:
    """最小の WebSocket クライアント(RFC 6455、クライアント→サーバはマスク必須)."""

    def __init__(self, ws_url):
        host_port, path = ws_url[len("ws://"):].split("/", 1)
        host, port = host_port.split(":")
        self.sock = socket.create_connection((host, int(port)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET /{path} HTTP/1.1\r\nHost: {host_port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += self.sock.recv(4096)
        if b" 101 " not in resp.split(b"\r\n")[0]:
            raise RuntimeError(resp[:200])
        self.buf = bytearray(resp.split(b"\r\n\r\n", 1)[1])
        self.msg_id = 0

    def _send(self, obj):
        data = json.dumps(obj).encode()
        mask = os.urandom(4)
        n = len(data)
        hdr = bytearray([0x81])
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack(">Q", n)
        self.sock.sendall(bytes(hdr) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _need(self, k):
        while len(self.buf) < k:
            chunk = self.sock.recv(1 << 16)
            if not chunk:
                raise RuntimeError("socket closed")
            self.buf.extend(chunk)

    def _recv_frame(self):
        self._need(2)
        op, n = self.buf[0] & 0x0F, self.buf[1] & 0x7F
        off = 2
        if n == 126:
            self._need(4)
            n, off = struct.unpack(">H", bytes(self.buf[2:4]))[0], 4
        elif n == 127:
            self._need(10)
            n, off = struct.unpack(">Q", bytes(self.buf[2:10]))[0], 10
        self._need(off + n)
        payload = bytes(self.buf[off:off + n])
        del self.buf[:off + n]
        return op, payload

    def call(self, method, params=None, timeout=120):
        self.msg_id += 1
        mid = self.msg_id
        self._send({"id": mid, "method": method, "params": params or {}})
        frags = b""
        t0 = time.time()
        while time.time() - t0 < timeout:
            op, payload = self._recv_frame()
            if op in (0x1, 0x0):
                frags += payload
                try:
                    m = json.loads(frags.decode())
                except Exception:
                    continue
                frags = b""
                if m.get("id") == mid:
                    return m.get("result", m)
        raise TimeoutError(method)


def screenshot(local_html, step, out, win="1180,930", wait_load=14, wait_after=8, port=9333):
    profile = tempfile.mkdtemp(prefix="ptcgvis-chrome-")
    proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--disable-web-security",
                             f"--user-data-dir={profile}", f"--remote-debugging-port={port}", f"--window-size={win}",
                             "--force-device-scale-factor=2", "--no-first-run", "--no-default-browser-check", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        targets = []
        for _ in range(100):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2))
                if any(t.get("type") == "page" for t in targets):
                    break
            except Exception:
                pass
            time.sleep(0.2)
        page = next(t for t in targets if t.get("type") == "page")
        cdp = CDP(page["webSocketDebuggerUrl"])
        cdp.call("Page.enable")
        cdp.call("Page.navigate", {"url": "file://" + os.path.abspath(local_html)})
        time.sleep(wait_load)
        r = cdp.call("Runtime.evaluate", {"expression": f"""(() => {{ const s = document.getElementById('slideindex'); if (!s) return 'no slideindex';
            s.value = '{step}'; s.dispatchEvent(new Event('change', {{bubbles: true}})); return 'set ' + s.value + ' / ' + s.max; }})()""",
            "returnByValue": True})
        print("step:", r.get("result", {}).get("value"))
        time.sleep(wait_after)
        shot = cdp.call("Page.captureScreenshot", {"format": "png"})
        with open(out, "wb") as f:
            f.write(base64.b64decode(shot["data"]))
        print("wrote", out, os.path.getsize(out), "bytes")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = {k: sys.argv[sys.argv.index(k) + 1] for k in ("--win", "--wait", "--after") if k in sys.argv}
    replay, player_index, step, out = args[0], int(args[1]), int(args[2]), args[3]
    rep = json.load(open(replay))
    ep_id = (rep.get("info") or {}).get("EpisodeId") or os.path.basename(replay)[2:-5]
    payload = build_payload(rep)
    html = fetch_visualizer_html(payload, ep_id, player_index)
    local = os.path.join(tempfile.gettempdir(), f"ptcgvis_{ep_id}_{player_index}.html")
    with open(local, "w", encoding="utf-8") as f:
        f.write(localize(html, step))
    print(f"visualizer html {len(html)} bytes → {local}; steps available = {len(payload)}")
    screenshot(local, step, out, win=opt.get("--win", "1180,930"), wait_load=float(opt.get("--wait", 14)), wait_after=float(opt.get("--after", 8)))


if __name__ == "__main__":
    main()
