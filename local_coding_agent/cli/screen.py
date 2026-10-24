"""端末への表示。文の種類ごとの色（ANSI のエスケープ）と、行の頭にいるかを扱う。

色は、出力が端末のときだけ付ける（起動のときに決める）。テストやファイルへの出力では付けない。
"""

from typing import Literal, TextIO

# 文の種類。本文（text）には色を付けず、推論の文（thinking）と添え書き（note）は薄くする
type Kind = Literal["text", "thinking", "note"]

DIM = "\x1b[2m"
RESET = "\x1b[0m"
# 端末のベル。鳴るか・どの音かは端末の設定による
BELL = "\a"


class Screen:
    """出力へ書く。文の種類が変わるときは、行の途中なら改行してから書く。"""

    def __init__(self, output: TextIO, color: bool) -> None:
        self._output = output
        self._color = color
        self._kind: Kind = "text"
        self._at_line_start = True

    def write(self, text: str, kind: Kind = "text") -> None:
        """文をそのまま書く。"""
        if not text:
            return
        if kind != self._kind:
            self.end_line()
            self._kind = kind
        dim = self._color and kind != "text"
        self._output.write(f"{DIM}{text}{RESET}" if dim else text)
        self._output.flush()
        self._at_line_start = text.endswith("\n")

    def line(self, text: str, kind: Kind = "text") -> None:
        """1行を書く。行の途中なら、改行してから書く。"""
        self.end_line()
        self.write(text + "\n", kind)

    def end_line(self) -> None:
        """行の途中なら改行して、行の頭へ移る。"""
        if not self._at_line_start:
            self._output.write("\n")
            self._at_line_start = True

    def bell(self) -> None:
        """端末のベルを鳴らす。カーソルは動かない。"""
        self._output.write(BELL)
        self._output.flush()
