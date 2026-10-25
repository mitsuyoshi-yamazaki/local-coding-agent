import unittest
from pathlib import Path

from inventory import load

STOCK = Path(__file__).with_name("stock.txt")


class StockTest(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(
            load(STOCK), [("ねじ", 40), ("ばね", 5), ("ナット", 30), ("座金", 8)]
        )


if __name__ == "__main__":
    unittest.main()
