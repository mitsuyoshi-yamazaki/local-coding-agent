"""許可の規則: 書き方の読み取りと、型と文字列の照合。

規則は「道具の名前」か「道具の名前(型)」の文字列である。型の * は、0字以上の任意の字
（/ と空白も含む）に合う。型が「 *」か「/*」で終わるときは、その2字が無いものにも合う。

ファイルの道具の型とパスは、どちらも絶対パスに解いてから照らす（.. とシンボリックリンクを
解く）。型は、規則を読むときに1度だけ解く。
"""

import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from local_coding_agent.permissions.command import tidy_spaces
from local_coding_agent.tools.tool import Tool

# 型の末尾にあるとき、その2字が無いものにも合う
OPTIONAL_ENDS = (" *", "/*")
_FORM = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\((.*)\))?", re.DOTALL)


class RuleError(ValueError):
    """規則の書き方の誤り。"""


@dataclass(frozen=True)
class Rule:
    """規則1つ。"""

    tool: str
    # 照らす型。ファイルの道具なら絶対パスに解いたもの。名前だけの規則なら None
    pattern: str | None
    # 利用者が書いたままの規則。表示と走行の記録に使う
    text: str

    def __str__(self) -> str:
        return self.text


def parse_rule(text: str, tools: Sequence[Tool], cwd: Path, home: Path) -> Rule:
    """規則の文字列を読む。ファイルの道具の型は、cwd と home から絶対パスに解く。"""
    form = _FORM.fullmatch(text)
    if form is None:
        message = f"規則の形が違う（「道具の名前」か「道具の名前(型)」）: {text}"
        raise RuleError(message)
    name, pattern = form.group(1), form.group(2)
    tool = next((tool for tool in tools if tool.name == name), None)
    if tool is None:
        names = ", ".join(tool.name for tool in tools)
        raise RuleError(f"知らない道具の名前: {name}（使える道具: {names}）")
    if pattern is None:
        return Rule(name, None, text)
    if not pattern:
        raise RuleError(f"型が空である: {text}")
    if tool.kind == "command":
        # コマンドの部分と同じく、空白の並びを1つの空白にしてから照らす
        return Rule(name, tidy_spaces(pattern), text)
    return Rule(name, resolve_pattern(pattern, cwd, home), text)


def matches(pattern: str, text: str) -> bool:
    """型が、文字列の全体に合うか。"""
    return _regex(pattern).fullmatch(text) is not None


def _regex(pattern: str) -> re.Pattern[str]:
    """型を正規表現にする。* は任意の字、末尾の「 *」「/*」は無くてもよい。"""
    body, rest = pattern, ""
    for end in OPTIONAL_ENDS:
        if len(pattern) > len(end) and pattern.endswith(end):
            body, rest = pattern[: -len(end)], f"(?:{re.escape(end[0])}.*)?"
            break
    stars = ".*".join(re.escape(part) for part in body.split("*"))
    return re.compile(stars + rest, re.DOTALL)


def resolve_target(path: str, cwd: Path) -> Path:
    """道具が受けたパスを、作業ディレクトリから解き、.. とシンボリックリンクを解いた絶対パスにする。"""
    return _resolve(cwd / path)


def resolve_pattern(pattern: str, cwd: Path, home: Path) -> str:
    """ファイルの道具の型を、絶対パスの型にする。

    / で始まれば絶対パス、~/ で始まれば home から、それ以外は cwd からとする。
    * が無ければ全体を、あれば最初の * より前のディレクトリの部分を、道具のパスと同じく解く
    （.. とシンボリックリンク）。* より後ろの .. は解かない。
    """
    if pattern.startswith("~/"):
        absolute = os.path.join(home, pattern[2:])
    else:
        # pattern が / で始まれば、join は cwd を捨てる
        absolute = os.path.join(cwd, pattern)
    head, star, tail = absolute.partition("*")
    if not star:
        return str(_resolve(Path(absolute)))
    directory, slash, name = head.rpartition("/")
    resolved = str(_resolve(Path(directory or "/"))).rstrip("/")
    return f"{resolved}{slash}{name}{star}{tail}"


def inside(path: Path, cwd: Path) -> bool:
    """解いたパスが、作業ディレクトリそのものか、その下にあるか。"""
    return path.is_relative_to(_resolve(cwd))


def _resolve(path: Path) -> Path:
    """.. とシンボリックリンクを解いた絶対パス。解けなければ（NUL の字など）、.. だけを解く。"""
    try:
        return path.resolve()
    except OSError, ValueError, RuntimeError:
        return Path(os.path.abspath(path))
