"""文書 docs/request-formats.md を組み立てる。場面を全て走らせ、見どころを照らしてから書く。"""

import inspect
from collections.abc import Sequence
from pathlib import Path

from tests.request_formats.check import check_highlight
from tests.request_formats.commands import (
    BUILTINS,
    CUSTOM_COMMAND,
    SKILL_BY_MODEL,
    SKILL_BY_USER,
)
from tests.request_formats.conversation import (
    FIRST_REQUEST,
    INSTRUCTIONS_FILE,
    SECOND_TURN,
)
from tests.request_formats.harness import Body, RunError, run_scenario
from tests.request_formats.render import Reference, fenced, request_lines
from tests.request_formats.scenario import FRAME_WORDS, Highlight, Maker, Scenario
from tests.request_formats.text import FRAME_MEANINGS, HEAD, NOT_SENT, SCENARIOS_HEAD
from tests.request_formats.tool_use import STOPPED, TOOL_CALL, TOOL_RESULTS

SCENARIOS: tuple[Scenario, ...] = (
    FIRST_REQUEST,
    TOOL_CALL,
    TOOL_RESULTS,
    CUSTOM_COMMAND,
    SKILL_BY_MODEL,
    SKILL_BY_USER,
    BUILTINS,
    STOPPED,
    SECOND_TURN,
    INSTRUCTIONS_FILE,
)
REPOSITORY = Path(__file__).resolve().parents[2]
DOCUMENT = REPOSITORY / "docs" / "request-formats.md"

type Run = tuple[Scenario, tuple[Body, ...]]


def render_document() -> str:
    """場面を走らせ、見どころを照らし、文書の全体を返す。"""
    runs = tuple((scenario, run_scenario(scenario)) for scenario in SCENARIOS)
    for scenario, bodies in runs:
        for highlight in scenario.highlights:
            check_highlight(highlight, bodies)
    lines = [
        *HEAD,
        *_frames(),
        *_fields(runs),
        *_summary(runs),
        *SCENARIOS_HEAD,
        *_scenarios(runs),
        *_makers(runs),
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


def _frames() -> list[str]:
    rows = [f"| {FRAME_WORDS[frame]} | {text} |" for frame, text in FRAME_MEANINGS]
    return ["## 伝わり方の種類", "", "| 伝わり方 | 意味 |", "|---|---|", *rows, ""]


def _fields(runs: Sequence[Run]) -> list[str]:
    """送る欄（どれかの要求に出た欄）と、Ollama にあって送らない欄。"""
    sent = list(
        dict.fromkeys(key for _, bodies in runs for body in bodies for key in body)
    )
    present = [key for key, _ in NOT_SENT if key in sent]
    if present:
        raise RunError(f"送らないと書いた欄を送っている: {', '.join(present)}")
    return [
        "## 送る欄",
        "",
        "要求の本文の一番上の欄は、どの場面でも次のとおりである。",
        "",
        f"- 送る欄: {'・'.join(f'`{key}`' for key in sent)}",
        "- [Ollama](technologies/ollama.md) の `/api/chat` にあり、送らない欄:",
        *(f"  - `{key}`: {meaning}" for key, meaning in NOT_SENT),
        "",
    ]


def _summary(runs: Sequence[Run]) -> list[str]:
    rows = [
        f"| {number}. {scenario.title} | {_cell(h.info)} | {FRAME_WORDS[h.frame]} "
        f"| {_where(h)} | {_checked(h)} |"
        for number, (scenario, _) in enumerate(runs, start=1)
        for h in scenario.highlights
    ]
    return [
        "## 一覧",
        "",
        (
            "場面ごとの見どころ（ある情報が、要求のどこに、どの伝わり方で入るか）の全てである。"
            "照らした文は、生成のときに、その場所にあることを確かめた文である。"
        ),
        "",
        "| 場面 | 情報 | 伝わり方 | 場所 | 照らした文 |",
        "|---|---|---|---|---|",
        *rows,
        "",
    ]


def _scenarios(runs: Sequence[Run]) -> list[str]:
    base = Reference(runs[0][1][0], "場面 1")
    lines: list[str] = []
    for number, (scenario, bodies) in enumerate(runs, start=1):
        lines += _scenario_head(number, scenario)
        for index, body in enumerate(bodies, start=1):
            previous = (
                Reference(bodies[index - 2], f"要求 {index - 1}") if index > 1 else None
            )
            lines += request_lines(index, body, previous, None if number == 1 else base)
    return lines


def _scenario_head(number: int, scenario: Scenario) -> list[str]:
    lines = [f"### {number}. {scenario.title}", "", scenario.summary, ""]
    lines += ["打つ行（上から順に）:", ""]
    lines += [f"{index}. {_code(line)}" for index, line in enumerate(scenario.lines, 1)]
    lines.append("")
    if scenario.args:
        shown = " ".join(
            arg.replace("{directory}", "<作業ディレクトリ>") for arg in scenario.args
        )
        lines += [
            f"起動の引数（`--model` と `--directory` のほか）: {_code(shown)}",
            "",
        ]
    for path, text in scenario.files.items():
        lines += [
            f"作業ディレクトリに置くファイル {_code(path)}:",
            "",
            *fenced(text.rstrip("\n")),
            "",
        ]
    rows = [
        f"| {_cell(h.info)} | {FRAME_WORDS[h.frame]} | {_where(h)} | {_checked(h)} "
        f"| {'・'.join(_maker_link(maker) for maker in h.made_by)} |"
        for h in scenario.highlights
    ]
    header = [
        "| 情報 | 伝わり方 | 場所 | 照らした文 | 作る所 |",
        "|---|---|---|---|---|",
    ]
    return [*lines, "見どころ:", "", *header, *rows, ""]


def _makers(runs: Sequence[Run]) -> list[str]:
    """作る所の一覧。行の番号は、生成したときのコードのもの。"""
    makers = list(
        dict.fromkeys(m for s, _ in runs for h in s.highlights for m in h.made_by)
    )
    rows = [
        f"- [{_label(maker)}]({_source(maker)}#L{_line(maker)})" for maker in makers
    ]
    intro = "見どころの「作る所」の、生成したときのコードの行である。"
    return ["## 作る所", "", intro, "", *rows, ""]


def _where(highlight: Highlight) -> str:
    return f"要求 {highlight.request} の {_code(highlight.path)}"


def _checked(highlight: Highlight) -> str:
    parts = [
        *([_code(_escaped(highlight.contains))] if highlight.contains else []),
        *(
            [f"{_code(_escaped(highlight.excludes))} を含まない"]
            if highlight.excludes
            else []
        ),
        *([f"{highlight.count} 個"] if highlight.count is not None else []),
    ]
    return "・".join(parts)


def _escaped(text: str) -> str:
    """表の1つの欄に収まるよう、改行とタブを \\n・\\t と書く。"""
    return text.replace("\n", "\\n").replace("\t", "\\t")


def _code(text: str) -> str:
    """表の中でも崩れない、コードの書き方。"""
    ticks = "``" if "`" in text else "`"
    pad = " " if "`" in text else ""
    return f"{ticks}{pad}{text.replace('|', '\\|')}{pad}{ticks}"


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _maker_link(maker: Maker) -> str:
    return f"[{_label(maker)}]({_source(maker)})"


def _label(maker: Maker) -> str:
    return f"`{maker.__module__.rsplit('.', 1)[-1]}.{maker.__qualname__}`"


def _source(maker: Maker) -> str:
    """文書（docs/）から、コードのファイルへの相対パス。"""
    path = inspect.getsourcefile(maker)
    if path is None:
        raise RunError(f"{_label(maker)} のファイルが分からない")
    return "../" + Path(path).resolve().relative_to(REPOSITORY).as_posix()


def _line(maker: Maker) -> int:
    return inspect.getsourcelines(maker)[1]
