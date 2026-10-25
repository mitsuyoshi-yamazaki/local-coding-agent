"""写しのテストを、時間を限って走らせる。通れば終了コード 0、通らない・終わらなければ 1。

使い方（リポジトリの根で）: .venv/bin/python tasks/f-05-run-command/judge.py <写しのディレクトリ>

words の終わらないテストが直っていなくても、判定が止まらないように、時間を限る。
"""

import subprocess
import sys

TIMEOUT_SECONDS = 30


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write(f"使い方: {argv[0]} <写しのディレクトリ>\n")
        return 2
    command = [sys.executable, "-m", "unittest", "discover", "-s", argv[1]]
    try:
        completed = subprocess.run(command, check=False, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"\n{TIMEOUT_SECONDS} 秒で終わらなかった\n")
        return 1
    return 0 if completed.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
