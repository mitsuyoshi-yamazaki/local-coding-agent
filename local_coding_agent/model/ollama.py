"""Ollama の独自の API（/api/chat）との接続。

system prompt と会話の形（model/messages.py）を、送る直前に /api/chat の形へ変える。応答は
NDJSON（1行に1つの JSON）で流れてくるので、1行ずつ読んで本文の断片と終わりの知らせに変える。
デバッグの表示のために、届いた行そのものと、推論の文・ほかの欄も知らせる。
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
    OtherFields,
    RawLine,
    StreamEvent,
    TextDelta,
    ThinkingDelta,
)
from local_coding_agent.model.messages import Message, metadata_text

# 最後の行（done が true）に載る、モデルの側が数えたトークン数と時間（時間はナノ秒）
STAT_KEYS = (
    "prompt_eval_count",
    "eval_count",
    "total_duration",
    "load_duration",
    "prompt_eval_duration",
    "eval_duration",
)

# 途中の行に毎回同じ形で来る欄。デバッグの表示で、途中の行からは除く
ROUTINE_KEYS = ("model", "created_at", "done")

# message の中で、文として別に表示する欄（role は常に assistant）
MESSAGE_TEXT_KEYS = ("role", "content", "thinking")


def to_ollama_messages(
    system: str, messages: Sequence[Message]
) -> list[dict[str, str]]:
    """system prompt と会話を、/api/chat の messages に変える。

    /api/chat には system prompt の欄が無いので、先頭の system の発言にする（空なら入れない）。
    発言ごとに、メタデータの文と本文の塊を、つないで1つの文字列にする。
    """
    head = [{"role": "system", "content": system}] if system else []
    return [*head, *(_ollama_message(message) for message in messages)]


def _ollama_message(message: Message) -> dict[str, str]:
    text = "".join(block.text for block in message.content)
    return {"role": message.role, "content": metadata_text(message) + text}


def chat_request_body(
    model: str, system: str, messages: Sequence[Message]
) -> dict[str, object]:
    """/api/chat へ送る JSON の全体を作る。"""
    return {
        "model": model,
        "messages": to_ollama_messages(system, messages),
        "stream": True,
    }


def read_stream(lines: Iterable[bytes]) -> Iterator[StreamEvent]:
    """NDJSON の行を読み、届いた行・推論の文と本文の断片・ほかの欄・終わりの知らせに変える。

    途中で error の行や、JSON として読めない行が届いたら、その行を返してから ModelError を投げる。
    """
    for raw in lines:
        if not raw.strip():
            continue
        yield RawLine(raw.decode(errors="replace").rstrip("\r\n"))
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ModelError(f"応答の行が JSON として読めない: {raw!r}") from error
        if not isinstance(event, dict):
            raise ModelError(f"応答の行が JSON の object ではない: {raw!r}")
        if "error" in event:
            raise ModelError(f"Ollama が誤りを返した: {event['error']}")
        message = event.get("message")
        thinking = message.get("thinking", "") if isinstance(message, dict) else ""
        text = message.get("content", "") if isinstance(message, dict) else ""
        if thinking:
            yield ThinkingDelta(str(thinking))
        if text:
            yield TextDelta(str(text))
        others = other_fields(event)
        if others:
            yield OtherFields(others)
        if event.get("done") is True:
            yield _done(event)
            return


def other_fields(event: dict[str, object]) -> dict[str, object]:
    """1行の欄から、本文と推論の文を除く。途中の行では、毎回同じ形で来る欄も除く。"""
    skipped = () if event.get("done") is True else ROUTINE_KEYS
    head = {
        key: value
        for key, value in event.items()
        if key != "message" and key not in skipped
    }
    message = event.get("message")
    if not isinstance(message, dict):
        return head if message is None else {**head, "message": message}
    rest = {
        key: value for key, value in message.items() if key not in MESSAGE_TEXT_KEYS
    }
    return {**head, "message": rest} if rest else head


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

    def build_request(self, system: str, messages: Sequence[Message]) -> ChatRequest:
        return ChatRequest(
            url=f"{self.host.rstrip('/')}/api/chat",
            body=chat_request_body(self.model, system, messages),
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
