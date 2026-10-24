import io
import unittest

from local_coding_agent.cli.screen import DIM, RESET, Screen


def screen(color: bool = False) -> tuple[Screen, io.StringIO]:
    output = io.StringIO()
    return Screen(output, color), output


class ScreenTest(unittest.TestCase):
    def test_same_kind_continues_on_the_line(self) -> None:
        target, output = screen()
        target.write("こん")
        target.write("にちは")
        self.assertEqual(output.getvalue(), "こんにちは")

    def test_new_kind_starts_on_a_new_line(self) -> None:
        target, output = screen()
        target.write("考え", "thinking")
        target.write("答え")
        self.assertEqual(output.getvalue(), "考え\n答え")

    def test_line_ends_the_current_line_first(self) -> None:
        target, output = screen()
        target.write("答え")
        target.line("数値")
        target.line("次")
        self.assertEqual(output.getvalue(), "答え\n数値\n次\n")

    def test_line_after_newline_adds_no_blank(self) -> None:
        target, output = screen()
        target.write("答え\n")
        target.line("数値")
        self.assertEqual(output.getvalue(), "答え\n数値\n")

    def test_color_dims_all_but_text(self) -> None:
        target, output = screen(color=True)
        target.write("考え", "thinking")
        target.write("答え")
        target.line("数値", "note")
        self.assertEqual(
            output.getvalue(), f"{DIM}考え{RESET}\n答え\n{DIM}数値\n{RESET}"
        )


if __name__ == "__main__":
    unittest.main()
