"""許可の設定ファイル（作業ディレクトリの .local-coding-agent/settings.json）を読む。

起動のときに1度だけ読む。無ければ、既定のモード（allow-all）で、規則は無し。形が違えば
SettingsError を投げ、起動しない。形は次のとおりで、どの欄も省ける。

    {"permissions": {"mode": "ask", "allow": [...], "ask": [...], "deny": [...]}}

規則の並びの要素は、規則の文字列か、理由を添えた {"rule": "<規則>", "reason": "<理由>"}。
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from local_coding_agent.permissions.policy import (
    MODES,
    Mode,
    Permissions,
    is_mode,
)
from local_coding_agent.permissions.rules import Rule, RuleError, parse_rule
from local_coding_agent.tools.tool import Tool

SETTINGS_PATH = Path(".local-coding-agent") / "settings.json"
LISTS = ("allow", "ask", "deny")
_SECTION_KEYS = ("mode", *LISTS)
_RULE_KEYS = ("rule", "reason")


class SettingsError(Exception):
    """設定ファイルを読めない・形が違う。文は、起動の前に人に見せる。"""


@dataclass(frozen=True)
class LoadedPermissions:
    """読んだ許可の設定。"""

    permissions: Permissions
    # 読んだ設定ファイル（作業ディレクトリからのパス）。無ければ None
    source: Path | None


def load_permissions(
    cwd: Path, tools: Sequence[Tool], home: Path, mode: Mode | None = None
) -> LoadedPermissions:
    """作業ディレクトリの設定ファイルを読む。mode を渡せば、ファイルのモードを上書きする。"""
    raw = _read_json(cwd / SETTINGS_PATH)
    permissions = Permissions() if raw is None else _permissions(raw, tools, cwd, home)
    if mode is not None:
        permissions = replace(permissions, mode=mode)
    return LoadedPermissions(permissions, None if raw is None else SETTINGS_PATH)


def describe(loaded: LoadedPermissions) -> str:
    """起動のときに出す1行。"""
    permissions = loaded.permissions
    count = len(permissions.allow) + len(permissions.ask) + len(permissions.deny)
    source = "設定ファイル無し" if loaded.source is None else str(loaded.source)
    return f"許可: {permissions.mode}・規則 {count}（{source}）"


def trace_record(loaded: LoadedPermissions) -> dict[str, object]:
    """走行の記録に、起動のときに書く1件。"""
    permissions = loaded.permissions
    return {
        "type": "permissions",
        "mode": permissions.mode,
        "source": None if loaded.source is None else str(loaded.source),
        "allow": [_rule_record(rule) for rule in permissions.allow],
        "ask": [_rule_record(rule) for rule in permissions.ask],
        "deny": [_rule_record(rule) for rule in permissions.deny],
    }


def _rule_record(rule: Rule) -> object:
    """記録の規則1つ。設定ファイルに書いたのと同じ形にする。"""
    if rule.reason is None:
        return str(rule)
    return {"rule": str(rule), "reason": rule.reason}


def _read_json(path: Path) -> object | None:
    """ファイルの JSON。ファイルが無ければ None。"""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as error:
        raise SettingsError(f"読めない: {error}") from None
    try:
        value: object = json.loads(text)
    except (ValueError, RecursionError) as error:
        # ValueError は JSONDecodeError と、桁の多すぎる数。RecursionError は深すぎる入れ子
        raise SettingsError(f"JSON として読めない: {error}") from None
    return value


def _permissions(
    raw: object, tools: Sequence[Tool], cwd: Path, home: Path
) -> Permissions:
    top = _object(raw, "設定ファイルの全体", ("permissions",))
    section = _object(top.get("permissions", {}), "permissions", _SECTION_KEYS)
    mode = section.get("mode", Permissions().mode)
    if not is_mode(mode):
        choices = "・".join(MODES)
        shown = json.dumps(mode, ensure_ascii=False)
        raise SettingsError(
            f"permissions.mode は {choices} のどれか（受けた値: {shown}）"
        )
    allow, ask, deny = (
        _rules(section.get(name, []), name, tools, cwd, home) for name in LISTS
    )
    return Permissions(mode, allow, ask, deny)


def _object(value: object, name: str, keys: Sequence[str]) -> Mapping[str, object]:
    """JSON のオブジェクトで、keys のほかの欄を持たないもの。"""
    if not isinstance(value, dict):
        raise SettingsError(f"{name} は JSON のオブジェクトでなければならない")
    unknown = [key for key in value if key not in keys]
    if unknown:
        raise SettingsError(f"{name} に知らない欄がある: {', '.join(unknown)}")
    return value


def _rules(
    value: object, name: str, tools: Sequence[Tool], cwd: Path, home: Path
) -> tuple[Rule, ...]:
    """規則の並び。形が違えば、または規則の書き方が違えば SettingsError。"""
    if not isinstance(value, list):
        raise SettingsError(_shape_message(name))
    return tuple(_rule(item, name, tools, cwd, home) for item in value)


def _rule(
    item: object, name: str, tools: Sequence[Tool], cwd: Path, home: Path
) -> Rule:
    text, reason = _rule_parts(item, name)
    try:
        rule = parse_rule(text, tools, cwd, home)
    except RuleError as error:
        raise SettingsError(f"permissions.{name}: {error}") from None
    return replace(rule, reason=reason)


def _rule_parts(item: object, name: str) -> tuple[str, str | None]:
    """並びの要素から、規則の文字列と理由を取り出す。"""
    if isinstance(item, str):
        return item, None
    if not isinstance(item, dict):
        raise SettingsError(_shape_message(name))
    fields = _object(item, f"permissions.{name} の規則", _RULE_KEYS)
    text, reason = fields.get("rule"), fields.get("reason")
    if not isinstance(text, str):
        raise SettingsError(f"permissions.{name} の規則に、rule（規則の文字列）が無い")
    if not isinstance(reason, str) or not reason:
        message = (
            f"permissions.{name} の規則の reason は、空でない文字列でなければならない"
        )
        raise SettingsError(message)
    return text, reason


def _shape_message(name: str) -> str:
    return (
        f"permissions.{name} は、規則の文字列か "
        '{"rule": <規則>, "reason": <理由>} の並びでなければならない'
    )
