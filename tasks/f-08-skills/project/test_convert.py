import math
import unittest

from convert import convert

# (値, 元, 先, 答え)
CASES = [
    (1, "km", "m", 1000),
    (500, "m", "km", 0.5),
    (1, "mile", "km", 1.609344),
    (1.609344, "km", "mile", 1),
]


class ConvertTest(unittest.TestCase):
    def test_cases(self) -> None:
        for value, source, target, expected in CASES:
            with self.subTest(source=source, target=target):
                self.assertTrue(math.isclose(convert(value, source, target), expected))

    def test_same_unit(self) -> None:
        self.assertEqual(convert(3, "km", "km"), 3)

    def test_unknown(self) -> None:
        with self.assertRaises(ValueError):
            convert(1, "km", "lb")


if __name__ == "__main__":
    unittest.main()
