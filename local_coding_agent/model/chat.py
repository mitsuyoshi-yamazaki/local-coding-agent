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
class ThinkingDelta:
    """流れてくる応答の、推論の文（thinking）の断片。デバッグの表示にだけ使う。"""

    text: str


@dataclass(frozen=True)
class OtherFields:
    """届いた1行の、本文と推論の文のほかの欄。デバッグの表示にだけ使う。

    途中の行では、毎回同じ形で来る欄（モデルの名前・時刻など）を除く。終わりの行では全ての欄を持つ。
    """

    fields: Mapping[str, object]


@dataclass(frozen=True)
class RawLine:
    """モデルから届いた1行を、そのままの文字列で。デバッグの表示にだけ使う。"""

    text: str


@dataclass(frozen=True)
class Done:
    """応答の終わり。終わった理由と、モデルの側が数えたトークン数と時間。"""

    done_reason: str | None
    stats: Mapping[str, int] = field(default_factory=dict)


# 1行が届くたびに、RawLine・ThinkingDelta・TextDelta・OtherFields の順に（あるものだけ）返し、
# 最後の行の後に Done を返す
type StreamEvent = RawLine | ThinkingDelta | TextDelta | OtherFields | Done


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
