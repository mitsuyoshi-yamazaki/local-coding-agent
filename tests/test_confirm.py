import unittest

from local_coding_agent.permissions.confirm import (
    PROMPT,
    REFUSED,
    Answer,
    confirm,
    refusal,
)
from tests.fakes import scripted_lines


class ConfirmTest(unittest.TestCase):
    def test_yes_answers_allow(self) -> None:
        for answer in ("y", "yes", "Y", "YES", " y "):
            with self.subTest(answer=answer):
                self.assertEqual(confirm(scripted_lines(answer)), Answer(True))

    def test_no_answers_refuse_without_reason(self) -> None:
        for answer in ("", "n", "no", "N", " no "):
            with self.subTest(answer=answer):
                self.assertEqual(confirm(scripted_lines(answer)), Answer(False))

    def test_other_answers_refuse_with_the_answer_as_reason(self) -> None:
        for answer, reason in (
            ("テストのコマンドだけを走らせる", "テストのコマンドだけを走らせる"),
            ("  消さずに残す  ", "消さずに残す"),
            ("yy", "yy"),
        ):
            with self.subTest(answer=answer):
                self.assertEqual(confirm(scripted_lines(answer)), Answer(False, reason))

    def test_end_of_input_refuses(self) -> None:
        self.assertEqual(confirm(scripted_lines()), Answer(False))

    def test_asks_with_prompt(self) -> None:
        read_line = scripted_lines("y")
        confirm(read_line)
        self.assertEqual(read_line.prompts, [PROMPT])

    def test_ctrl_c_is_not_caught(self) -> None:
        with self.assertRaises(KeyboardInterrupt):
            confirm(scripted_lines(KeyboardInterrupt()))


class RefusalTest(unittest.TestCase):
    def test_text_for_the_model(self) -> None:
        self.assertEqual(refusal(Answer(False)), REFUSED)
        self.assertEqual(
            refusal(Answer(False, "消さずに残す")), f"{REFUSED}。理由: 消さずに残す"
        )


if __name__ == "__main__":
    unittest.main()
