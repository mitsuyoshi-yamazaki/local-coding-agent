"""エージェントのループ。

1回の依頼の中で、モデルが道具を呼ぶ間、「モデルを呼ぶ → 道具を実行する → 結果を履歴に足す」
を繰り返し、道具を呼ばない応答が来たら終える。
"""

from dataclasses import dataclass, replace

from local_coding_agent.loop.model_call import Outcome, call_model
from local_coding_agent.loop.session import Session
from local_coding_agent.loop.tool_call import run_tool_calls
from local_coding_agent.model.messages import (
    Message,
    TextBlock,
    assistant_message,
    tool_results,
    user_text,
)

CANCELLED = "（止めた）"
NOT_KEPT = "（この回は履歴に足さない）"
KEPT = "（済んだ歩みまでを履歴に残す）"
# 済んだ歩みを残すときに、最後の発言の末尾に足す知らせ。モデルが読む
CANCELLED_NOTE = "（利用者がこの回を途中で止めた）"
ERROR_NOTE = "（誤りで、この回が途中で止まった）"
# 本文も道具の呼び出しも無い応答で、回を終えたときの表示
THINKING_ONLY = "（推論だけで終わった）"


@dataclass(frozen=True)
class TurnResult:
    """1回の依頼を処理した結果。"""

    history: tuple[Message, ...]
    # その回で最後に終わりまで届いた応答の、入力のトークン数（prompt_eval_count）。
    # 1つも届かなかったか、モデルの API が数えなかったら None
    input_tokens: int | None = None


def run_turn(
    session: Session,
    history: tuple[Message, ...],
    text: str,
    turn: int,
    command: str | None = None,
    skill: str | None = None,
) -> TurnResult:
    """1回の依頼を処理し、新しい履歴を返す。command は、自作のコマンドで送るときの、打った行。
    skill は、スキルを /<名前> で呼んで送るときの、打った行。

    回数の上限は無く、止めるのは人の Ctrl-C である。止めた回と誤りの回は、済んだ歩み
    （応答と、その呼び出しの結果）までを履歴に残す。済んだ歩みが無ければ、元の履歴を返す。
    """
    request = user_text(text, sent_at=session.now(), command=command, skill=skill)
    messages = (*history, request)
    step = 0
    tokens: int | None = None
    try:
        while True:
            step += 1
            outcome = call_model(session, messages, turn, step)
            if outcome.status != "done":
                error = outcome.status == "error"
                kept = _stopped(session, history, messages, error)
                return TurnResult(kept, tokens)
            tokens = _input_tokens(outcome, tokens)
            reply = assistant_message(outcome.text, outcome.tool_uses, outcome.thinking)
            if not outcome.tool_uses:
                if not outcome.text.strip():
                    session.output.write(THINKING_ONLY + "\n")
                return TurnResult((*messages, reply), tokens)
            results = run_tool_calls(session, outcome.tool_uses, turn, step)
            messages = (*messages, reply, tool_results(results.blocks))
            if results.stopped:
                session.output.write("\n" + CANCELLED + "\n")
                kept = _stopped(session, history, messages, error=False)
                return TurnResult(kept, tokens)
    except KeyboardInterrupt:
        # 応答の途中と道具の途中の外で押された Ctrl-C（表示や記録の途中など）
        session.output.write("\n" + CANCELLED + "\n")
        kept = _stopped(session, history, messages, error=False)
        return TurnResult(kept, tokens)


def _input_tokens(outcome: Outcome, before: int | None) -> int | None:
    """終わりまで届いた応答の、入力のトークン数。モデルの API が数えなければ before。"""
    counted = outcome.done.stats.get("prompt_eval_count") if outcome.done else None
    return before if counted is None else counted


def _stopped(
    session: Session,
    history: tuple[Message, ...],
    messages: tuple[Message, ...],
    error: bool,
) -> tuple[Message, ...]:
    """止まった回の履歴。済んだ歩みが無ければ元の履歴、あれば止まったことの知らせを足して残す。

    済んだ歩みがあれば、messages の最後の発言は、道具の結果の発言である。
    """
    if len(messages) == len(history) + 1:
        session.output.write(NOT_KEPT + "\n")
        return history
    session.output.write(KEPT + "\n")
    note = TextBlock(ERROR_NOTE if error else CANCELLED_NOTE)
    last = messages[-1]
    return (*messages[:-1], replace(last, content=(*last.content, note)))
