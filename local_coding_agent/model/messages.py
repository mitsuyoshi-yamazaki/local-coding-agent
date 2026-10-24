"""会話の形。Claude の Messages API に揃え、発言を塊（content block）の並びで持つ。

使う塊は本文（text）だけである。thinking・tool_use・tool_result の塊は、それを使う機能で足す。

利用者の発言は、メタデータとして送った時刻（sent_at）を持つ。Messages API の発言には無い欄で、
モデルは文しか読めないので、送る直前に本文の前へ文として入れる（metadata_text）。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

type Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class TextBlock:
    """本文の塊。"""

    text: str
    type: Literal["text"] = "text"


type ContentBlock = TextBlock


@dataclass(frozen=True)
class Message:
    """1つの発言。役割と、塊の並びと、メタデータ。"""

    role: Role
    content: tuple[ContentBlock, ...]
    # 利用者が送った時刻。モデルの発言では None
    sent_at: datetime | None = None


def user_text(text: str, sent_at: datetime | None = None) -> Message:
    """本文だけの、利用者の発言を作る。"""
    return Message(role="user", content=(TextBlock(text),), sent_at=sent_at)


def assistant_text(text: str) -> Message:
    """本文だけの、モデルの発言を作る。"""
    return Message(role="assistant", content=(TextBlock(text),))


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
