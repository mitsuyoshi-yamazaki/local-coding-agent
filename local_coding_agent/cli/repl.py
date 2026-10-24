"""端末の REPL。依頼を1行ずつ受け、ループ（loop/turn.py）に渡す。

モデルの API は会話の状態を持たないので、履歴はここで持つ。回ごとに履歴をループへ渡し、
その回を足した新しい履歴を受け取る。
"""

from local_coding_agent.loop.session import Session
from local_coding_agent.loop.turn import run_turn
from local_coding_agent.model.messages import Message

PROMPT = "> "


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
