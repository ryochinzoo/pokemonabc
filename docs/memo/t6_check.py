#!/usr/bin/env python3
"""T6 機械照合: writeup 本文の数値が、その段落が引く台帳行(claims-ledger.md)に載っているかを突合する.

playbook §7 T6「主張台帳にない数値・N/CIなしの数値・族内測定由来の数値を成果物に書いたら停止」の機械化。
ラベル(探索的/弱確証)の断定形チェックは機械化しない(writeup-draft.md 105-114 のチェックリストで人手)。

使い方:
  python3 docs/memo/t6_check.py [writeup.md] [--ledger claims-ledger.md] [--limit 1960] [--strict] [--quiet]
  本文範囲 = 「## Measure Before」の見出し行から、最初の "---\\n---"(本文外の区切り)の直前まで。
出力: 段落ごとに 数値 / 引用# / MATCH|UNMATCHED|UNCITED。Fig 番号の連番と make_figures.CAPTIONS の整合。
語数 = 公開版(= [#N] 台帳タグを剥がした全文、見出し・表・Fig参照込み)の split() 数。Kaggle の数え方が未観測なので保守側。
exit 1: 語数 > limit、Fig 不整合、または --strict で UNMATCHED > 0。
"""
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NUM = re.compile(r"(?<![0-9.])[+\-−–±]?\d[\d,]*(?:\.\d+)?(?![0-9.])")  # 台帳は日本語が数値に隣接するので ASCII のみ除外
CITE = re.compile(r"\s*\[#(\d+)((?:,\s*(?:#\d+|Fig\.\s*\d+))*)\]")  # 先頭の空白ごと剥がす(公開版の語数を正しく数える)
CITE_INNER = re.compile(r"#(\d+)")
FIG = re.compile(r"Fig\.\s*(\d+)")
# 本文で使う定数・非測定値(台帳行に無くてよいもの)。増やすときは理由を書く
ALLOW = {
    "120", "10,000", "1e9", "1.2", "250",       # #27 のコード定数(マージン/サイド項/終局)とその比
    "60", "2", "3", "4", "5", "6", "7", "8", "10", "12", "1",  # 枚数・回数・例数・節番号
    "2,000", "1,000", "96",                      # 語数上限 / 直近1,000譜 / 安全床96%
    "700", "799", "700–799",                     # 帯
    "20", "21", "14",                            # 小N(台帳#2/#3 内に併記)
}


def load_ledger(path):
    rows = {}
    for ln in Path(path).read_text().splitlines():
        m = re.match(r"^\|\s*\**(\d+)\**\s*\|", ln)  # 先行研究表は | **8** | 形式
        if m:
            rows.setdefault(m.group(1), "")
            rows[m.group(1)] += " " + ln
    return rows


def norm(tok):
    t = tok.replace("−", "-").replace("–", "-").replace("±", "").replace(",", "").lstrip("+")
    return t.lstrip("-")


def body_of(text):
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("## ") and not l.startswith("## v"))  # 本文タイトル = 最初の "## "(チェンジログは "> ")
    end = len(lines)
    for i in range(start, len(lines) - 1):
        if lines[i].strip() == "---" and lines[i + 1].strip() == "---":
            end = i
            break
    return "\n".join(lines[start:end]).strip()


def main():
    argv = sys.argv[1:]
    args = [a for i, a in enumerate(argv)
            if not a.startswith("--") and not (i > 0 and argv[i - 1] in ("--ledger", "--limit", "--prose-limit"))]
    wp = Path(args[0]) if args else HERE / "writeup-v1-fulldraft.md"
    ledger = HERE / "claims-ledger.md"
    if "--ledger" in sys.argv:
        ledger = Path(sys.argv[sys.argv.index("--ledger") + 1])
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 1960
    # 2026-09-09 運営回答(Strategy discussion 738657): 表・図の中の文字は語数外。地の文(表行・見出しを除く)にも上限を掛ける
    prose_limit = int(sys.argv[sys.argv.index("--prose-limit") + 1]) if "--prose-limit" in sys.argv else None
    strict, quiet = "--strict" in sys.argv, "--quiet" in sys.argv
    body = body_of(wp.read_text())
    rows = load_ledger(ledger)
    ledger_norm = {k: {norm(t) for t in NUM.findall(v)} for k, v in rows.items()}
    paras = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    n_match = n_un = n_uncited = 0
    for pi, p in enumerate(paras, 1):
        if p.lstrip().startswith("#"):
            continue
        cited = set()
        for m in CITE.finditer(p):
            cited.add(m.group(1))
            cited |= set(CITE_INNER.findall(m.group(2)))
        text_wo_cites = CITE.sub("", p)
        text_wo_cites = FIG.sub("", text_wo_cites)
        nums = [t for t in NUM.findall(text_wo_cites)]
        for t in nums:
            n = norm(t)
            if t in ALLOW or n in ALLOW or re.fullmatch(r"20\d\d", n):
                continue
            if not cited:
                n_uncited += 1
                if not quiet:
                    print(f"¶{pi:02d} UNCITED   {t:>10s}   (no [#N] in paragraph)  …{p.strip()[:60]}")
                continue
            hit = [c for c in cited if n in ledger_norm.get(c, set())]
            if hit:
                n_match += 1
            else:
                n_un += 1
                if not quiet:
                    print(f"¶{pi:02d} UNMATCHED {t:>10s}   cited #{','.join(sorted(cited))}  …{p.strip()[:60]}")
    figs = sorted({int(x) for x in FIG.findall(body)})
    fig_ok = True
    try:
        spec = importlib.util.spec_from_file_location("mf", HERE / "figures" / "make_figures.py")
        mf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mf)
        cap_nums = sorted(n for _, n, _ in mf.CAPTIONS)
        missing = [n for n in figs if n not in cap_nums]
        contiguous = figs == list(range(1, len(figs) + 1)) if figs else True
        fig_ok = not missing and contiguous
        print(f"Fig refs in body: {figs}  captions: {cap_nums}  {'OK' if fig_ok else 'MISMATCH'}"
              + (f"  missing caption for {missing}" if missing else "") + ("" if contiguous else "  (not contiguous from 1)"))
    except Exception as e:
        print("Fig check skipped:", e)
    words_all = len(body.split())
    # 公開版 = [#N] タグを剥がした全文(見出し・表・Fig参照は残る)。表の罫線トークン("|", "|---|")はどの数え方でも語ではないので除く
    words_pub = len([t for t in CITE.sub("", body).split() if not re.fullmatch(r"\|[-|:]*", t)])
    prose = "\n".join(l for l in body.splitlines() if not l.startswith("|") and not l.startswith("#"))
    words_prose = len(CITE.sub("", prose).split())
    print(f"words: publish(no [#N] tags)={words_pub} (limit {limit})  raw={words_all}  prose-only={words_prose}"
          + (f" (prose limit {prose_limit})" if prose_limit else ""))
    print(f"numbers: MATCH={n_match} UNMATCHED={n_un} UNCITED={n_uncited}")
    bad = words_pub > limit or not fig_ok or (strict and n_un > 0) or (prose_limit is not None and words_prose > prose_limit)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
