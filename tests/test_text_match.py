import unittest

from local_coding_agent.tools.text_match import (
    EXACT,
    INDENT,
    TRAILING,
    find,
    has_line_numbers,
    nearest,
    replace,
)


def edited(text: str, old: str, new: str) -> tuple[str, str]:
    """見つかった段と、置き換えた後の中身。"""
    found = find(text, old, new)
    assert found is not None
    return found.stage, replace(text, found.spans)


class ExactTest(unittest.TestCase):
    def test_part_of_a_line(self) -> None:
        self.assertEqual(
            edited("a = 1\nb = 2\n", "= 1", "= 3"), (EXACT, "a = 3\nb = 2\n")
        )

    def test_several_lines(self) -> None:
        self.assertEqual(edited("a\nb\nc\n", "a\nb\n", "x\n"), (EXACT, "x\nc\n"))

    def test_every_place_is_found(self) -> None:
        found = find("x\ny\nx\n", "x", "z")
        assert found is not None
        self.assertEqual(len(found.spans), 2)
        self.assertEqual(replace("x\ny\nx\n", found.spans), "z\ny\nz\n")

    def test_exact_comes_first(self) -> None:
        # 行の単位で比べる段でも合うが、そのまま合う段で止める
        self.assertEqual(edited("  x  \n", "x", "y"), (EXACT, "  y  \n"))


class TrailingWhitespaceTest(unittest.TestCase):
    def test_trailing_spaces_and_tabs_are_ignored(self) -> None:
        self.assertEqual(
            edited("x  \ny\t\nz\n", "x\ny", "X\nY"), (TRAILING, "X\nY\nz\n")
        )

    def test_trailing_newline_of_old_string_is_ignored(self) -> None:
        self.assertEqual(edited("x  \ny\n", "x\ny\n", "z\n"), (TRAILING, "z\n"))

    def test_last_line_without_newline(self) -> None:
        self.assertEqual(edited("a\nx  \ny", "x\ny", "z"), (TRAILING, "a\nz"))

    def test_empty_new_string_removes_the_lines(self) -> None:
        self.assertEqual(edited("a\nb  \nc\n", "b\n", ""), (TRAILING, "a\nc\n"))


class IndentTest(unittest.TestCase):
    def test_old_string_indented_less_than_file(self) -> None:
        text = "def f():\n    if a:\n        b()\n"
        self.assertEqual(
            edited(text, "if a:\n    b()", "if a:\n    c()\n    d()"),
            (INDENT, "def f():\n    if a:\n        c()\n        d()\n"),
        )

    def test_old_string_indented_more_than_file(self) -> None:
        self.assertEqual(
            edited(
                "if a:\n    b()\n", "    if a:\n        b()", "    if a:\n        c()"
            ),
            (INDENT, "if a:\n    c()\n"),
        )

    def test_blank_lines_in_the_block(self) -> None:
        text = "    a()\n\n    b()\n"
        self.assertEqual(
            edited(text, "a()\n\nb()", "a()\n\nc()"), (INDENT, "    a()\n\n    c()\n")
        )

    def test_uneven_shift_does_not_match(self) -> None:
        # 1行目は 4 字、2行目は 8 字ずれている
        self.assertIsNone(find("    if a:\n            b()\n", "if a:\n    b()", "x"))

    def test_tabs_and_spaces_do_not_match(self) -> None:
        self.assertIsNone(find("\tif a:\n\t\tb()\n", "    if a:\n        b()", "x"))


class NotFoundTest(unittest.TestCase):
    def test_none_when_no_stage_matches(self) -> None:
        self.assertIsNone(find("a\nb\n", "c", "d"))

    def test_nearest_lines(self) -> None:
        text = "def f():\n    return 1\n\ndef g():\n    return 22\n"
        found = nearest(text, "    return 2")
        assert found is not None
        self.assertEqual((found.line, found.lines), (5, ("    return 22",)))
        self.assertGreater(found.ratio, 0.9)

    def test_nearest_keeps_the_size_of_old_string(self) -> None:
        found = nearest("a\nb\nc\nd\n", "b\nc\nx")
        assert found is not None
        self.assertEqual((found.line, found.lines), (2, ("b", "c", "d")))

    def test_nearest_in_a_short_file(self) -> None:
        found = nearest("a\n", "a\nb\nc")
        assert found is not None
        self.assertEqual((found.line, found.lines), (1, ("a",)))

    def test_no_nearest_in_an_empty_file(self) -> None:
        self.assertIsNone(nearest("", "a"))

    def test_line_numbers_copied_from_read_file(self) -> None:
        self.assertTrue(has_line_numbers("     5\t    x = 1\n     6\t\n     7\ty"))
        self.assertFalse(has_line_numbers("x = 1\n     6\ty"))
        self.assertFalse(has_line_numbers("12 個"))


if __name__ == "__main__":
    unittest.main()
