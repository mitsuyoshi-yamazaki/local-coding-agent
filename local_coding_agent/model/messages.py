"""会話の形。Claude の Messages API に揃え、発言を塊（content block）の並びで持つ。

F-01 で使う塊は本文（text）だけである。thinking・tool_use・tool_result の塊は、
それを使う機能で足す。
"""

from dataclasses import dataclass
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
    """1つの発言。役割と、塊の並び。"""

    role: Role
    content: tuple[ContentBlock, ...]


def user_text(text: str) -> Message:
    """本文だけの、利用者の発言を作る。"""
    return Message(role="user", content=(TextBlock(text),))


def assistant_text(text: str) -> Message:
    """本文だけの、モデルの発言を作る。"""
    return Message(role="assistant", content=(TextBlock(text),))
