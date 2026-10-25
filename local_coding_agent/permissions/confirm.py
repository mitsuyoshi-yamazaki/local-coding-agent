"""実行の前に、人に確かめる。

問うのは、変更を伴う道具（Tool.changes が True）だけである。判定するのはハーネスと人で、
モデルは関わらない。拒んだことは、誤りの結果としてモデルに返す。
"""

from collections.abc import Callable

PROMPT = "実行してよいか [y/N]: "
# 許すとみなす答え（大文字も可）
YES = ("y", "yes")
# 拒んだときに、モデルに返す結果
REFUSED = "利用者が実行を拒んだ"


def confirm(read_line: Callable[[str], str]) -> bool:
    """人に問い、許したら True。

    y か yes なら許す。それ以外の答えと、入力の終わり（Ctrl-D）は拒んだとする。
    Ctrl-C（KeyboardInterrupt）は捕まえない。呼ぶ側が、その回を止める。
    """
    try:
        answer = read_line(PROMPT)
    except EOFError:
        return False
    return answer.strip().lower() in YES
