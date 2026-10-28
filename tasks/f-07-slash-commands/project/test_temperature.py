import unittest

from temperature import celsius_to_fahrenheit, fahrenheit_to_celsius


class CelsiusToFahrenheitTest(unittest.TestCase):
    def test_freezing_point(self) -> None:
        self.assertEqual(celsius_to_fahrenheit(0), 32)

    def test_boiling_point(self) -> None:
        self.assertEqual(celsius_to_fahrenheit(100), 212)


class FahrenheitToCelsiusTest(unittest.TestCase):
    def test_freezing_point(self) -> None:
        self.assertEqual(fahrenheit_to_celsius(32), 0)

    def test_round_trip(self) -> None:
        self.assertAlmostEqual(fahrenheit_to_celsius(celsius_to_fahrenheit(37)), 37)


if __name__ == "__main__":
    unittest.main()
