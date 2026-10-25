import io
import unittest

from local_coding_agent.loop.turn import run_turn
from local_coding_agent.model.chat import Done, ToolCall
from local_coding_agent.model.messages import ToolResultBlock
from local_coding_agent.tools import edit_file, write_file
from local_coding_agent.tools.default import DEFAULT_TOOLS
from local_coding_agent.tools.tool import ToolError, ToolInput
from tests.fakes import ScriptedLines, ScriptedModel, fake_session
from tests.test_tools import ToolTestCase

STOP = Done(done_reason="stop", stats={})


class WriteFileTest(ToolTestCase):
    def run_tool(self, path: str, content: str) -> str:
        return write_file.TOOL.run({"path": path, "content": content}, self.cwd)

    def test_new_file_and_parent_directory(self) -> None:
        result = self.run_tool("src/a.py", "x\ny\n")
        self.assertEqual(result, "新しいファイルを書いた: src/a.py（2 行）")
        self.assertEqual((self.cwd / "src/a.py").read_text(encoding="utf-8"), "x\ny\n")

    def test_overwrites(self) -> None:
        self.write("a.txt", "古い\n")
        self.assertEqual(
            self.run_tool("a.txt", "新しい\n"), "上書きした: a.txt（1 行）"
        )
        self.assertEqual((self.cwd / "a.txt").read_text(encoding="utf-8"), "新しい\n")

    def test_preview_of_new_file_does_not_write(self) -> None:
        preview = write_file.TOOL.preview
        assert preview is not None
        diff = preview({"path": "a.txt", "content": "x\ny\n"}, self.cwd)
        self.assertEqual(diff, "--- /dev/null\n+++ a.txt\n@@ -0,0 +1,2 @@\n+x\n+y")
        self.assertFalse((self.cwd / "a.txt").exists())

    def test_keeps_crlf(self) -> None:
        (self.cwd / "a.txt").write_bytes(b"a\r\nb\r\n")
        self.run_tool("a.txt", "a\nc\n")
        self.assertEqual((self.cwd / "a.txt").read_bytes(), b"a\r\nc\r\n")

    def test_preview_shows_change_of_last_newline(self) -> None:
        self.write("a.txt", "a")
        preview = write_file.TOOL.preview
        assert preview is not None
        self.assertEqual(
            preview({"path": "a.txt", "content": "a\n"}, self.cwd),
            "--- a.txt\n+++ a.txt\n@@ -1 +1 @@\n-a\n\\ No newline at end of file\n+a",
        )

    def test_errors(self) -> None:
        self.write("same.txt", "x\n")
        (self.cwd / "dir").mkdir()
        (self.cwd / "bin").write_bytes(b"\xff\xfe\x00")
        (self.cwd / "mixed.txt").write_bytes(b"a\r\nb\n")
        for path, message in (
            ("same.txt", "書いても中身が変わらない: same.txt"),
            ("dir", "ディレクトリである: dir"),
            ("bin", "UTF-8 として読めない: bin"),
            ("mixed.txt", r"改行に \\r\\n と \\n が混ざっている: mixed.txt"),
            ("a\0b", "パスとして使えない"),
        ):
            with self.subTest(path=path), self.assertRaisesRegex(ToolError, message):
                self.run_tool(path, "x\n")


class EditFileTest(ToolTestCase):
    def edit(self, old: str, new: str, **extra: object) -> str:
        arguments: ToolInput = {
            "path": "a.txt",
            "old_string": old,
            "new_string": new,
            **extra,
        }
        return edit_file.TOOL.run(arguments, self.cwd)

    def content(self) -> str:
        return (self.cwd / "a.txt").read_text(encoding="utf-8")

    def test_result_shows_three_lines_around_the_change(self) -> None:
        self.write("a.txt", "".join(f"行{n}\n" for n in range(1, 11)))
        self.assertEqual(
            self.edit("行5", "五"),
            "置き換えた: a.txt の 5 行目（段: そのまま）\n"
            "     2\t行2\n     3\t行3\n     4\t行4\n     5\t五\n"
            "     6\t行6\n     7\t行7\n     8\t行8",
        )

    def test_result_of_several_lines_and_relaxed_stage(self) -> None:
        self.write("a.txt", "def f():\n    a = 1  \n    return a\n")
        self.assertEqual(
            self.edit("    a = 1\n    return a", "    return 1"),
            "置き換えた: a.txt の 2 行目（段: 行末の空白を除く）\n"
            "     1\tdef f():\n     2\t    return 1",
        )

    def test_replace_all(self) -> None:
        self.write("a.txt", "x\ny\nx\n")
        self.assertEqual(
            self.edit("x", "z", replace_all=True),
            "置き換えた: a.txt の 2 か所（1・3 行目。段: そのまま）",
        )
        self.assertEqual(self.content(), "z\ny\nz\n")

    def test_several_places_without_replace_all(self) -> None:
        self.write("a.txt", "x\ny\nx\n")
        with self.assertRaisesRegex(
            ToolError, r"old_string が 2 か所に合う（段: そのまま。1・3 行目）"
        ):
            self.edit("x", "z")
        self.assertEqual(self.content(), "x\ny\nx\n")

    def test_not_found_shows_the_nearest_lines(self) -> None:
        self.write("a.txt", "def f():\n    return 1\n")
        with self.assertRaises(ToolError) as caught:
            self.edit("    return 2", "    return 3")
        message = str(caught.exception)
        self.assertIn("置き換え元が見つからない: a.txt", message)
        self.assertRegex(message, r"最も近いのは 2 行目（似ている度合い 0\.\d\d）:")
        self.assertIn("     2\t    return 1", message)

    def test_not_found_and_nothing_near(self) -> None:
        self.write("a.txt", "abc\n")
        with self.assertRaisesRegex(
            ToolError, r"最も近い所でも、似ている度合いは 0\.\d\d（1 行目）"
        ):
            self.edit("xyz", "w")

    def test_not_found_with_line_numbers(self) -> None:
        self.write("a.txt", "a = 1\n")
        with self.assertRaisesRegex(ToolError, "行番号とタブ"):
            self.edit("     1\ta = 1", "a = 2")

    def test_keeps_crlf(self) -> None:
        (self.cwd / "a.txt").write_bytes(b"a\r\nb\r\n")
        self.edit("b\n", "c\n")
        self.assertEqual((self.cwd / "a.txt").read_bytes(), b"a\r\nc\r\n")

    def test_preview_is_a_diff_and_does_not_write(self) -> None:
        self.write("a.txt", "a\nb\n")
        preview = edit_file.TOOL.preview
        assert preview is not None
        arguments = {"path": "a.txt", "old_string": "b", "new_string": "c"}
        self.assertEqual(
            preview(arguments, self.cwd),
            "--- a.txt\n+++ a.txt\n@@ -1,2 +1,2 @@\n a\n-b\n+c",
        )
        self.assertEqual(self.content(), "a\nb\n")

    def test_errors(self) -> None:
        self.write("a.txt", "x\n")
        (self.cwd / "dir").mkdir()
        (self.cwd / "bin").write_bytes(b"\xff\xfe\x00")
        for path, old, new, message in (
            (
                "none.txt",
                "x",
                "y",
                r"ファイルが無い: none.txt（新しいファイルは write_file",
            ),
            ("a.txt", "", "y", "old_string が空である"),
            ("a.txt", "x", "x", "old_string と new_string が同じである"),
            ("dir", "x", "y", "ディレクトリである: dir"),
            ("bin", "x", "y", "UTF-8 として読めない: bin"),
        ):
            arguments = {"path": path, "old_string": old, "new_string": new}
            with self.subTest(path=path), self.assertRaisesRegex(ToolError, message):
                edit_file.TOOL.run(arguments, self.cwd)

    def test_changing_tools(self) -> None:
        self.assertTrue(edit_file.TOOL.changes and write_file.TOOL.changes)


class EditInLoopTest(ToolTestCase):
    """本物の edit_file を、台本どおりに呼ぶ偽物のモデルのループに掛ける。"""

    def run_turn(self, answer: str) -> tuple[ScriptedModel, str]:
        self.write("a.txt", "a\nb\n")
        edit = ToolCall(
            "c", "edit_file", {"path": "a.txt", "old_string": "b", "new_string": "c"}
        )
        model = ScriptedModel([[edit, STOP], [STOP]])
        output = io.StringIO()
        session = fake_session(
            model, DEFAULT_TOOLS, ScriptedLines(answer), output=output, cwd=self.cwd
        )
        run_turn(session, (), "直せ", 1)
        return model, output.getvalue()

    def test_shows_diff_then_writes_when_allowed(self) -> None:
        model, output = self.run_turn("y")
        self.assertIn("--- a.txt\n+++ a.txt\n@@ -1,2 +1,2 @@\n a\n-b\n+c\n", output)
        self.assertEqual(self.content_of("a.txt"), "a\nc\n")
        result = model.sent[1][-1].content[0]
        assert isinstance(result, ToolResultBlock)
        self.assertTrue(
            result.content.startswith("置き換えた: a.txt の 2 行目（段: そのまま）")
        )

    def test_does_not_write_when_refused(self) -> None:
        self.run_turn("n")
        self.assertEqual(self.content_of("a.txt"), "a\nb\n")

    def content_of(self, name: str) -> str:
        return (self.cwd / name).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
