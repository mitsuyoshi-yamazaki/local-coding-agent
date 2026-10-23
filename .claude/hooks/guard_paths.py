#!/usr/bin/env python3
"""リポジトリの外のファイルを編集する道具の呼び出しを拒む、PreToolUse の hook。

Claude Code が道具の呼び出しを JSON で標準入力に渡す。編集の対象がリポジトリの外なら、
拒む判断を JSON で標準出力に返す。何も出さなければ、通常の許可の判断に任せる。
"""

import json
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
PATH_KEYS = ("file_path", "notebook_path")


def outside_paths(tool_input: dict[str, object]) -> list[Path]:
    paths = []
    for key in PATH_KEYS:
        value = tool_input.get(key)
        if not isinstance(value, str):
            continue
        target = (REPOSITORY / value).resolve()
        if target != REPOSITORY and REPOSITORY not in target.parents:
            paths.append(target)
    return paths


def main() -> None:
    event = json.load(sys.stdin)
    paths = outside_paths(event.get("tool_input", {}))
    if not paths:
        return
    decision = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"リポジトリの外のファイルは編集しない: {', '.join(map(str, paths))}"
            ),
        }
    }
    json.dump(decision, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
