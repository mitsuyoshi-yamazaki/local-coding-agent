import unittest

from duration import format_duration, parse_duration

CASES = (
    ("0s", 0),
    ("45s", 45),
    ("1m30s", 90),
    ("2h", 7200),
    ("1h30m", 5400),
    ("1h1m1s", 3661),
)


class ParseDurationTest(unittest.TestCase):
    def test_cases(self) -> None:
        for text, seconds in CASES:
            with self.subTest(text=text):
                self.assertEqual(parse_duration(text), seconds)

    def test_unknown_unit(self) -> None:
        with self.assertRaises(ValueError):
            parse_duration("3d")


class FormatDurationTest(unittest.TestCase):
    def test_cases(self) -> None:
        for text, seconds in CASES:
            with self.subTest(seconds=seconds):
                self.assertEqual(format_duration(seconds), text)


if __name__ == "__main__":
    unittest.main()
