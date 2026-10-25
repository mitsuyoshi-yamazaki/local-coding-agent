import io
import termios
import unittest
from unittest import mock

from local_coding_agent.cli.user_input import (
    BRACKETED_PASTE_OFF,
    BRACKETED_PASTE_ON,
    CONTINUATION_PROMPT,
    PASTE_END,
    PASTE_START,
    InputCancelled,
    bracketed_paste,
    read_request,
)


class Lines:
    """決めた行を順に返し、渡された案内を覚えておく、偽物の入力。"""

    def __init__(self, *lines: str) -> None:
        self.remaining = iter(lines)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        try:
            return next(self.remaining)
        except StopIteration:
            # 行が尽きたら、Ctrl-D を真似る
            raise EOFError from None


def read(*lines: str) -> tuple[str, list[str]]:
    """偽物の入力から依頼を1つ読み、依頼と、出した案内を返す。"""
    source = Lines(*lines)
    return read_request(source, "> "), source.prompts


class ContinuationTest(unittest.TestCase):
    def test_single_line(self) -> None:
        self.assertEqual(read("こんにちは"), ("こんにちは", ["> "]))

    def test_backslash_continues_with_newline(self) -> None:
        self.assertEqual(
            read("一行目\\", "二行目\\", "三行目"),
            (
                "一行目\n二行目\n三行目",
                ["> ", CONTINUATION_PROMPT, CONTINUATION_PROMPT],
            ),
        )

    def test_backslash_only_line_adds_empty_line(self) -> None:
        self.assertEqual(read("a\\", "\\", "b")[0], "a\n\nb")


class PasteTest(unittest.TestCase):
    def test_pasted_lines_become_one_request(self) -> None:
        self.assertEqual(
            read(f"{PASTE_START}a", "b", f"c{PASTE_END}"),
            ("a\nb\nc", ["> ", "", ""]),
        )

    def test_text_typed_around_paste_is_kept(self) -> None:
        self.assertEqual(
            read(f"次を直して: {PASTE_START}a", f"b{PASTE_END} お願い")[0],
            "次を直して: a\nb お願い",
        )

    def test_paste_ending_with_newline(self) -> None:
        # 貼り付けた文の末尾の改行は、依頼に残さない
        self.assertEqual(read(f"{PASTE_START}a", "b", f"{PASTE_END}")[0], "a\nb")

    def test_backslash_inside_paste_does_not_continue(self) -> None:
        self.assertEqual(
            read(f"{PASTE_START}ls \\", f"  -la\\{PASTE_END}"),
            ("ls \\\n  -la\\", ["> ", ""]),
        )

    def test_backslash_typed_after_paste_continues(self) -> None:
        self.assertEqual(
            read(f"{PASTE_START}a{PASTE_END}\\", "b"),
            ("a\nb", ["> ", CONTINUATION_PROMPT]),
        )

    def test_second_paste_on_same_line(self) -> None:
        self.assertEqual(
            read(f"{PASTE_START}a{PASTE_END} と {PASTE_START}b", f"c{PASTE_END}")[0],
            "a と b\nc",
        )


class CancelTest(unittest.TestCase):
    def test_ctrl_d_on_first_line_is_end_of_input(self) -> None:
        with self.assertRaises(EOFError):
            read()

    def test_ctrl_d_while_continuing_cancels_request(self) -> None:
        with self.assertRaisesRegex(InputCancelled, "Ctrl-D"):
            read("a\\")

    def test_ctrl_d_inside_paste_cancels_request(self) -> None:
        with self.assertRaisesRegex(InputCancelled, "Ctrl-D"):
            read(f"{PASTE_START}a")

    def test_arrow_key_cancels_request(self) -> None:
        with self.assertRaisesRegex(InputCancelled, "矢印キー"):
            read("abc\x1b[DX")

    def test_escape_inside_paste_is_kept(self) -> None:
        self.assertEqual(read(f"{PASTE_START}色\x1b[31m{PASTE_END}")[0], "色\x1b[31m")


class FakeTerminal(io.StringIO):
    """端末のふりをする出力。"""

    def isatty(self) -> bool:
        return True

    def fileno(self) -> int:
        return 0


# termios.tcgetattr が返す形: [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
SAVED = [1, 2, 3, termios.ECHOCTL | termios.ECHO, 5, 6, []]


class BracketedPasteTest(unittest.TestCase):
    def test_does_nothing_without_terminal(self) -> None:
        output = io.StringIO()
        with (
            mock.patch("termios.tcsetattr") as set_attr,
            bracketed_paste(io.StringIO(), output),
        ):
            pass
        self.assertEqual(output.getvalue(), "")
        set_attr.assert_not_called()

    def test_turns_on_and_restores_even_on_error(self) -> None:
        terminal = FakeTerminal()
        with (
            mock.patch("termios.tcgetattr", return_value=SAVED),
            mock.patch("termios.tcsetattr") as set_attr,
            self.assertRaises(KeyboardInterrupt),
            bracketed_paste(terminal, terminal),
        ):
            self.assertEqual(terminal.getvalue(), BRACKETED_PASTE_ON)
            raise KeyboardInterrupt
        self.assertEqual(terminal.getvalue(), BRACKETED_PASTE_ON + BRACKETED_PASTE_OFF)
        quiet, restored = (call.args[2] for call in set_attr.call_args_list)
        self.assertEqual(quiet[3], termios.ECHO)
        self.assertEqual(restored, SAVED)


if __name__ == "__main__":
    unittest.main()
