"""Ollama の独自の API（/api/chat）との接続。

会話の形（model/messages.py）を、送る直前に /api/chat の形へ変える。応答は NDJSON
（1行に1つの JSON）で流れてくるので、1行ずつ読んで本文の断片と終わりの知らせに変える。
"""

import json
import urllib.error
import urllib.request
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass

from local_coding_agent.model.chat import (
    ChatRequest,
    Done,
    ModelError,
    StreamEvent,
    TextDelta,
)
from local_coding_agent.model.messages import Message

# 最後の行（done が true）に載る、モデルの側が数えたトークン数と時間（時間はナノ秒）
STAT_KEYS = (
    "prompt_eval_count",
    "eval_count",
    "total_duration",
    "load_duration",
    "prompt_eval_duration",
    "eval_duration",
)


def to_ollama_messages(messages: Sequence[Message]) -> list[dict[str, str]]:
    """会話を /api/chat の messages に変える。本文の塊を、つないで1つの文字列にする。"""
    return [
        {"role": message.role, "content": "".join(b.text for b in message.content)}
        for message in messages
    ]


def chat_request_body(model: str, messages: Sequence[Message]) -> dict[str, object]:
    """/api/chat へ送る JSON の全体を作る。"""
    return {
        "model": model,
        "messages": to_ollama_messages(messages),
        "stream": True,
    }


def read_stream(lines: Iterable[bytes]) -> Iterator[StreamEvent]:
    """NDJSON の行を読み、本文の断片と、終わりの知らせに変える。

    途中で error の行が届いたら ModelError を投げる。
    """
    for raw in lines:
        if not raw.strip():
            continue
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise ModelError(f"応答の行が JSON の object ではない: {raw!r}")
        if "error" in event:
            raise ModelError(f"Ollama が誤りを返した: {event['error']}")
        message = event.get("message")
        text = message.get("content", "") if isinstance(message, dict) else ""
        if text:
            yield TextDelta(str(text))
        if event.get("done") is True:
            yield _done(event)
            return


def _done(event: dict[str, object]) -> Done:
    reason = event.get("done_reason")
    values = {key: event.get(key) for key in STAT_KEYS}
    stats = {key: value for key, value in values.items() if isinstance(value, int)}
    return Done(done_reason=reason if isinstance(reason, str) else None, stats=stats)


def http_error_message(error: urllib.error.HTTPError) -> str:
    """誤りの応答（本文は {"error": "…"}）を、表示する文に変える。読んだら接続を閉じる。"""
    with error:
        body = error.read()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict) and "error" in payload:
        detail = str(payload["error"])
    else:
        detail = body.decode(errors="replace")
    return f"Ollama が誤りを返した（{error.code}）: {detail}"


@dataclass(frozen=True)
class OllamaChat:
    """手元の Ollama の /api/chat に会話を送る。"""

    host: str
    model: str

    def build_request(self, messages: Sequence[Message]) -> ChatRequest:
        return ChatRequest(
            url=f"{self.host.rstrip('/')}/api/chat",
            body=chat_request_body(self.model, messages),
        )

    def stream(self, request: ChatRequest) -> Iterator[StreamEvent]:
        http_request = urllib.request.Request(
            request.url,
            data=json.dumps(request.body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request) as response:
                yield from read_stream(response)
        except urllib.error.HTTPError as error:
            raise ModelError(http_error_message(error)) from error
        except urllib.error.URLError as error:
            raise ModelError(
                f"Ollama に繋がらない（{request.url}）: {error.reason}"
            ) from error
        except OSError as error:
            raise ModelError(f"Ollama との通信が切れた: {error}") from error
