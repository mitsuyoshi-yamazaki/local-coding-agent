"""依頼の入力。1行ずつ読む関数（input など）から、改行を含む依頼を組み立てる。

改行は2通りで入る。
- 行末の \\ で Enter を押すと、改行を入れて次の行へ続く（Claude Code と同じ）
- 貼り付けた複数行は1つの依頼になる。端末の bracketed paste（貼り付けた文を、端末が
  ESC [200~ と ESC [201~ の印で囲んで送る機能）を使い、印の間の改行で依頼を切らない

端末は、Enter までを1行として渡す形（canonical mode）のまま使う。行の編集は端末に任せる。
矢印キーなどの ESC で始まる列を送るキーでは、行を編集できない。画面と依頼の中身が食い違う
ので、それらが入った依頼は送らない。
"""

import re
import termios
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TextIO

ESC = "\x1b"
PASTE_START = "\x1b[200~"
PASTE_END = "\x1b[201~"
# 印で囲まれた、貼り付けた文
PASTED = re.compile(f"{re.escape(PASTE_START)}.*?{re.escape(PASTE_END)}", re.DOTALL)
# 端末に、貼り付けた文を印で囲ませる・囲ませるのをやめる
BRACKETED_PASTE_ON = "\x1b[?2004h"
BRACKETED_PASTE_OFF = "\x1b[?2004l"
# \ で続けた2行目からの案内。"> " と幅を揃える
CONTINUATION_PROMPT = "  "


class InputCancelled(Exception):
    """依頼の入力を取り消した。読みかけの依頼は送らない。理由を文で持つ。"""


def read_request(read_line: Callable[[str], str], prompt: str) -> str:
    """依頼を1つ読む。行末の \\ で続けた行と、貼り付けた複数行を、改行でつないで1つにする。

    最初の行での Ctrl-D（EOFError）は、入力の終わりとしてそのまま投げる。依頼の途中の Ctrl-D と、
    矢印キーなどの編集のキーを打った依頼では、InputCancelled を投げる。末尾の改行は除く。
    """
    parts: tuple[str, ...] = ()
    reader = read_line
    next_prompt = prompt
    while True:
        text, last = read_line_or_paste(reader, next_prompt)
        # 貼り付けの終わりの印は貼り付けた文の後に来るので、貼り付けた文の末尾の \ では続けない
        if not last.endswith("\\"):
            return "\n".join((*parts, text)).rstrip("\n")
        parts = (*parts, text[:-1])
        reader = continuing(read_line)
        next_prompt = CONTINUATION_PROMPT


def read_line_or_paste(read_line: Callable[[str], str], prompt: str) -> tuple[str, str]:
    """1行を読む。貼り付けの途中で行が終わっていれば、貼り付けの終わりの印がある行まで読む。

    返すのは、読んだ行を改行でつないで印を除いた文と、最後に読んだ行（印を除く前）。
    """
    lines: tuple[str, ...] = (read_line(prompt),)
    inside = inside_paste_after(lines[-1], inside=False)
    more = continuing(read_line)
    while inside:
        # 貼り付けた行は、届いたときに端末がまとめて表示しているので、案内は出さない
        lines = (*lines, more(""))
        inside = inside_paste_after(lines[-1], inside)
    raw = "\n".join(lines)
    if ESC in PASTED.sub("", raw):
        raise InputCancelled("矢印キーなどの、行を編集するキーは使えない")
    return raw.replace(PASTE_START, "").replace(PASTE_END, ""), lines[-1]


def continuing(read_line: Callable[[str], str]) -> Callable[[str], str]:
    """依頼の途中の行を読む関数にする。途中の Ctrl-D は、依頼の取り消しにする。"""

    def read(prompt: str) -> str:
        try:
            return read_line(prompt)
        except EOFError:
            raise InputCancelled("入力の途中で Ctrl-D が押された") from None

    return read


def inside_paste_after(line: str, inside: bool) -> bool:
    """行を読み終えたとき、貼り付けの途中か。inside は、行を読む前に途中だったか。"""
    start = line.rfind(PASTE_START)
    end = line.rfind(PASTE_END)
    if start == end == -1:
        return inside
    return start > end


@contextmanager
def bracketed_paste(stdin: TextIO, stdout: TextIO) -> Iterator[None]:
    """端末に、貼り付けた文を印で囲ませる。抜けるときに端末の設定を元に戻す。

    印は制御文字 ESC で始まる。端末は既定で、入力した制御文字を ^[ のように見える形で
    表示し返す（ECHOCTL）ので、その間はこれを切る。入力か出力が端末でなければ、何もしない。
    """
    if not (stdin.isatty() and stdout.isatty()):
        yield
        return
    fd = stdin.fileno()
    saved = termios.tcgetattr(fd)
    quiet = [*saved[:3], saved[3] & ~termios.ECHOCTL, *saved[4:]]
    termios.tcsetattr(fd, termios.TCSANOW, quiet)
    stdout.write(BRACKETED_PASTE_ON)
    stdout.flush()
    try:
        yield
    finally:
        stdout.write(BRACKETED_PASTE_OFF)
        stdout.flush()
        termios.tcsetattr(fd, termios.TCSANOW, saved)
