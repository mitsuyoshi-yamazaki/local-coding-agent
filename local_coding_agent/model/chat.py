"""モデルとのやりとりの形。どのモデルの API にも依らない。

ループはこの形だけを使い、Ollama の形は知らない。テストでは、この形を持つ偽物のモデルを使う。
"""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from local_coding_agent.model.messages import Message


class ModelError(Exception):
    """モデルに繋がらない・モデルが誤りを返した。"""


@dataclass(frozen=True)
class ToolDefinition:
    """モデルに渡す道具の定義。Messages API の道具の定義と同じ欄を持つ。"""

    name: str
    # モデルが、いつ・どう使うかを決めるための説明
    description: str
    # 入力の形（JSON Schema）
    input_schema: Mapping[str, object]


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
class ToolCall:
    """応答の中の、道具の呼び出し1つ。"""

    # モデルの API が付けた id。付けなければ None で、ループが付ける
    id: str | None
    name: str
    input: Mapping[str, object]


@dataclass(frozen=True)
class Done:
    """応答の終わり。終わった理由と、モデルの側が数えたトークン数と時間。"""

    done_reason: str | None
    stats: Mapping[str, int] = field(default_factory=dict)


type StreamEvent = TextDelta | ToolCall | Done


class ChatModel(Protocol):
    """会話を送り、応答を流して受け取る相手。"""

    def build_request(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolDefinition],
    ) -> ChatRequest:
        """system prompt と会話の全体と道具の定義から、送る要求を作る。

        Messages API と同じく、system prompt と道具の定義は、発言の並びとは別に渡す。
        どちらも、空なら送らない。
        """
        ...

    def stream(self, request: ChatRequest) -> Iterator[StreamEvent]:
        """要求を送り、応答を届いた順に返す。繋がらないときは ModelError を投げる。"""
        ...
