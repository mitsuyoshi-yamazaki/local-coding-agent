import difflib
import unittest

from tests.request_formats.check import check_highlight, parse_path
from tests.request_formats.document import DOCUMENT, render_document
from tests.request_formats.harness import Body, RunError
from tests.request_formats.render import Reference, messages_part, tools_part
from tests.request_formats.scenario import Highlight
from tests.request_formats.text import GENERATE

# 食い違いのときに出す差分の行数の上限
DIFF_LINES = 80


class DocumentTest(unittest.TestCase):
    def test_document_is_generated_from_current_code(self) -> None:
        expected = render_document()
        actual = DOCUMENT.read_text(encoding="utf-8")
        if actual == expected:
            return
        diff = difflib.unified_diff(
            actual.splitlines(),
            expected.splitlines(),
            "commit した文書",
            "今のコードから生成した文書",
            lineterm="",
        )
        shown = "\n".join(list(diff)[:DIFF_LINES])
        self.fail(
            f"{DOCUMENT.name} が今のコードと合わない。{GENERATE} で生成し直す。\n{shown}"
        )


MESSAGES: list[object] = [
    {"role": "system", "content": "指示"},
    {"role": "user", "content": "<metadata>\n</metadata>\n依頼"},
]
BODY: Body = {"messages": MESSAGES}


def highlight(
    path: str = "messages[1].content",
    contains: str = "",
    excludes: str = "",
    count: int | None = None,
) -> Highlight:
    return Highlight(
        "依頼", "frame", 1, path, contains=contains, excludes=excludes, count=count
    )


class CheckTest(unittest.TestCase):
    def test_path_is_names_and_indexes(self) -> None:
        self.assertEqual(
            parse_path("tools[5].function.name"), ("tools", 5, "function", "name")
        )

    def test_bad_path_fails(self) -> None:
        with self.assertRaises(RunError):
            parse_path("messages[x]")

    def test_contained_text_passes(self) -> None:
        check_highlight(highlight(contains="依頼"), (BODY,))

    def test_missing_text_fails(self) -> None:
        with self.assertRaises(RunError):
            check_highlight(highlight(contains="答え"), (BODY,))

    def test_excluded_text_fails(self) -> None:
        with self.assertRaises(RunError):
            check_highlight(highlight(excludes="metadata"), (BODY,))

    def test_count_of_list(self) -> None:
        check_highlight(highlight(path="messages", count=2), (BODY,))
        with self.assertRaises(RunError):
            check_highlight(highlight(path="messages", count=3), (BODY,))

    def test_missing_place_fails(self) -> None:
        with self.assertRaises(RunError):
            check_highlight(highlight(path="messages[2].content"), (BODY,))

    def test_missing_request_fails(self) -> None:
        with self.assertRaises(RunError):
            check_highlight(highlight(contains="依頼"), ())


def tool(name: str) -> dict[str, object]:
    return {"type": "function", "function": {"name": name}}


class RenderTest(unittest.TestCase):
    def test_continued_messages_show_only_added(self) -> None:
        later: Body = {"messages": [*MESSAGES, {"role": "assistant"}]}
        part = messages_part(later, Reference(BODY, "要求 1"), None)
        self.assertEqual(part.items, ({"role": "assistant"},))
        self.assertEqual(part.start, 2)

    def test_same_system_is_omitted(self) -> None:
        other: Body = {
            "messages": [{"role": "system", "content": "指示"}, {"role": "user"}]
        }
        part = messages_part(other, None, Reference(BODY, "場面 1"))
        self.assertEqual(part.items, ({"role": "user"},))
        self.assertIn("場面 1 と同じ", part.note)

    def test_added_system_text_is_shown(self) -> None:
        other: Body = {"messages": [{"role": "system", "content": "指示\n\n# スキル"}]}
        part = messages_part(other, None, Reference(BODY, "場面 1"))
        self.assertIn("# スキル", part.lines)
        self.assertIn("改行 2 つを挟んで", part.lines[0])

    def test_added_tools_are_shown(self) -> None:
        earlier: Body = {"tools": [tool("a")]}
        part = tools_part(
            {"tools": [tool("a"), tool("b")]}, Reference(earlier, "場面 1")
        )
        self.assertEqual(part.items, (tool("b"),))
        self.assertEqual(part.start, 1)


if __name__ == "__main__":
    unittest.main()
