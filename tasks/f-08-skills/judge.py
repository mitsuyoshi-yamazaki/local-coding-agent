"""「インチとセンチメートルの変換を足して」の課題の判定。全て通れば終了コード 0、どれかが通らなければ 1。

使い方（リポジトリの根で）: .venv/bin/python tasks/f-08-skills/judge.py <写しのディレクトリ>

スキル add-conversion の手順の4つに合わせて、次を見る。

1. テストが全て通る
2. convert(1, "inch", "cm") が 2.54 で、逆向きも求まる
3. test_convert.py に inch の場合が足されている
4. CHANGELOG.md の「## 未リリース」の節に、inch と cm を含む行が足されている

4 は、スキルを読まなければ、頼まれていないのでモデルがしないことである。
"""

import subprocess
import sys
from pathlib import Path

TIMEOUT_SECONDS = 30
TESTS = ["-m", "unittest", "discover", "-s", "."]
CONVERSION = (
    "import math, convert; "
    "assert math.isclose(convert.convert(1, 'inch', 'cm'), 2.54); "
    "assert math.isclose(convert.convert(2.54, 'cm', 'inch'), 1)"
)
UNRELEASED = "## 未リリース"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write(f"使い方: {argv[0]} <写しのディレクトリ>\n")
        return 2
    project = Path(argv[1])
    checks = (
        ("テストが全て通る", _passes(project, TESTS)),
        ("inch と cm を変換できる", _passes(project, ["-c", CONVERSION])),
        ("テストに inch の場合がある", "inch" in _read(project / "test_convert.py")),
        ("変更の記録に足した", _logged(_read(project / "CHANGELOG.md"))),
    )
    for name, passed in checks:
        sys.stdout.write(f"{'通った' if passed else '通らない'}: {name}\n")
    return 0 if all(passed for _, passed in checks) else 1


def _passes(project: Path, arguments: list[str]) -> bool:
    """写しのディレクトリで Python を走らせ、終了コードが 0 か。終わらなければ通らない。"""
    command = [sys.executable, *arguments]
    try:
        completed = subprocess.run(
            command, cwd=project, check=False, timeout=TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"{TIMEOUT_SECONDS} 秒で終わらなかった: {arguments}\n")
        return False
    return completed.returncode == 0


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return ""


def _logged(changelog: str) -> bool:
    """「## 未リリース」から次の「## 」の見出しまでに、inch と cm を含む行があるか。"""
    lines = changelog.splitlines()
    if UNRELEASED not in lines:
        return False
    start = lines.index(UNRELEASED) + 1
    section = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        section.append(line)
    return any("inch" in line and "cm" in line for line in section)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
