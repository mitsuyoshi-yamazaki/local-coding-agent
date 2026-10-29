"""要求の本文を、文書の行にする。

前の要求（場面の最初の要求では、場面 1 の最初の要求）と同じ所は省き、そう書く。改行を含む文は、
JSON の中では印（⟨文 1⟩ など）に替え、JSON の後にそのまま示す。
"""

import json
import re
from dataclasses import dataclass

from tests.request_formats.harness import Body

# 省いて書く欄。ほかの欄は、比べる要求と違うときだけ書く
LISTED = ("messages", "tools")


@dataclass(frozen=True)
class Reference:
    """省くときに比べる要求と、その呼び方（例: 要求 1・場面 1）。"""

    body: Body
    name: str


@dataclass(frozen=True)
class Part:
    """要求の一部の書き方: 説明の1行・その下に置く行・JSON で示す要素と、その始めの番号。"""

    note: str
    lines: tuple[str, ...] = ()
    items: tuple[object, ...] = ()
    start: int = 0


def text_mark(number: int) -> str:
    return f"⟨文 {number}⟩"


def fenced(text: str, language: str = "text") -> list[str]:
    """文をそのまま示す囲み。文の中の ` の並びより長い囲みにする。"""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return [fence + language, text, fence]


def request_lines(
    number: int, body: Body, previous: Reference | None, base: Reference | None
) -> list[str]:
    """要求1つの節。"""
    reference = previous if previous is not None else base
    tools = tools_part(body, reference)
    messages = messages_part(body, previous, base)
    notes = [*field_notes(body, reference), tools.note, messages.note]
    lines = [f"#### 要求 {number}", "", *(f"- {note}" for note in notes), ""]
    texts: list[tuple[str, str]] = []
    for name, part in (("tools", tools), ("messages", messages)):
        lines += [*part.lines, *_json_block(name, part, texts)]
    return lines


def field_notes(body: Body, reference: Reference | None) -> list[str]:
    """messages と tools のほかの欄。比べる要求と同じなら書かない。"""
    notes = [
        f"`{key}`: `{json.dumps(value, ensure_ascii=False)}`"
        for key, value in body.items()
        if key not in LISTED and (reference is None or reference.body.get(key) != value)
    ]
    if reference is not None:
        gone = [key for key in reference.body if key not in body]
        notes += [f"`{key}`: 送らない（{reference.name} では送った）" for key in gone]
    return notes


def tools_part(body: Body, reference: Reference | None) -> Part:
    tools = _list(body.get("tools"))
    if not tools:
        return Part("`tools`: 送らない")
    names = "・".join(_tool_name(tool) for tool in tools)
    known = _list(reference.body.get("tools")) if reference is not None else []
    if reference is not None and tools == known:
        return Part(f"`tools`: {reference.name} と同じ {len(tools)} 個（{names}）")
    if reference is not None and known and tools[: len(known)] == known:
        note = (
            f"`tools`: {len(tools)} 個（{names}）。"
            f"{reference.name} の {len(known)} 個の後に、{len(tools) - len(known)} 個を足した"
        )
        return Part(note, items=tuple(tools[len(known) :]), start=len(known))
    return Part(f"`tools`: {len(tools)} 個（{names}）", items=tuple(tools))


def messages_part(
    body: Body, previous: Reference | None, base: Reference | None
) -> Part:
    messages = _list(body.get("messages"))
    lead = f"`messages`: {len(messages)} 個"
    if previous is not None:
        earlier = _list(previous.body.get("messages"))
        if earlier and messages[: len(earlier)] == earlier:
            added = len(messages) - len(earlier)
            note = f"{lead}。{previous.name} の {len(earlier)} 個の後に、{added} 個を足した"
            return Part(note, items=tuple(messages[len(earlier) :]), start=len(earlier))
        return _with_system(
            f"{lead}（{previous.name} の続きではない）", messages, previous
        )
    if base is None:
        return Part(lead, items=tuple(messages))
    return _with_system(lead, messages, base)


def _with_system(lead: str, messages: list[object], reference: Reference) -> Part:
    """先頭の system の発言を、比べる要求の system の発言と比べて省く。"""
    known = _list(reference.body.get("messages"))
    if not messages or not known or _role(messages[0]) != "system":
        return Part(lead, items=tuple(messages))
    rest = tuple(messages[1:])
    if messages[0] == known[0]:
        note = f"{lead}。messages[0]（system の発言）は{reference.name} と同じ"
        return Part(note, items=rest, start=1)
    content, earlier = _content(messages[0]), _content(known[0])
    if not earlier or not content.startswith(earlier):
        return Part(lead, items=tuple(messages))
    added = content[len(earlier) :]
    shown = added.lstrip("\n")
    breaks = len(added) - len(shown)
    note = f"{lead}。messages[0]（system の発言）は、{reference.name} の content に文を足したもの"
    label = (
        f"`messages[0].content` は、{reference.name} の content の後に、"
        f"改行 {breaks} つを挟んで、次を足したもの:"
    )
    return Part(note, (label, "", *fenced(shown), ""), rest, 1)


def _json_block(name: str, part: Part, texts: list[tuple[str, str]]) -> list[str]:
    """part の要素を JSON にし、改行を含む文を後に示す。texts は要求の中で通しの番号を持つ。"""
    if not part.items:
        return []
    first = len(texts)
    shown = [
        _replace_texts(item, f"{name}[{part.start + index}]", texts)
        for index, item in enumerate(part.items)
    ]
    label = f"`{name}`:" if part.start == 0 else f"`{name}[{part.start}]` から:"
    lines = [
        label,
        "",
        *fenced(json.dumps(shown, ensure_ascii=False, indent=2), "json"),
        "",
    ]
    for number, (path, text) in enumerate(texts[first:], start=first + 1):
        lines += [f"{text_mark(number)}（`{path}`）:", "", *fenced(text), ""]
    return lines


def _replace_texts(value: object, path: str, texts: list[tuple[str, str]]) -> object:
    if isinstance(value, str) and "\n" in value:
        texts.append((path, value))
        return text_mark(len(texts))
    if isinstance(value, dict):
        return {
            key: _replace_texts(item, f"{path}.{key}", texts)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _replace_texts(item, f"{path}[{index}]", texts)
            for index, item in enumerate(value)
        ]
    return value


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _role(message: object) -> object:
    return message.get("role") if isinstance(message, dict) else None


def _content(message: object) -> str:
    content = message.get("content") if isinstance(message, dict) else None
    return content if isinstance(content, str) else ""


def _tool_name(tool: object) -> str:
    function = tool.get("function") if isinstance(tool, dict) else None
    name = function.get("name") if isinstance(function, dict) else None
    return name if isinstance(name, str) else "?"
