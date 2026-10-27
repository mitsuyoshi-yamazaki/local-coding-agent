"""コマンドを、許可の規則と照らす部分に分ける。

引用符（'…'・"…"・$'…'）の外の &&・||・;・|・&・改行で分ける。リダイレクトの >&・&>・<&
（2>&1 など）の & では分けない。分けた部分は、空白の並びを1つの空白にし、頭のグループの括弧・
否定・予約語（( { ! if then do など）を除く。シェルの文法を全て解くのではなく、規則と照らすのに
要る所だけを見る。
"""

import re
from collections.abc import Iterator

# 長いものを先に置く（&& を & と & に分けないため）
SEPARATORS = ("&&", "||", ";", "|", "&", "\n")
# 中で走るコマンドを照らせない書き方（コマンド置換とプロセス置換）
SUBSTITUTIONS = ("$(", "`", "<(", ">(")
# 部分の頭にあっても、走るコマンドの名前ではないもの（グループの括弧・否定・予約語）
_PREFIX = re.compile(r"^(?:[({!]\s*|(?:if|then|do|else|elif|while|until|time)\s+)+")


def split_command(command: str) -> tuple[str, ...]:
    """コマンドを部分に分け、それぞれを整える。空になった部分は捨てる。"""
    cuts = tuple(_separators(command))
    starts = (0, *(position + width for position, width in cuts))
    ends = (*(position for position, _ in cuts), len(command))
    parts = (_tidy(command[start:end]) for start, end in zip(starts, ends))
    return tuple(part for part in parts if part)


def tidy_spaces(text: str) -> str:
    """空白（タブと改行も）の並びを1つの空白にし、前後の空白を除く。"""
    return " ".join(text.split())


def _tidy(part: str) -> str:
    """部分を、規則と照らす形にする。(rm x) と do rm x は、rm x) と rm x になる。"""
    return _PREFIX.sub("", tidy_spaces(part))


def has_substitution(command: str) -> bool:
    """コマンド置換かプロセス置換の書き方を含むか。引用符の中も見る（安全な側に倒す）。"""
    return any(mark in command for mark in SUBSTITUTIONS)


def _separators(command: str) -> Iterator[tuple[int, int]]:
    """引用符の外の区切りの、位置と字数。

    quote は、今いる引用符の始まり（' か " か $'）。閉じる字は、どれも最後の字である。
    index は、下の行で1字（区切りならその字数）進む。バックスラッシュと $' では、その前に
    1字進めておき、合わせて2字進む。
    """
    quote: str | None = None
    index = 0
    while index < len(command):
        char = command[index]
        width = 0
        if quote == "'":
            # '…' の中では、\ も特別ではない
            quote = None if char == "'" else quote
        elif char == "\\":
            # 次の字は、区切りにも引用符にもならない（"…" と $'…' の中でも）
            index += 1
        elif quote is not None:
            quote = None if char == quote[-1] else quote
        elif command.startswith("$'", index):
            quote = "$'"
            index += 1
        elif char in "'\"":
            quote = char
        else:
            width = _separator_width(command, index)
        if width:
            yield index, width
        index += max(width, 1)


def _separator_width(command: str, index: int) -> int:
    """index から始まる区切りの字数。区切りでなければ 0。"""
    for separator in SEPARATORS:
        if command.startswith(separator, index):
            if separator == "&" and _is_redirect(command, index):
                return 0
            return len(separator)
    return 0


def _is_redirect(command: str, index: int) -> bool:
    """index の & が、リダイレクト（>&・<&・&>）の一部か。"""
    before = command[index - 1] if index > 0 else ""
    after = command[index + 1 : index + 2]
    return before in ("<", ">") or after == ">"
