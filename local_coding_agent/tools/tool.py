"""道具の形。

道具は、モデルに渡す定義と、変更を伴うかの印と、実行する関数からなる。実行する関数は、
入力と作業ディレクトリを受け、結果の文を返す。誤りは ToolError で知らせる。
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from local_coding_agent.model.chat import ToolDefinition

type ToolInput = Mapping[str, object]


class ToolError(Exception):
    """道具が誤りを返す。文は、誤りの結果としてモデルに渡る。"""


@dataclass(frozen=True)
class Tool:
    """道具1つ。"""

    definition: ToolDefinition
    # 変更を伴うか。True なら、実行の前に人に確かめる
    changes: bool
    # 実行する関数。入力は、実行の前に定義と照らしてある（tools/input_check.py）
    run: Callable[[ToolInput, Path], str]

    @property
    def name(self) -> str:
        return self.definition.name


def find_tool(tools: Sequence[Tool], name: str) -> Tool | None:
    """名前で道具を探す。無ければ None。"""
    return next((tool for tool in tools if tool.name == name), None)


def resolve(cwd: Path, path: str) -> Path:
    """道具に渡されたパスを解く。相対パスは作業ディレクトリから、絶対パスはそのまま。"""
    return cwd / path
