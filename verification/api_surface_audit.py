#!/usr/bin/env python3
"""API面の数え上げ監査 (2026-08-02、D62 項目⓪)。

**なぜ**: 2026-08-02 の先行研究監査で、`State`/`PlayerState` の20フィールド中12個を
一度も読んでいないことが判明した(supporterPlayed / energyAttached / firstPlayer /
状態異常5種 など)。しかしそれは**291件の公開ノートブックを読んで偶然見つかった12個**であって、
**数え上げの結果ではない**。「291件読んで見つけた穴より、リストを1回作って見つかる穴の方が
多いかもしれない」(2026-08-02 の議論)。

**何をするか**: `cg/api.py` の全 dataclass の全フィールドと、全 IntEnum の全メンバを列挙し、
対象エージェントの `main.py` が**それぞれを一度でも参照しているか**を機械的に判定する。

**判定の限界(必ず併記)**: 判定は**識別子の grep**であり、意味的な使用を保証しない。
- 偽陽性: 別の意味で同名の識別子を使っている場合(例: 変数名 `turn`)
- 偽陰性: `getattr(o, name)` のような動的アクセス
よって出力は「**未参照の候補**」であり、「未使用の証明」ではない。**人が1件ずつ見て判断する。**

使い方(デッキディレクトリから):
    cd src/input/datasets/decks/starmie-aggro
    python3 ../../../../../verification/api_surface_audit.py
    python3 ../../../../../verification/api_surface_audit.py --agent main.py --api cg/api.py
"""
import argparse
import os
import re
import sys

# 数え上げから除く自明なもの(内部/ダンダー/変換ヘルパ)
SKIP = {"__init__", "__post_init__", "to_dict", "from_dict"}


def parse_api(path: str):
    """dataclass のフィールドと IntEnum のメンバを、定義順に抽出する。"""
    src = open(path, encoding="utf-8").read()
    lines = src.split("\n")
    blocks, cur = [], None
    for ln in lines:
        # `class X(IntEnum):` と `class X:`(dataclass)の両方を拾う。
        # ※ 初版は前者しか拾えず dataclass を全て取りこぼしていた(2026-08-02 自己訂正)。
        m = re.match(r"^class (\w+)(?:\((\w+)\))?\s*:", ln)
        if m:
            cur = {"name": m.group(1), "base": m.group(2) or "dataclass", "items": []}
            blocks.append(cur)
            continue
        if re.match(r"^\S", ln) and not ln.startswith("@"):
            if not re.match(r"^class ", ln):
                cur = None
        if cur is None:
            continue
        if cur["base"] == "IntEnum":
            mm = re.match(r"^\s{4}([A-Z][A-Z0-9_]*)\s*=", ln)
        else:
            mm = re.match(r"^\s{4}(\w+)\s*:", ln)
        if mm and mm.group(1) not in SKIP:
            cur["items"].append(mm.group(1))
    return [b for b in blocks if b["items"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="main.py")
    ap.add_argument("--api", default="cg/api.py")
    ap.add_argument("--only-unused", action="store_true")
    args = ap.parse_args()

    for p in (args.agent, args.api):
        if not os.path.exists(p):
            sys.exit(f"見つからない: {p}(デッキディレクトリから実行すること)")

    agent_src = open(args.agent, encoding="utf-8").read()
    # コメント行は参照とみなさない(「# supporterPlayed は未対応」等を拾わないため)
    code_only = "\n".join(
        re.sub(r"#.*$", "", ln) for ln in agent_src.split("\n")
    )

    blocks = parse_api(args.api)
    tot = used = 0
    report = []
    for b in blocks:
        rows = []
        for it in b["items"]:
            hits = len(re.findall(r"\b%s\b" % re.escape(it), code_only))
            tot += 1
            if hits:
                used += 1
            rows.append((it, hits))
        report.append((b, rows))

    kind = lambda b: "Enum " if b["base"] == "IntEnum" else "data "
    print(f"API面の数え上げ — agent={args.agent} / api={args.api}")
    print(f"定義: {len(blocks)} クラス / {tot} 項目   参照あり {used} ({100*used/tot:.0f}%)"
          f"   **未参照 {tot-used}**\n")

    for b, rows in report:
        un = [r for r in rows if r[1] == 0]
        if args.only_unused and not un:
            continue
        head = f"{kind(b)}{b['name']}  ({len(rows)-len(un)}/{len(rows)} 参照)"
        print(head)
        print("-" * len(head))
        for it, hits in rows:
            if args.only_unused and hits:
                continue
            mark = f"✓ {hits:>3}" if hits else "✗   —"
            print(f"  {mark}  {it}")
        print()

    print("注意: 判定は識別子の grep であり、意味的な使用を保証しない。")
    print("      出力は『未参照の候補』であって『未使用の証明』ではない。1件ずつ人が見ること。")


if __name__ == "__main__":
    main()
