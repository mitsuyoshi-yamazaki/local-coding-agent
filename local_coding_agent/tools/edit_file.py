"""道具 edit_file: ファイルの中の old_string を new_string に置き換える。

置き換え元は、そのまま → 行末の空白を除く → 字下げのずれを除く、の順に緩めて探す
（tools/text_match.py）。結果には、見つけた段を書く。見つからなければ、最も近い所を添えて
誤りを返す。どちらも、編集の失敗が内容の誤りか写し間違いかを、走行の記録から見分けるためである。
"""

from collections.abc import Sequence
from itertools import accumulate
from pathlib import Path
from typing import cast

from local_coding_agent.model.chat import ToolDefinition
from local_coding_agent.tools.file_change import (
    FileChange,
    checked,
    file_tool,
    read_current,
)
from local_coding_agent.tools.lines import numbered, split_lines
from local_coding_agent.tools.text_match import (
    STAGES,
    Found,
    Span,
    find,
    has_line_numbers,
    nearest,
    replace,
)
from local_coding_agent.tools.tool import ToolError, ToolInput, resolve

# 結果に添える、置き換えた所の前後の行数
CONTEXT_LINES = 3
# 最も近い所の行を添える、似ている度合いの下限（Aider の find_similar_lines と同じ）
NEAR_RATIO = 0.6
LINE_NUMBER_HINT = (
    "old_string の行が、read_file の結果の行番号とタブで始まっている。"
    "行番号とタブは除いて写す"
)

DEFINITION = ToolDefinition(
    name="edit_file",
    description=(
        "ファイルの中の old_string を new_string に置き換える。"
        "old_string は、read_file の結果から行番号とタブを除き、字下げと空白を含めてそのまま写す。"
        "old_string がファイルの中の1か所だけに合うよう、前後の行を含める。"
        "合う所を全て置き換えるときは replace_all に true を渡す。"
        "そのままでは見つからないときは、行末の空白と字下げのずれを除いて探す。"
        "新しいファイルは write_file で作る。実行の前に、利用者が差分を見て確かめる。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "直すファイル。作業ディレクトリからの相対パスか、絶対パス",
            },
            "old_string": {"type": "string", "description": "置き換える元"},
            "new_string": {"type": "string", "description": "置き換えた後"},
            "replace_all": {
                "type": "boolean",
                "description": "true なら、合う所を全て置き換える。既定は false",
            },
        },
        "required": ["path", "old_string", "new_string"],
    },
)


def plan(arguments: ToolInput, cwd: Path) -> FileChange:
    """置き換え元を探し、書く前と後の中身を組み立てる。"""
    # 入力は、実行の前に定義と照らしてある
    path = cast(str, arguments["path"])
    old = cast(str, arguments["old_string"]).replace("\r\n", "\n")
    new = cast(str, arguments["new_string"]).replace("\r\n", "\n")
    replace_all = cast(bool, arguments.get("replace_all", False))
    if not old:
        raise ToolError("old_string が空である（新しいファイルは write_file で作る）")
    if old == new:
        raise ToolError("old_string と new_string が同じである")
    target = resolve(cwd, path)
    current = read_current(target, path)
    if current is None:
        raise ToolError(f"ファイルが無い: {path}（新しいファイルは write_file で作る）")
    text, newline = current
    found = find(text, old, new)
    if found is None:
        raise ToolError(_not_found(path, text, old))
    if len(found.spans) > 1 and not replace_all:
        raise ToolError(_ambiguous(text, found))
    after = replace(text, found.spans)
    result = _result(path, after, found)
    return checked(FileChange(target, path, text, after, newline, result))


def _result(path: str, after: str, found: Found) -> str:
    """置き換えた行と段。1か所なら、置き換えた所の前後の行を添える。"""
    placed = _placed(found.spans)
    if len(placed) > 1:
        lines = "・".join(str(_line_of(after, start)) for start, _ in placed)
        where = f"{len(placed)} か所（{lines} 行目。段: {found.stage}）"
        return f"置き換えた: {path} の {where}"
    start, end = placed[0]
    first, last = _line_of(after, start), _line_of(after, max(start, end - 1))
    lines = f"{first} 行目" if first == last else f"{first}〜{last} 行目"
    head = f"置き換えた: {path} の {lines}（段: {found.stage}）"
    return "\n".join((head, *_around(after, first, last)))


def _placed(spans: Sequence[Span]) -> list[tuple[int, int]]:
    """置き換えた後の中身での、各所の始まりと終わりの位置。"""
    growths = (len(span.replacement) - (span.end - span.start) for span in spans)
    shifts = accumulate(growths, initial=0)
    return [
        (span.start + shift, span.start + shift + len(span.replacement))
        for span, shift in zip(spans, shifts)
    ]


def _around(text: str, first: int, last: int) -> list[str]:
    """first 行目から last 行目と、その前後の行に、行番号を付けたもの。"""
    lines = split_lines(text)
    start = max(1, first - CONTEXT_LINES)
    end = min(len(lines), last + CONTEXT_LINES)
    return [numbered(number, lines[number - 1]) for number in range(start, end + 1)]


def _ambiguous(text: str, found: Found) -> str:
    lines = "・".join(str(_line_of(text, span.start)) for span in found.spans)
    return (
        f"old_string が {len(found.spans)} か所に合う（段: {found.stage}。{lines} 行目）。"
        "前後の行を old_string に足して1か所に絞るか、replace_all に true を渡す"
    )


def _not_found(path: str, text: str, old: str) -> str:
    """見つからなかったことと、最も近い所と、行番号の写し込みの知らせ。"""
    stages = "・".join(STAGES)
    head = f"置き換え元が見つからない: {path}（{stages}、の{len(STAGES)}段で探した）"
    hint = [LINE_NUMBER_HINT] if has_line_numbers(old) else []
    return "\n".join((head, *_nearest_lines(text, old), *hint))


def _nearest_lines(text: str, old: str) -> list[str]:
    near = nearest(text, old)
    if near is None:
        return ["ファイルは空である"]
    if near.ratio < NEAR_RATIO:
        ratio = f"{near.ratio:.2f}（{near.line} 行目）"
        return [
            f"最も近い所でも、似ている度合いは {ratio}。ファイルを read_file で読み直す"
        ]
    last = near.line + len(near.lines) - 1
    lines = f"{near.line} 行目" if near.line == last else f"{near.line}〜{last} 行目"
    return [
        f"最も近いのは {lines}（似ている度合い {near.ratio:.2f}）:",
        *(numbered(near.line + index, line) for index, line in enumerate(near.lines)),
    ]


def _line_of(text: str, position: int) -> int:
    """position 字目がある行の番号（1 から）。"""
    return text.count("\n", 0, position) + 1


TOOL = file_tool(DEFINITION, plan)
