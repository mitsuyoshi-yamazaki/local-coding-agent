"""走行の記録を JSONL（1行に1つの JSON）で書き出す。

起動ごとに1つのファイルを作り、要求と応答を1件1行で足していく。
"""

import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Protocol


class TraceSink(Protocol):
    """走行の記録の書き出し先。"""

    def write(self, record: Mapping[str, object]) -> None:
        """1件を書く。"""
        ...


def trace_path(directory: Path, started: datetime) -> Path:
    """起動の時刻から、記録のファイルの場所を決める（例: traces/20261024-153012.jsonl）。"""
    return directory / f"{started.strftime('%Y%m%d-%H%M%S')}.jsonl"


class TraceWriter:
    """記録を、ファイルの末尾に1件1行で足す。"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, record: Mapping[str, object]) -> None:
        line = {"time": _now(), **record}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(line, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")
