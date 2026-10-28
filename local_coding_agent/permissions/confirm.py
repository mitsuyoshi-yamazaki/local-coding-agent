"""実行の前に、人に確かめる。

問うのは、許可の判定（permissions/policy.py の decide）が「問う」に決めた呼び出しだけである。
判定するのはハーネスと人で、モデルは関わらない。拒んだことは、誤りの結果としてモデルに返す。
人は、拒む理由を答えに書ける。書いた理由は、拒んだことと一緒にモデルに返す。
"""

from collections.abc import Callable
from dataclasses import dataclass

PROMPT = "実行してよいか [y/N/拒む理由]: "
# 許すとみなす答え（大文字も可）
YES = ("y", "yes")
# 理由を書かずに拒むとみなす答え（大文字も可）
NO = ("", "n", "no")
# 拒んだときに、モデルに返す結果
REFUSED = "利用者が実行を拒んだ"


@dataclass(frozen=True)
class Answer:
    """問いへの答え。"""

    allowed: bool
    # 拒んだときに、人が書いた理由。書かなかったら None
    reason: str | None = None


def confirm(read_line: Callable[[str], str]) -> Answer:
    """人に問い、答えを返す。

    y か yes なら許す。n・no・空なら、理由を書かずに拒む。それ以外の答えは、拒む理由として
    受ける。入力の終わり（Ctrl-D）は、理由を書かずに拒んだとする。
    Ctrl-C（KeyboardInterrupt）は捕まえない。呼ぶ側が、その回を止める。
    """
    try:
        text = read_line(PROMPT).strip()
    except EOFError:
        return Answer(False)
    if text.lower() in YES:
        return Answer(True)
    if text.lower() in NO:
        return Answer(False)
    return Answer(False, text)


def refusal(answer: Answer) -> str:
    """人が拒んだときに、モデルに返す結果の文。理由があれば後ろに付ける。"""
    return REFUSED if answer.reason is None else f"{REFUSED}。理由: {answer.reason}"
