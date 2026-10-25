"""edit_file の置き換え元を、ファイルの中身から段階的に緩めて探す。

段は、そのまま → 行末の空白を除く → 字下げのずれを除く、の順である。合う所が見つかった最初の段で
止める。そのままの段は、文字列として探す（行の一部でもよい）。後の2つの段は、行の単位で比べ、
合った行の全体を置き換える。

中身は、改行を \\n に揃えてあるものとする。
"""

import difflib
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from itertools import accumulate
from os.path import commonprefix

from local_coding_agent.tools.lines import split_lines

EXACT = "そのまま"
TRAILING = "行末の空白を除く"
INDENT = "字下げのずれを除く"
STAGES = (EXACT, TRAILING, INDENT)

_BLANKS = " \t"
# read_file の結果の、行番号の形（右に寄せた行番号とタブ）
_LINE_NUMBER = re.compile(r"\s*\d+\t")

# 行の単位で比べる段の比べ方。ファイルの行の並び・old_string の行・new_string の行を受け、
# 合えば置き換えた後の行を、合わなければ None を返す
type _Rule = Callable[[Sequence[str], Sequence[str], Sequence[str]], list[str] | None]


@dataclass(frozen=True)
class Span:
    """置き換える所。中身の start 字目から end 字目の手前までを、replacement にする。"""

    start: int
    end: int
    replacement: str


@dataclass(frozen=True)
class Found:
    """ある段で見つかった所。"""

    stage: str
    # 合った所の全て。前から並び、重ならない
    spans: tuple[Span, ...]


@dataclass(frozen=True)
class Nearest:
    """置き換え元に最も近い所。"""

    # 始まりの行番号（1 から）
    line: int
    # 似ている度合い（difflib.SequenceMatcher の ratio。0 から 1）
    ratio: float
    lines: tuple[str, ...]


def find(text: str, old: str, new: str) -> Found | None:
    """段の順に探し、合う所が見つかった最初の段と、その段で合った全ての所を返す。

    どの段でも見つからなければ None。old は空でないものとする。
    """
    for stage, spans_of in _FINDERS:
        spans = spans_of(text, old, new)
        if spans:
            return Found(stage, spans)
    return None


def replace(text: str, spans: Sequence[Span]) -> str:
    """所を全て置き換えた中身。"""
    kept_starts = (0, *(span.end for span in spans))
    kept_ends = (*(span.start for span in spans), len(text))
    replacements = (*(span.replacement for span in spans), "")
    return "".join(
        text[start:end] + replacement
        for start, end, replacement in zip(kept_starts, kept_ends, replacements)
    )


def nearest(text: str, old: str) -> Nearest | None:
    """old と同じ行数の連続した行のうち、old に最も似ている所。中身が空なら None。"""
    lines = split_lines(text)
    if not lines:
        return None
    target = "\n".join(_rows(old))
    size = min(len(_rows(old)), len(lines))
    ratios = (
        (_ratio("\n".join(lines[index : index + size]), target), index)
        for index in range(len(lines) - size + 1)
    )
    ratio, index = max(ratios, key=lambda pair: pair[0])
    return Nearest(index + 1, ratio, tuple(lines[index : index + size]))


def has_line_numbers(old: str) -> bool:
    """old の空でない行が全て、read_file の結果の行番号の形で始まっているか。"""
    rows = [row for row in _rows(old) if row.strip()]
    return bool(rows) and all(_LINE_NUMBER.match(row) for row in rows)


def _exact(text: str, old: str, new: str) -> tuple[Span, ...]:
    return tuple(
        Span(match.start(), match.end(), new)
        for match in re.finditer(re.escape(old), text)
    )


def _line_spans(text: str, old: str, new: str, rule: _Rule) -> tuple[Span, ...]:
    """行の単位で、rule に合う所を前から探す。合った所の次の行から、続けて探す。"""
    lines = split_lines(text)
    # 行の始まりの位置。末尾の1つは、最後の行の改行の次の位置
    starts = tuple(accumulate((len(line) + 1 for line in lines), initial=0))
    old_rows = _rows(old)
    # new_string が空なら、合った行を除く
    new_rows = _rows(new) if new else []
    size = len(old_rows)
    spans: tuple[Span, ...] = ()
    index = 0
    while index + size <= len(lines):
        after = rule(lines[index : index + size], old_rows, new_rows)
        if after is None:
            index += 1
            continue
        # 合った行の最後に改行があれば、置き換えた後の行の最後にも付ける
        ending = "\n" if starts[index + size] <= len(text) else ""
        replacement = "\n".join(after) + ending if after else ""
        end = min(starts[index + size], len(text))
        spans = (*spans, Span(starts[index], end, replacement))
        index += size
    return spans


def _trailing(
    window: Sequence[str], old: Sequence[str], new: Sequence[str]
) -> list[str] | None:
    """行末の空白を除いて比べる。合えば new をそのまま置く。"""
    if all(
        line.rstrip(_BLANKS) == row.rstrip(_BLANKS) for line, row in zip(window, old)
    ):
        return list(new)
    return None


def _indented(
    window: Sequence[str], old: Sequence[str], new: Sequence[str]
) -> list[str] | None:
    """行末の空白と、行の並びに共通する字下げを除いて比べる。合えば new の字下げを直して置く。"""
    lines = [line.rstrip(_BLANKS) for line in window]
    rows = [row.rstrip(_BLANKS) for row in old]
    file_indent, old_indent = _common_indent(lines), _common_indent(rows)
    if any(
        line.removeprefix(file_indent) != row.removeprefix(old_indent)
        for line, row in zip(lines, rows)
    ):
        return None
    return [_reindented(row, old_indent, file_indent) for row in new]


def _common_indent(lines: Sequence[str]) -> str:
    """空でない行の全てに共通する、行頭の空白。"""
    indents = [line[: len(line) - len(line.lstrip(_BLANKS))] for line in lines if line]
    return commonprefix(indents) if indents else ""


def _reindented(row: str, old_indent: str, file_indent: str) -> str:
    """new_string の行の字下げを、old_string の字下げからファイルの字下げに替える。

    空の行と、old_string の字下げで始まらない行は、そのまま置く。
    """
    if not row.strip(_BLANKS) or not row.startswith(old_indent):
        return row
    return file_indent + row.removeprefix(old_indent)


def _rows(text: str) -> list[str]:
    """old_string・new_string を行に分ける。末尾の改行1つは無視する。"""
    return text.removesuffix("\n").split("\n")


def _ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


# 段と、その段で探す関数。find がこの順に探す
_FINDERS: tuple[tuple[str, Callable[[str, str, str], tuple[Span, ...]]], ...] = (
    (EXACT, _exact),
    (TRAILING, partial(_line_spans, rule=_trailing)),
    (INDENT, partial(_line_spans, rule=_indented)),
)
