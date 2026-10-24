"""端末の REPL。依頼を1行ずつ受け、会話の全体をモデルに送り、応答を流して表示する。

モデルの API は会話の状態を持たないので、履歴はここで持ち、毎回その全体を送る。
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TextIO

from local_coding_agent.model.chat import (
    ChatModel,
    ChatRequest,
    Done,
    ModelError,
    TextDelta,
)
from local_coding_agent.model.messages import Message, assistant_text, user_text
from local_coding_agent.trace.writer import TraceSink

type Status = Literal["done", "cancelled", "error"]

PROMPT = "> "


@dataclass(frozen=True)
class Session:
    """REPL が使うもの。テストでは偽物に差し替える。"""

    model: ChatModel
    read_line: Callable[[str], str]
    output: TextIO
    trace: TraceSink
    clock: Callable[[], float]


@dataclass(frozen=True)
class Outcome:
    """1回の応答を受け取った結果。"""

    status: Status
    text: str
    done: Done | None
    first_token_seconds: float | None
    total_seconds: float
    error: str | None = None


def run(session: Session) -> None:
    """入力の終わり（Ctrl-D）まで、依頼を受けて応答を返す。"""
    history: tuple[Message, ...] = ()
    turn = 0
    while True:
        try:
            line = session.read_line(PROMPT)
        except EOFError:
            session.output.write("\n")
            return
        except KeyboardInterrupt:
            session.output.write("\n")
            continue
        if not line.strip():
            continue
        turn += 1
        history = run_turn(session, history, line, turn)


def run_turn(
    session: Session, history: tuple[Message, ...], text: str, turn: int
) -> tuple[Message, ...]:
    """1回の依頼を送って応答を表示し、新しい履歴を返す。

    止めた回と誤りの回は履歴に足さず、元の履歴を返す。
    """
    messages = (*history, user_text(text))
    request = session.model.build_request(messages)
    session.trace.write(
        {"type": "request", "turn": turn, "url": request.url, "body": request.body}
    )
    outcome = receive(session, request)
    session.trace.write(response_record(turn, outcome))
    session.output.write("\n" + summary(outcome) + "\n")
    if outcome.status != "done":
        return history
    return (*messages, assistant_text(outcome.text))


def receive(session: Session, request: ChatRequest) -> Outcome:
    """応答を届いた順に表示し、本文と時間を集める。"""
    started = session.clock()
    text = ""
    first: float | None = None
    done: Done | None = None
    try:
        for event in session.model.stream(request):
            if isinstance(event, TextDelta):
                if first is None:
                    first = session.clock() - started
                text += event.text
                session.output.write(event.text)
                session.output.flush()
            else:
                done = event
    except KeyboardInterrupt:
        return Outcome("cancelled", text, None, first, session.clock() - started)
    except ModelError as error:
        elapsed = session.clock() - started
        return Outcome("error", text, None, first, elapsed, str(error))
    elapsed = session.clock() - started
    if done is None:
        return Outcome(
            "error", text, None, first, elapsed, "応答が終わりの行の前に切れた"
        )
    return Outcome("done", text, done, first, elapsed)


def response_record(turn: int, outcome: Outcome) -> dict[str, object]:
    """応答の1件の、走行の記録。"""
    return {
        "type": "response",
        "turn": turn,
        "status": outcome.status,
        "text": outcome.text,
        "done_reason": outcome.done.done_reason if outcome.done else None,
        "model_stats": dict(outcome.done.stats) if outcome.done else {},
        "measured": {
            "first_token_seconds": outcome.first_token_seconds,
            "total_seconds": outcome.total_seconds,
        },
        "error": outcome.error,
    }


def summary(outcome: Outcome) -> str:
    """応答の後に出す1行。"""
    if outcome.status == "cancelled":
        return "（止めた。この回は履歴に足さない）"
    if outcome.status == "error":
        return f"誤り: {outcome.error}（この回は履歴に足さない）"
    stats = outcome.done.stats if outcome.done else {}
    return (
        f"[入力 {stats.get('prompt_eval_count', '?')} トークン・"
        f"出力 {stats.get('eval_count', '?')} トークン・"
        f"最初の文字まで {_seconds(outcome.first_token_seconds)}・"
        f"全体 {_seconds(outcome.total_seconds)}]"
    )


def _seconds(value: float | None) -> str:
    return "?" if value is None else f"{value:.2f} 秒"
