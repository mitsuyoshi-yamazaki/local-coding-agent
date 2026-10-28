import tempfile
import unittest
from pathlib import Path
from unittest import mock

from local_coding_agent.commands.custom import (
    COMMANDS_PATH,
    CommandError,
    CustomCommand,
    Listed,
    expand,
    find_custom,
    list_custom,
    parse_custom,
    split_front_matter,
)

PATH = COMMANDS_PATH / "fix.md"


def command(body: str) -> CustomCommand:
    return CustomCommand("fix", PATH, "説明", body)


class FrontMatterTest(unittest.TestCase):
    def test_front_matter_and_body(self) -> None:
        text = "---\ndescription: 直す\nmodel: x\n---\n\n本文\n"
        self.assertEqual(
            split_front_matter(text), (("description: 直す", "model: x"), "\n本文\n")
        )

    def test_without_front_matter(self) -> None:
        self.assertEqual(split_front_matter("本文\n---\n"), ((), "本文\n---\n"))

    def test_unclosed_front_matter_is_body(self) -> None:
        text = "---\ndescription: 直す\n本文\n"
        self.assertEqual(split_front_matter(text), ((), text))

    def test_fence_may_have_trailing_spaces(self) -> None:
        self.assertEqual(split_front_matter("---  \na: b\n---\t\nx"), (("a: b",), "x"))

    def test_empty_text(self) -> None:
        self.assertEqual(split_front_matter(""), ((), ""))


class DescriptionTest(unittest.TestCase):
    def test_description_from_front_matter(self) -> None:
        parsed = parse_custom("fix", PATH, "---\ndescription: 直す\n---\n本文\n")
        self.assertEqual(parsed, CustomCommand("fix", PATH, "直す", "本文\n"))

    def test_quotes_are_removed(self) -> None:
        for quoted in ('"直す: 速く"', "'直す'"):
            with self.subTest(quoted=quoted):
                text = f"---\ndescription: {quoted}\n---\n本文"
                self.assertEqual(
                    parse_custom("fix", PATH, text).description, quoted[1:-1]
                )

    def test_other_keys_are_not_used(self) -> None:
        text = "---\nallowed-tools: Bash\nargument-hint: <file>\n---\n\n  最初の行  \n2行目"
        self.assertEqual(parse_custom("fix", PATH, text).description, "最初の行")

    def test_first_non_empty_line_when_no_front_matter(self) -> None:
        self.assertEqual(
            parse_custom("fix", PATH, "\n\n# 直す\n本文").description, "# 直す"
        )

    def test_empty_body_has_empty_description(self) -> None:
        self.assertEqual(parse_custom("fix", PATH, "").description, "")


class ExpandTest(unittest.TestCase):
    def test_every_placeholder_is_replaced(self) -> None:
        self.assertEqual(
            expand(command("\n$ARGUMENTS を読み、$ARGUMENTS を直せ\n"), "a.py"),
            "a.py を読み、a.py を直せ",
        )

    def test_placeholder_without_arguments_becomes_empty(self) -> None:
        self.assertEqual(expand(command("直せ: $ARGUMENTS"), ""), "直せ:")

    def test_arguments_are_appended_without_placeholder(self) -> None:
        self.assertEqual(
            expand(command("テストを直せ\n\n"), "a.py -v"),
            "テストを直せ\n\nARGUMENTS: a.py -v",
        )

    def test_no_arguments_and_no_placeholder(self) -> None:
        self.assertEqual(expand(command("  テストを直せ\n"), ""), "テストを直せ")

    def test_empty_body_with_arguments(self) -> None:
        self.assertEqual(expand(command(""), "a.py"), "ARGUMENTS: a.py")

    def test_empty_body_without_arguments(self) -> None:
        self.assertEqual(expand(command("\n  \n"), ""), "")


class FilesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cwd = Path(directory.name)

    def write(self, name: str, data: str | bytes) -> None:
        path = self.cwd / COMMANDS_PATH / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8")


class FindCustomTest(FilesTestCase):
    def test_reads_file_each_time(self) -> None:
        self.write("fix.md", "1つ目")
        first = find_custom(self.cwd, "fix")
        self.write("fix.md", "2つ目")
        second = find_custom(self.cwd, "fix")
        self.assertEqual(first, CustomCommand("fix", PATH, "1つ目", "1つ目"))
        self.assertEqual(second, CustomCommand("fix", PATH, "2つ目", "2つ目"))

    def test_missing_file(self) -> None:
        self.assertIsNone(find_custom(self.cwd, "fix"))
        self.write("other.md", "x")
        self.assertIsNone(find_custom(self.cwd, "fix"))

    def test_directory_is_not_a_command(self) -> None:
        (self.cwd / COMMANDS_PATH / "fix.md").mkdir(parents=True)
        self.assertIsNone(find_custom(self.cwd, "fix"))

    def test_not_utf8(self) -> None:
        self.write("fix.md", b"\xff\xfe")
        with self.assertRaises(CommandError):
            find_custom(self.cwd, "fix")

    def test_reason_does_not_contain_path(self) -> None:
        self.write("fix.md", "x")
        denied = PermissionError(13, "Permission denied", str(self.cwd / PATH))
        with (
            mock.patch.object(Path, "read_text", side_effect=denied),
            self.assertRaises(CommandError) as raised,
        ):
            find_custom(self.cwd, "fix")
        self.assertEqual(str(raised.exception), "Permission denied")


class ListCustomTest(FilesTestCase):
    def test_no_directory(self) -> None:
        self.assertEqual(list_custom(self.cwd, ()), ())

    def test_directory_that_cannot_be_listed(self) -> None:
        (self.cwd / COMMANDS_PATH).mkdir(parents=True)
        denied = PermissionError(13, "Permission denied")
        with mock.patch.object(Path, "iterdir", side_effect=denied):
            listed = list_custom(self.cwd, ())
        self.assertEqual(
            listed,
            (
                Listed(
                    ".local-coding-agent/commands/", "", "読めない: Permission denied"
                ),
            ),
        )

    def test_sorted_markdown_files_only(self) -> None:
        self.write("review.md", "---\ndescription: 見る\n---\n")
        self.write("explain.md", "説明する\n")
        self.write("notes.txt", "x")
        (self.cwd / COMMANDS_PATH / "sub.md").mkdir()
        self.assertEqual(
            list_custom(self.cwd, ()),
            (Listed("/explain", "説明する"), Listed("/review", "見る")),
        )

    def test_problems(self) -> None:
        self.write("Fix.md", "x")
        self.write("clear.md", "消す")
        self.write("broken.md", b"\xff")
        listed = list_custom(self.cwd, ("clear",))
        self.assertEqual(
            [(item.label, item.problem) for item in listed],
            [
                ("Fix.md", "名前に使えない字があるので呼べない"),
                ("/broken", listed[1].problem),
                ("/clear", "組み込みと同じ名前なので呼べない"),
            ],
        )
        self.assertTrue(str(listed[1].problem).startswith("読めない: "))
        self.assertEqual(listed[2].description, "消す")


if __name__ == "__main__":
    unittest.main()
