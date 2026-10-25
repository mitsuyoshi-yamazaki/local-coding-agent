"""ループの1歩: モデルを1回呼び、応答を流して表示し、走行の記録に書く。

毎回、system prompt と道具の定義と会話の全体を送る。応答の本文は届いたそばから表示し、
道具の呼び出しは集めて返す（実行は loop/tool_call.py）。
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from local_coding_agent.loop.session import Session
from local_coding_agent.model.chat import (
    ChatRequest,
    Done,
    ModelError,
    TextDelta,
    ToolCall,
)
from local_coding_agent.model.messages import Message, ToolUseBlock

type Status = Literal["done", "cancelled", "error"]


@dataclass(frozen=True)
class Outcome:
    """モデルを1回呼んだ結果。"""

    status: Status
    text: str
    # 道具の呼び出し。id は必ず付いている
    tool_uses: tuple[ToolUseBlock, ...]
    done: Done | None
    # 本文の断片か道具の呼び出しが、最初に届くまでの時間
    first_token_seconds: float | None
    total_seconds: float
    error: str | None = None


def call_model(
    session: Session, messages: Sequence[Message], turn: int, step: int
) -> Outcome:
    """モデルを1回呼ぶ。step は、その回の中で何回目にモデルを呼んだか。"""
    tools = tuple(tool.definition for tool in session.tools)
    request = session.model.build_request(session.system, messages, tools)
    session.trace.write(
        {
            "type": "request",
            "turn": turn,
            "step": step,
            "url": request.url,
            "body": request.body,
        }
    )
    outcome = receive(session, request, id_prefix=f"call_{turn}_{step}")
    session.trace.write(response_record(turn, step, outcome))
    session.output.write("\n" + summary(outcome) + "\n")
    return outcome


def receive(session: Session, request: ChatRequest, id_prefix: str) -> Outcome:
    """応答を届いた順に表示し、本文・道具の呼び出し・時間を集める。

    モデルの API が呼び出しに id を付けなければ、id_prefix と順から付ける（例: call_1_2_0）。
    """
    started = session.clock()
    text = ""
    calls: tuple[ToolCall, ...] = ()
    first: float | None = None
    done: Done | None = None
    try:
        for event in session.model.stream(request):
            if first is None and not isinstance(event, Done):
                first = session.clock() - started
            if isinstance(event, TextDelta):
                text += event.text
                session.output.write(event.text)
                session.output.flush()
            elif isinstance(event, ToolCall):
                calls = (*calls, event)
            else:
                done = event
    except KeyboardInterrupt:
        return Outcome("cancelled", text, (), None, first, session.clock() - started)
    except ModelError as error:
        elapsed = session.clock() - started
        return Outcome("error", text, (), None, first, elapsed, str(error))
    elapsed = session.clock() - started
    if done is None:
        message = "応答が終わりの行の前に切れた"
        return Outcome("error", text, (), None, first, elapsed, message)
    uses = _tool_uses(calls, id_prefix)
    return Outcome("done", text, uses, done, first, elapsed)


def _tool_uses(calls: Sequence[ToolCall], id_prefix: str) -> tuple[ToolUseBlock, ...]:
    return tuple(
        ToolUseBlock(
            id=call.id or f"{id_prefix}_{index}", name=call.name, input=call.input
        )
        for index, call in enumerate(calls)
    )


def response_record(turn: int, step: int, outcome: Outcome) -> dict[str, object]:
    """応答の1件の、走行の記録。"""
    return {
        "type": "response",
        "turn": turn,
        "step": step,
        "status": outcome.status,
        "text": outcome.text,
        "tool_calls": [
            {"id": use.id, "name": use.name, "input": dict(use.input)}
            for use in outcome.tool_uses
        ],
        "done_reason": outcome.done.done_reason if outcome.done else None,
        "model_stats": dict(outcome.done.stats) if outcome.done else {},
        "measured": {
            "first_token_seconds": outcome.first_token_seconds,
            "total_seconds": outcome.total_seconds,
        },
        "error": outcome.error,
    }


def summary(outcome: Outcome) -> str:
    """応答の後に出す1行。止めた・誤りの回を履歴にどう残すかは、ループが次の行に出す。"""
    if outcome.status == "cancelled":
        return "（止めた）"
    if outcome.status == "error":
        return f"誤り: {outcome.error}"
    stats = outcome.done.stats if outcome.done else {}
    return (
        f"[入力 {stats.get('prompt_eval_count', '?')} トークン・"
        f"出力 {stats.get('eval_count', '?')} トークン・"
        f"最初の文字まで {_seconds(outcome.first_token_seconds)}・"
        f"全体 {_seconds(outcome.total_seconds)}]"
    )


def _seconds(value: float | None) -> str:
    return "?" if value is None else f"{value:.2f} 秒"
