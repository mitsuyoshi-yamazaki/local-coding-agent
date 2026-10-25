import unittest

from local_coding_agent.permissions.confirm import PROMPT, confirm
from tests.fakes import scripted_lines


class ConfirmTest(unittest.TestCase):
    def test_yes_answers_allow(self) -> None:
        for answer in ("y", "yes", "Y", "YES", " y "):
            with self.subTest(answer=answer):
                self.assertTrue(confirm(scripted_lines(answer)))

    def test_other_answers_refuse(self) -> None:
        for answer in ("", "n", "no", "はい", "yy"):
            with self.subTest(answer=answer):
                self.assertFalse(confirm(scripted_lines(answer)))

    def test_end_of_input_refuses(self) -> None:
        self.assertFalse(confirm(scripted_lines()))

    def test_asks_with_prompt(self) -> None:
        read_line = scripted_lines("y")
        confirm(read_line)
        self.assertEqual(read_line.prompts, [PROMPT])

    def test_ctrl_c_is_not_caught(self) -> None:
        with self.assertRaises(KeyboardInterrupt):
            confirm(scripted_lines(KeyboardInterrupt()))


if __name__ == "__main__":
    unittest.main()
