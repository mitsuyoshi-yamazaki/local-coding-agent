"""許可の判定: 道具の呼び出しを、通す・問う・拒むのどれかに決める。

規則を deny → ask → allow の順に照らし、最初に合ったもので決める。どれにも合わなければ、
モードと道具の種類で決める。判定するのはハーネスで、モデルは関わらない。
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeIs

from local_coding_agent.permissions.command import has_substitution, split_command
from local_coding_agent.permissions.rules import (
    Rule,
    inside,
    matches,
    resolve_target,
)
from local_coding_agent.tools.tool import Tool, ToolInput

type Mode = Literal["ask", "accept-edits", "allow-all"]
type Verdict = Literal["allow", "ask", "deny"]

MODES: tuple[Mode, ...] = ("ask", "accept-edits", "allow-all")
DEFAULT_MODE: Mode = "allow-all"
# 画面に出す、判定の言葉
VERDICT_WORDS: dict[Verdict, str] = {"allow": "通す", "ask": "問う", "deny": "拒む"}
# 規則で拒んだときに、モデルに返す結果の始まり
DENIED = "規則で拒んだ"
# 規則で拒んだときに、モデルに返す結果の終わり。拒んだ意図と、次にすることを伝える
DENIED_NOTE = (
    "利用者がこの操作を禁じている。同じ目的を、別のコマンドや道具で果たそうとしない。"
    "要るなら、利用者に尋ねる"
)


def is_mode(value: object) -> TypeIs[Mode]:
    return value in MODES


@dataclass(frozen=True)
class Permissions:
    """モードと規則の組。起動のときに1度作り、会話の間は変えない。"""

    mode: Mode = DEFAULT_MODE
    allow: tuple[Rule, ...] = ()
    ask: tuple[Rule, ...] = ()
    deny: tuple[Rule, ...] = ()


@dataclass(frozen=True)
class Decision:
    """判定。"""

    verdict: Verdict
    # 人に見せ、走行の記録に書く理由（例: 「規則 deny: run_command(rm *)」「モード ask」）
    reason: str
    # 合った規則。モードで決めたなら None
    rule: str | None = None
    # 合った規則（deny か ask）に、利用者が添えた理由。無ければ None
    rule_reason: str | None = None


@dataclass(frozen=True)
class _Call:
    """規則と照らすための、呼び出しの姿。"""

    tool: Tool
    # 型と照らす文字列（解いたパス1つか、分けたコマンドの部分）。持たない道具なら空
    texts: tuple[str, ...]
    # 型を持つ allow の規則を当ててよいか（コマンド置換を含むコマンドには当てない）
    allow_patterns: bool
    # 作業ディレクトリの中か。パスを持たない道具なら None
    inside: bool | None


def decide(
    permissions: Permissions, tool: Tool, arguments: ToolInput, cwd: Path
) -> Decision:
    """呼び出しを判定する。入力は、定義と照らしてあるものとする。"""
    call = _call(tool, arguments, cwd)
    lists: tuple[tuple[Verdict, tuple[Rule, ...]], ...] = (
        ("deny", permissions.deny),
        ("ask", permissions.ask),
    )
    for verdict, rules in lists:
        hit = next((rule for rule in rules if _hits_any(rule, call)), None)
        if hit is not None:
            return Decision(verdict, f"規則 {verdict}: {hit}", str(hit), hit.reason)
    allowed = _allowed_by(permissions.allow, call)
    if allowed:
        names = "・".join(str(rule) for rule in allowed)
        return Decision("allow", f"規則 allow: {names}", names)
    return _by_mode(permissions.mode, tool, call.inside)


def denial(decision: Decision) -> str:
    """規則で拒んだときに、モデルに返す結果の文。

    合った規則・規則の * の意味（シェルのワイルドカードと読まれないため）・利用者が添えた
    理由・拒んだ意図と次にすることを、この順に並べる。
    """
    rule = decision.rule or ""
    star = "（規則の * は任意の文字列を表す）" if "*" in rule else ""
    reason = f"理由: {decision.rule_reason}。" if decision.rule_reason else ""
    return f"{DENIED}: {rule}{star}。{reason}{DENIED_NOTE}"


def _call(tool: Tool, arguments: ToolInput, cwd: Path) -> _Call:
    if tool.target is None:
        return _Call(tool, (), True, None)
    text = tool.target(arguments)
    if tool.kind == "command":
        return _Call(tool, split_command(text), not has_substitution(text), None)
    path = resolve_target(text, cwd)
    return _Call(tool, (str(path),), True, inside(path, cwd))


def _hits(rule: Rule, text: str) -> bool:
    """規則が、呼び出しの文字列の1つに合うか。道具の名前は、呼ぶ側が見ておく。"""
    return rule.pattern is None or matches(rule.pattern, text)


def _hits_any(rule: Rule, call: _Call) -> bool:
    """deny と ask の規則: 名前だけの規則か、文字列のどれか1つに合えば合う。"""
    if rule.tool != call.tool.name:
        return False
    return rule.pattern is None or any(_hits(rule, text) for text in call.texts)


def _allowed_by(rules: Sequence[Rule], call: _Call) -> tuple[Rule, ...]:
    """allow の規則: 文字列の全てが、それぞれどれかの規則に合えば、合った規則を返す。

    合わなければ空。名前だけの規則は、それ1つで全てに合う。
    """
    mine = tuple(rule for rule in rules if rule.tool == call.tool.name)
    bare = next((rule for rule in mine if rule.pattern is None), None)
    if bare is not None:
        return (bare,)
    if not call.allow_patterns or not call.texts:
        return ()
    found = tuple(
        next((rule for rule in mine if _hits(rule, text)), None) for text in call.texts
    )
    if None in found:
        return ()
    # 同じ規則が複数の部分に合ったら、1つにまとめる
    return tuple(dict.fromkeys(rule for rule in found if rule is not None))


def _by_mode(mode: Mode, tool: Tool, inside: bool | None) -> Decision:
    """規則のどれにも合わないときの判定。"""
    reason = f"モード {mode}"
    if mode == "allow-all":
        return Decision("allow", reason)
    if inside is False:
        return Decision("ask", f"{reason}・作業ディレクトリの外")
    if tool.kind == "read" or (tool.kind == "edit" and mode == "accept-edits"):
        return Decision("allow", reason)
    return Decision("ask", reason)
