import unittest

from inventory import total_count


class TotalCountTest(unittest.TestCase):
    def test_sums_counts(self):
        self.assertEqual(total_count([("ねじ", 12), ("ばね", 5)]), 17)

    def test_empty(self):
        self.assertEqual(total_count([]), 0)


if __name__ == "__main__":
    unittest.main()
