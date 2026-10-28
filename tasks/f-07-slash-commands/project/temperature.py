"""温度の単位を変換する。"""


def celsius_to_fahrenheit(celsius: float) -> float:
    """摂氏を華氏に変える。"""
    return celsius * 9 / 5 - 32


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """華氏を摂氏に変える。"""
    return (fahrenheit - 32) * 5 / 9
