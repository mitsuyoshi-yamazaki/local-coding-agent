"""エージェントのループ。

1回の依頼の中で、モデルが道具を呼ぶ間、「モデルを呼ぶ → 道具を実行する → 結果を履歴に足す」
を繰り返し、道具を呼ばない応答が来たら終える。
"""

from dataclasses import replace

from local_coding_agent.loop.model_call import call_model
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


def run_turn(
    session: Session, history: tuple[Message, ...], text: str, turn: int
) -> tuple[Message, ...]:
    """1回の依頼を処理し、新しい履歴を返す。

    回数の上限は無く、止めるのは人の Ctrl-C である。止めた回と誤りの回は、済んだ歩み
    （応答と、その呼び出しの結果）までを履歴に残す。済んだ歩みが無ければ、元の履歴を返す。
    """
    messages = (*history, user_text(text, sent_at=session.now()))
    step = 0
    try:
        while True:
            step += 1
            outcome = call_model(session, messages, turn, step)
            if outcome.status != "done":
                return _stopped(session, history, messages, outcome.status == "error")
            reply = assistant_message(outcome.text, outcome.tool_uses, outcome.thinking)
            if not outcome.tool_uses:
                if not outcome.text.strip():
                    session.output.write(THINKING_ONLY + "\n")
                return (*messages, reply)
            results = run_tool_calls(session, outcome.tool_uses, turn, step)
            messages = (*messages, reply, tool_results(results.blocks))
            if results.stopped:
                session.output.write("\n" + CANCELLED + "\n")
                return _stopped(session, history, messages, error=False)
    except KeyboardInterrupt:
        # 応答の途中と道具の途中の外で押された Ctrl-C（表示や記録の途中など）
        session.output.write("\n" + CANCELLED + "\n")
        return _stopped(session, history, messages, error=False)


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
