"""モデルとのやりとりの形。どのモデルの API にも依らない。

REPL はこの形だけを使い、Ollama の形は知らない。テストでは、この形を持つ偽物のモデルを使う。
"""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from local_coding_agent.model.messages import Message


class ModelError(Exception):
    """モデルに繋がらない・モデルが誤りを返した。"""


@dataclass(frozen=True)
class ChatRequest:
    """モデルへ送る要求。送り先と、送る JSON の全体。"""

    url: str
    body: Mapping[str, object]


@dataclass(frozen=True)
class TextDelta:
    """流れてくる応答の、本文の断片。"""

    text: str


@dataclass(frozen=True)
class Done:
    """応答の終わり。終わった理由と、モデルの側が数えたトークン数と時間。"""

    done_reason: str | None
    stats: Mapping[str, int] = field(default_factory=dict)


type StreamEvent = TextDelta | Done


class ChatModel(Protocol):
    """会話を送り、応答を流して受け取る相手。"""

    def build_request(self, system: str, messages: Sequence[Message]) -> ChatRequest:
        """system prompt と会話の全体から、送る要求を作る。

        Messages API と同じく、system prompt は発言の並びとは別に渡す。空なら送らない。
        """
        ...

    def stream(self, request: ChatRequest) -> Iterator[StreamEvent]:
        """要求を送り、応答を届いた順に返す。繋がらないときは ModelError を投げる。"""
        ...
