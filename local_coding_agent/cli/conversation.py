"""REPL が、会話の間に持つもの。"""

from dataclasses import dataclass

from local_coding_agent.loop.session import Session
from local_coding_agent.model.messages import Message


@dataclass(frozen=True)
class Conversation:
    """REPL が会話の間に持つもの。組み込みのコマンドは、これを受けて新しいものを返す。"""

    # ループに渡すもの。/mode は、許可のモードを替えた session を作る
    session: Session
    # 会話の履歴。/clear で空にする
    history: tuple[Message, ...] = ()
    # 始めた回の数。走行の記録の turn で、/clear の後も続けて数える
    turn: int = 0
    # 最後に終わりまで届いた応答の、入力のトークン数（/context）。無ければ None
    input_tokens: int | None = None
    # /exit で True にする
    finished: bool = False

    @property
    def next_turn(self) -> int:
        """次に始める回の番号。"""
        return self.turn + 1
