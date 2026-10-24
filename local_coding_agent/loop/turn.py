"""エージェントのループ。

1回の依頼の中で、モデルが道具を呼ぶ間、「モデルを呼ぶ → 道具を実行する → 結果を履歴に足す」
を繰り返し、道具を呼ばない応答が来たら終える。
"""

from local_coding_agent.loop.model_call import call_model
from local_coding_agent.loop.session import Session
from local_coding_agent.loop.tool_call import run_tool_calls
from local_coding_agent.model.messages import (
    Message,
    assistant_message,
    tool_results,
    user_text,
)

CANCELLED = "（止めた。この回は履歴に足さない）"


def run_turn(
    session: Session, history: tuple[Message, ...], text: str, turn: int
) -> tuple[Message, ...]:
    """1回の依頼を処理し、新しい履歴を返す。

    回数の上限は無く、止めるのは人の Ctrl-C である。止めた回と誤りの回は、その回の全体
    （依頼・道具の呼び出し・結果）を履歴に足さず、元の履歴を返す。
    """
    messages = (*history, user_text(text, sent_at=session.now()))
    step = 0
    try:
        while True:
            step += 1
            outcome = call_model(session, messages, turn, step)
            if outcome.status != "done":
                return history
            reply = assistant_message(outcome.text, outcome.tool_uses)
            messages = (*messages, reply)
            if not outcome.tool_uses:
                return messages
            results = run_tool_calls(session, outcome.tool_uses, turn, step)
            messages = (*messages, tool_results(results))
    except KeyboardInterrupt:
        # 道具の実行の途中・確かめる問いの途中の Ctrl-C。応答の途中の Ctrl-C は call_model が扱う
        session.output.write("\n" + CANCELLED + "\n")
        return history
