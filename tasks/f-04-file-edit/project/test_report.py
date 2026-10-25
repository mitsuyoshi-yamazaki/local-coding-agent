import unittest

from report import low_stock


class LowStockTest(unittest.TestCase):
    def test_names_below_threshold_in_table_order(self):
        rows = [("ねじ", 12), ("ばね", 5), ("ナット", 10), ("座金", 8)]
        self.assertEqual(low_stock(rows, 10), ["ばね", "座金"])

    def test_none_below_threshold(self):
        self.assertEqual(low_stock([("ねじ", 12)], 10), [])


if __name__ == "__main__":
    unittest.main()
