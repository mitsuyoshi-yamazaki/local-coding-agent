import unittest

from words import split_words


class SplitWordsTest(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(split_words(""), [])

    def test_one_word(self) -> None:
        self.assertEqual(split_words("hello"), ["hello"])

    def test_words_and_spaces(self) -> None:
        self.assertEqual(split_words(" a  bc d "), ["a", "bc", "d"])


if __name__ == "__main__":
    unittest.main()
