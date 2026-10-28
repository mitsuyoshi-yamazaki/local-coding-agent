"""ループと REPL が使うもの。起動のときに1度作り、会話の間は変えない。"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TextIO

from local_coding_agent.model.chat import ChatModel
from local_coding_agent.permissions.policy import Permissions
from local_coding_agent.tools.tool import Tool
from local_coding_agent.trace.writer import TraceSink


@dataclass(frozen=True)
class Session:
    """ループと REPL が使うもの。テストでは偽物に差し替える。"""

    model: ChatModel
    # 起動のときに組み立てた system prompt
    system: str
    # モデルに渡し、ループが実行する道具
    tools: tuple[Tool, ...]
    # 道具が相対パスを解く基点。起動したディレクトリ
    cwd: Path
    # 1行を受ける。依頼と、実行の前の問いの答えに使う
    read_line: Callable[[str], str]
    output: TextIO
    trace: TraceSink
    # 時間を測る時計（秒）
    clock: Callable[[], float]
    # 発言に付ける、今の時刻（時差つき）
    now: Callable[[], datetime]
    # 道具の呼び出しを、通す・問う・拒むのどれにするかを決める、モードと規則
    permissions: Permissions
    # 推論の文を表示するか（--show-thinking）。表示しなくても、走行の記録には残す
    show_thinking: bool = False
