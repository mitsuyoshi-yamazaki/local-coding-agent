"""道具の形。

道具は、モデルに渡す定義と、種類（読む・編集・コマンド）と、実行する関数からなる。実行する
関数は、入力と作業ディレクトリを受け、結果の文を返す。誤りは ToolError で知らせる。

編集とコマンドの道具は、実行の前に人に見せる文（下見。ファイルを書く道具なら差分）を作る関数も
持てる。下見の関数は、実行する関数と同じ入力を受け、何も変えずに文を返す。

道具は、許可の規則と照らす文字列（パスかコマンド）を、入力から取り出す関数も持てる。
道具は、結果の文から、画面に出す結果の1行を作る関数も持てる。持たなければ、行数を出す。
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from local_coding_agent.model.chat import ToolDefinition

type ToolInput = Mapping[str, object]
# 道具の種類。許可のモードは、種類ごとに通すか問うかを決める（permissions/policy.py）
type ToolKind = Literal["read", "edit", "command"]


class ToolError(Exception):
    """道具が誤りを返す。文は、誤りの結果としてモデルに渡る。"""


@dataclass(frozen=True)
class Tool:
    """道具1つ。"""

    definition: ToolDefinition
    # 種類。読む道具（read）は何も変えない
    kind: ToolKind
    # 実行する関数。入力は、実行の前に定義と照らしてある（tools/input_check.py）
    run: Callable[[ToolInput, Path], str]
    # 実行の前に人に見せる文を作る関数。無ければ None。誤りは ToolError で知らせる
    preview: Callable[[ToolInput, Path], str] | None = None
    # 結果の文から、画面に出す結果の1行を作る関数。無ければ None。誤りの結果には使わない
    summary: Callable[[str], str] | None = None
    # 許可の規則と照らす文字列を入力から取り出す関数。ファイルの道具はパス（解く前のもの）、
    # コマンドの道具はコマンドを返す。無ければ None（型を持つ規則に合わない）
    target: Callable[[ToolInput], str] | None = None

    @property
    def name(self) -> str:
        return self.definition.name


def find_tool(tools: Sequence[Tool], name: str) -> Tool | None:
    """名前で道具を探す。無ければ None。"""
    return next((tool for tool in tools if tool.name == name), None)


def resolve(cwd: Path, path: str) -> Path:
    """道具に渡されたパスを解く。相対パスは作業ディレクトリから、絶対パスはそのまま。"""
    return cwd / path
