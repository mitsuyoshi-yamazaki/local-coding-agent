import unittest

from local_coding_agent.commands.parse import CommandLine, parse_command


class ParseCommandTest(unittest.TestCase):
    def test_name_only(self) -> None:
        self.assertEqual(parse_command("/help"), CommandLine("/help", "help", ""))

    def test_arguments_are_rest_of_line_without_surrounding_spaces(self) -> None:
        self.assertEqual(
            parse_command("/fix  test_a.py  -v  "),
            CommandLine("/fix  test_a.py  -v", "fix", "test_a.py  -v"),
        )

    def test_tab_ends_name(self) -> None:
        command = parse_command("/mode\task")
        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual((command.name, command.arguments), ("mode", "ask"))

    def test_hyphen_underscore_and_digits(self) -> None:
        for name in ("fix-test", "fix_test", "2nd", "a1"):
            with self.subTest(name=name):
                command = parse_command(f"/{name} x")
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual(command.name, name)

    def test_lines_that_are_not_commands(self) -> None:
        for line in (
            "help",
            " /help",
            "/tmp/a.txt を読んで",
            "/",
            "/ help",
            "/Help",
            "/-x",
            "/_x",
            "/a.md",
            "/../x",
            "/名前",
        ):
            with self.subTest(line=line):
                self.assertIsNone(parse_command(line))


if __name__ == "__main__":
    unittest.main()
