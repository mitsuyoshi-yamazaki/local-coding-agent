"""Ollama の独自の API（/api/chat）との接続。

送る形は model/ollama_messages.py で作る。応答は NDJSON（1行に1つの JSON）で流れてくるので、
1行ずつ読んで、推論の文の断片・本文の断片・道具の呼び出し・終わりの知らせに変える。
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
    ThinkingDelta,
    ToolCall,
    ToolDefinition,
)
from local_coding_agent.model.messages import Message
from local_coding_agent.model.ollama_messages import chat_request_body

# 最後の行（done が true）に載る、モデルの側が数えたトークン数と時間（時間はナノ秒）
STAT_KEYS = (
    "prompt_eval_count",
    "eval_count",
    "total_duration",
    "load_duration",
    "prompt_eval_duration",
    "eval_duration",
)


def read_stream(lines: Iterable[bytes]) -> Iterator[StreamEvent]:
    """NDJSON の行を読み、推論の文と本文の断片・道具の呼び出し・終わりの知らせに変える。

    途中で error の行や、読めない行が届いたら ModelError を投げる。
    """
    for raw in lines:
        if not raw.strip():
            continue
        event = _parse_line(raw)
        yield from _message_events(event.get("message"))
        if event.get("done") is True:
            yield _done(event)
            return


def _parse_line(raw: bytes) -> dict[str, object]:
    try:
        event = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ModelError(f"応答の行が JSON として読めない: {raw!r}") from error
    if not isinstance(event, dict):
        raise ModelError(f"応答の行が JSON の object ではない: {raw!r}")
    if "error" in event:
        raise ModelError(f"Ollama が誤りを返した: {event['error']}")
    return event


def _message_events(message: object) -> Iterator[StreamEvent]:
    """1行の message から、推論の文の断片・本文の断片・道具の呼び出しを取り出す。

    推論の文は、本文と別の欄（thinking）に載る。`think` を送らなくても、推論を学習した
    モデルは返す。呼び出しがどの行に載るかは決まっていないので、全ての行から集める。
    """
    if not isinstance(message, dict):
        return
    thinking = message.get("thinking", "")
    if thinking:
        yield ThinkingDelta(str(thinking))
    text = message.get("content", "")
    if text:
        yield TextDelta(str(text))
    calls = message.get("tool_calls")
    if calls is None:
        return
    if not isinstance(calls, list):
        raise ModelError(f"tool_calls が配列ではない: {calls!r}")
    for call in calls:
        yield _tool_call(call)


def _tool_call(call: object) -> ToolCall:
    """tool_calls の1つ（{"id": …, "function": {"name": …, "arguments": {…}}}）を読む。"""
    function = call.get("function") if isinstance(call, dict) else None
    if not isinstance(call, dict) or not isinstance(function, dict):
        raise ModelError(f"道具の呼び出しの形が読めない: {call!r}")
    name = function.get("name")
    arguments = function.get("arguments", {})
    if not isinstance(name, str) or not isinstance(arguments, dict):
        raise ModelError(f"道具の呼び出しの形が読めない: {call!r}")
    call_id = call.get("id")
    return ToolCall(
        id=call_id if isinstance(call_id, str) and call_id else None,
        name=name,
        input=arguments,
    )


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

    def build_request(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolDefinition],
    ) -> ChatRequest:
        return ChatRequest(
            url=f"{self.host.rstrip('/')}/api/chat",
            body=chat_request_body(self.model, system, messages, tools),
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
