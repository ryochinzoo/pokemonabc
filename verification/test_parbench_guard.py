#!/usr/bin/env python3
"""parbench の並列許可ガードの回帰テスト（CPU を使わない静的検査のみ）。

2026-07-25 の実バグ: 検出正規表現が `import time as _time` → `_time.time()` を
取り逃し、**steel_agent.py を並列で 40 戦走らせてしまった**。
D51 の「規則ではなく構造で守る」を名乗る以上、ガード自体に回帰テストが要る。

    python3 verification/test_parbench_guard.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from parbench import split_even, uses_wallclock  # noqa: E402

# 壁時計を読む＝並列禁止でなければならないもの
MUST_REFUSE = ["reference/steel_agent.py"]

# CEW の 4 成分＝並列可でなければならないもの（D51 で全数監査済み）
MUST_ALLOW = [
    "reference/official_lucario_agent.py",
    "reference/tomato_archaludon_agent.py",
    "reference/official_dragapult_agent.py",
    "reference/official_abomasnow_agent.py",
]

fails = []

for rel in MUST_REFUSE:
    p = os.path.join(HERE, rel)
    if not uses_wallclock(p):
        fails.append(f"検出漏れ（危険）: {rel} は壁時計依存だが並列可と判定された")

for rel in MUST_ALLOW:
    p = os.path.join(HERE, rel)
    if uses_wallclock(p):
        fails.append(f"偽陽性: {rel} は壁時計非依存のはずが並列不可と判定された")

# 存在しないファイルは安全側（＝禁止）に倒れること
if not uses_wallclock(os.path.join(HERE, "reference/__does_not_exist__.py")):
    fails.append("読めないファイルが並列可と判定された（安全側に倒れていない）")

# チャンクは必ず偶数（run_series の i%2 席交換の均衡）
for n, k in ((3200, 8), (600, 7), (40, 4), (2, 8)):
    chunks = split_even(n, k)
    if sum(chunks) != n:
        fails.append(f"split_even({n},{k}) の合計が {sum(chunks)} で N と一致しない")
    if any(c % 2 for c in chunks):
        fails.append(f"split_even({n},{k}) が奇数チャンクを返した: {chunks}")

try:
    split_even(601, 8)
    fails.append("奇数 N が拒否されなかった")
except ValueError:
    pass

if fails:
    for f in fails:
        print(f"FAIL: {f}")
    print(f"GUARD_TEST=FAIL ({len(fails)}件)")
    sys.exit(1)

print(f"検査: 拒否{len(MUST_REFUSE)}件 / 許可{len(MUST_ALLOW)}件 / 分割4件 + 奇数N拒否")
print("GUARD_TEST=PASS")
