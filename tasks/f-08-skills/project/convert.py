"""長さの単位の変換。"""

# (元, 先): 元の 1 が、先のいくつか。逆向きの変換は、この表から求める
RATES: dict[tuple[str, str], float] = {
    ("km", "m"): 1000.0,
    ("mile", "km"): 1.609344,
}


def convert(value: float, source: str, target: str) -> float:
    """value（単位 source）を、単位 target で表す。"""
    if source == target:
        return value
    if (source, target) in RATES:
        return value * RATES[(source, target)]
    if (target, source) in RATES:
        return value / RATES[(target, source)]
    raise ValueError(f"知らない変換: {source} → {target}")
