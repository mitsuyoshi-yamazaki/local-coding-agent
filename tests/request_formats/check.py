"""見どころを、要求の本文と照らす。合わなければ RunError を投げ、文書を生成しない。"""

import json
import re
from collections.abc import Sequence

from tests.request_formats.harness import Body, RunError
from tests.request_formats.scenario import Highlight

# 場所の書き方の1つ: 欄の名前か、[番号]
_PART = re.compile(r"\[(\d+)\]|\.?([A-Za-z_]+)")


def parse_path(path: str) -> tuple[str | int, ...]:
    """場所の書き方（例: messages[1].content）を、欄の名前と番号の列にする。"""
    parts: tuple[str | int, ...] = ()
    position = 0
    while position < len(path):
        found = _PART.match(path, position)
        if found is None:
            raise RunError(f"場所の書き方が違う: {path}")
        index, name = found.groups()
        parts = (*parts, int(index) if index is not None else name)
        position = found.end()
    return parts


def value_at(body: Body, path: str) -> object:
    """本文の中の場所の値。無ければ RunError。"""
    value: object = body
    for part in parse_path(path):
        if isinstance(part, int) and isinstance(value, list) and part < len(value):
            value = value[part]
            continue
        if isinstance(part, str) and isinstance(value, dict) and part in value:
            value = value[part]
            continue
        raise RunError(f"本文に {path} が無い")
    return value


def check_highlight(highlight: Highlight, bodies: Sequence[Body]) -> None:
    """見どころの場所に、照らした文があるか（含まないはずの文が無いか・数が合うか）。"""
    where = f"要求 {highlight.request} の {highlight.path}"
    if not 1 <= highlight.request <= len(bodies):
        raise RunError(f"{highlight.info}: 要求 {highlight.request} が無い")
    value = value_at(bodies[highlight.request - 1], highlight.path)
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if highlight.contains and highlight.contains not in text:
        raise RunError(f"{highlight.info}: {where} に「{highlight.contains}」が無い")
    if highlight.excludes and highlight.excludes in text:
        raise RunError(f"{highlight.info}: {where} に「{highlight.excludes}」がある")
    count = highlight.count
    if count is not None and not (isinstance(value, list) and len(value) == count):
        raise RunError(f"{highlight.info}: {where} が {count} 個でない")
