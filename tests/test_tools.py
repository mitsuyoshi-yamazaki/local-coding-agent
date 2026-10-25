import tempfile
import unittest
from pathlib import Path

from local_coding_agent.tools import list_directory, read_file
from local_coding_agent.tools.default import DEFAULT_TOOLS
from local_coding_agent.tools.input_check import input_problem
from local_coding_agent.tools.tool import ToolError, find_tool


class ToolTestCase(unittest.TestCase):
    """一時ディレクトリを作業ディレクトリにする。"""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cwd = Path(directory.name)

    def write(self, name: str, text: str) -> Path:
        path = self.cwd / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class ReadFileTest(ToolTestCase):
    def test_numbers_lines_like_cat_n(self) -> None:
        self.write("a.txt", "一\n二\n")
        self.assertEqual(
            read_file.run({"path": "a.txt"}, self.cwd), "     1\t一\n     2\t二"
        )

    def test_last_line_without_newline(self) -> None:
        self.write("a.txt", "一\n二")
        self.assertEqual(
            read_file.run({"path": "a.txt"}, self.cwd), "     1\t一\n     2\t二"
        )

    def test_absolute_path(self) -> None:
        path = self.write("a.txt", "一\n")
        self.assertEqual(read_file.run({"path": str(path)}, Path("/")), "     1\t一")

    def test_offset_and_limit_with_rest_notice(self) -> None:
        self.write("a.txt", "".join(f"行{n}\n" for n in range(1, 11)))
        self.assertEqual(
            read_file.run({"path": "a.txt", "offset": 3, "limit": 2}, self.cwd),
            "     3\t行3\n     4\t行4\n"
            "\n"
            "（全体は 10 行。続きは、offset に 5 を渡して読む）",
        )

    def test_default_limit_is_2000(self) -> None:
        self.write("a.txt", "x\n" * 2001)
        result = read_file.run({"path": "a.txt"}, self.cwd)
        self.assertIn("  2000\tx\n", result)
        self.assertNotIn("  2001\t", result)
        self.assertTrue(
            result.endswith("（全体は 2001 行。続きは、offset に 2001 を渡して読む）")
        )

    def test_no_notice_when_read_to_the_end(self) -> None:
        self.write("a.txt", "一\n二\n")
        result = read_file.run({"path": "a.txt", "offset": 2, "limit": 5}, self.cwd)
        self.assertEqual(result, "     2\t二")

    def test_long_line_is_cut(self) -> None:
        self.write("a.txt", "あ" * 2001 + "\n")
        result = read_file.run({"path": "a.txt"}, self.cwd)
        self.assertEqual(
            result, "     1\t" + "あ" * 2000 + "…（この行は 2001 字。2000 字で切った）"
        )

    def test_empty_file(self) -> None:
        self.write("a.txt", "")
        self.assertEqual(read_file.run({"path": "a.txt"}, self.cwd), "（空のファイル）")

    def test_offset_beyond_end(self) -> None:
        self.write("a.txt", "一\n")
        with self.assertRaisesRegex(ToolError, "offset が行数を超えている"):
            read_file.run({"path": "a.txt", "offset": 2}, self.cwd)

    def test_errors(self) -> None:
        (self.cwd / "dir").mkdir()
        (self.cwd / "bin").write_bytes(b"\xff\xfe\x00")
        for path, message in (
            ("none.txt", "ファイルが無い: none.txt"),
            ("dir", "ディレクトリである"),
            ("bin", "UTF-8 として読めない: bin"),
            ("a\0b", "パスとして使えない"),
        ):
            with (
                self.subTest(path=path),
                self.assertRaisesRegex(ToolError, message),
            ):
                read_file.run({"path": path}, self.cwd)


class ListDirectoryTest(ToolTestCase):
    def test_names_in_order_with_slash_for_directories(self) -> None:
        self.write("b.txt", "")
        self.write("src/main.py", "")
        self.write(".hidden", "")
        self.assertEqual(list_directory.run({}, self.cwd), ".hidden\nb.txt\nsrc/")

    def test_relative_path(self) -> None:
        self.write("src/main.py", "")
        self.assertEqual(list_directory.run({"path": "src"}, self.cwd), "main.py")

    def test_empty_directory(self) -> None:
        self.assertEqual(list_directory.run({}, self.cwd), "（空のディレクトリ）")

    def test_errors(self) -> None:
        self.write("a.txt", "")
        for path, message in (
            ("none", "ディレクトリが無い: none"),
            ("a.txt", "ディレクトリではなくファイルである"),
            ("a\0b", "パスとして使えない"),
        ):
            with (
                self.subTest(path=path),
                self.assertRaisesRegex(ToolError, message),
            ):
                list_directory.run({"path": path}, self.cwd)


class InputCheckTest(unittest.TestCase):
    schema = read_file.DEFINITION.input_schema

    def test_valid_input(self) -> None:
        self.assertIsNone(input_problem(self.schema, {"path": "a", "offset": 2}))

    def test_fields_not_in_definition_are_ignored(self) -> None:
        self.assertIsNone(input_problem(self.schema, {"path": "a", "x": 1}))

    def test_problems(self) -> None:
        for value, message in (
            ({}, "必須の欄が無い: path"),
            ({"path": 1}, "path は string でなければならない（受けた値: 1）"),
            (
                {"path": "a", "limit": "10"},
                'limit は integer でなければならない（受けた値: "10"）',
            ),
            ({"path": "a", "offset": True}, "offset は integer でなければならない"),
            ({"path": "a", "offset": 1.5}, "offset は integer でなければならない"),
            (
                {"path": "a", "offset": 0},
                "offset は 1 以上でなければならない（受けた値: 0）",
            ),
        ):
            with self.subTest(value=value):
                problem = input_problem(self.schema, value)
                self.assertIsNotNone(problem)
                self.assertIn(message, str(problem))


class DefaultToolsTest(unittest.TestCase):
    def test_tools_and_which_change_files(self) -> None:
        self.assertEqual(
            [(tool.name, tool.changes) for tool in DEFAULT_TOOLS],
            [
                ("read_file", False),
                ("list_directory", False),
                ("write_file", True),
                ("edit_file", True),
            ],
        )

    def test_changing_tools_have_preview(self) -> None:
        for tool in DEFAULT_TOOLS:
            with self.subTest(tool=tool.name):
                self.assertEqual(tool.preview is not None, tool.changes)

    def test_find_tool(self) -> None:
        self.assertIs(find_tool(DEFAULT_TOOLS, "read_file"), read_file.TOOL)
        self.assertIsNone(find_tool(DEFAULT_TOOLS, "run_command"))


if __name__ == "__main__":
    unittest.main()
