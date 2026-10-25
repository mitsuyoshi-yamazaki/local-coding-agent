"""会話の形。Claude の Messages API に揃え、発言を塊（content block）の並びで持つ。

使う塊は、推論（thinking）・本文（text）・道具の呼び出し（tool_use）・道具の結果（tool_result）
である。

利用者の発言は、メタデータとして送った時刻（sent_at）を持つ。Messages API の発言には無い欄で、
モデルは文しか読めないので、送る直前に本文の前へ文として入れる（metadata_text）。
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

type Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class ThinkingBlock:
    """推論の塊。モデルの発言の先頭に入る。次の要求で、モデルに戻す。"""

    thinking: str
    type: Literal["thinking"] = "thinking"


@dataclass(frozen=True)
class TextBlock:
    """本文の塊。"""

    text: str
    type: Literal["text"] = "text"


@dataclass(frozen=True)
class ToolUseBlock:
    """道具の呼び出しの塊。モデルの発言に入る。"""

    # 呼び出しの id。結果の塊が、どの呼び出しの結果かをこれで示す
    id: str
    name: str
    input: Mapping[str, object]
    type: Literal["tool_use"] = "tool_use"


@dataclass(frozen=True)
class ToolResultBlock:
    """道具の結果の塊。Messages API と同じく、利用者の発言に入る。"""

    tool_use_id: str
    content: str
    # 道具が誤りを返した・入力が定義に合わない・利用者が拒んだ、のとき True
    is_error: bool = False
    type: Literal["tool_result"] = "tool_result"


type ContentBlock = ThinkingBlock | TextBlock | ToolUseBlock | ToolResultBlock


@dataclass(frozen=True)
class Message:
    """1つの発言。役割と、塊の並びと、メタデータ。"""

    role: Role
    content: tuple[ContentBlock, ...]
    # 利用者が送った時刻。モデルの発言と、道具の結果の発言では None
    sent_at: datetime | None = None


def user_text(text: str, sent_at: datetime | None = None) -> Message:
    """本文だけの、利用者の発言を作る。"""
    return Message(role="user", content=(TextBlock(text),), sent_at=sent_at)


def assistant_text(text: str) -> Message:
    """本文だけの、モデルの発言を作る。"""
    return Message(role="assistant", content=(TextBlock(text),))


def assistant_message(
    text: str, tool_uses: Sequence[ToolUseBlock], thinking: str = ""
) -> Message:
    """推論と本文と道具の呼び出しからなる、モデルの発言を作る。塊は、推論・本文・呼び出しの順。

    推論が空なら、推論の塊を入れない。呼び出しがあって本文が空なら、本文の塊を入れない。
    推論も呼び出しも無ければ assistant_text と同じ。
    """
    thought = (ThinkingBlock(thinking),) if thinking else ()
    head = (TextBlock(text),) if text or not tool_uses else ()
    return Message(role="assistant", content=(*thought, *head, *tool_uses))


def tool_results(results: Sequence[ToolResultBlock]) -> Message:
    """1回の応答の呼び出しの結果を、まとめて1つの利用者の発言にする。"""
    return Message(role="user", content=tuple(results))


def text_of(message: Message) -> str:
    """発言の本文の塊を、つないで1つの文字列にする。"""
    return "".join(
        block.text for block in message.content if isinstance(block, TextBlock)
    )


def metadata_text(message: Message) -> str:
    """発言のメタデータを、本文の前に入れる文にする。メタデータが無ければ空の文字列。"""
    if message.sent_at is None:
        return ""
    return f"<metadata>\n送った時刻: {_minutes(message.sent_at)}\n</metadata>\n"


def _minutes(moment: datetime) -> str:
    """分までの時刻と時差。例: 2026-10-24 15:30 (+09:00)"""
    offset = moment.strftime("%z")  # 例: +0900。時差を持たない時刻では空
    suffix = f" ({offset[:3]}:{offset[3:5]})" if offset else ""
    return f"{moment:%Y-%m-%d %H:%M}{suffix}"
