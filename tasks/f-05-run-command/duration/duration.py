"""時間の長さの文字列（「1h30m」など）と、秒数を変換する。"""

# 単位と、その秒数。大きい単位から並べる
UNITS = {"h": 3600, "m": 60, "s": 1}


def parse_duration(text: str) -> int:
    """「1h30m」「45s」「2h5s」などを秒数にする。単位は h・m・s。"""
    total = 0
    number = ""
    for char in text:
        if char.isdigit():
            number += char
        elif char in UNITS and number:
            total += int(number) * UNITS[char]
        else:
            raise ValueError(f"読めない: {text!r}")
    return total


def format_duration(seconds: int) -> str:
    """秒数を「1h30m」の形にする。0 の単位は書かない。0 秒は「0s」。"""
    if seconds == 0:
        return "0s"
    parts = []
    rest = seconds
    for unit, size in UNITS.items():
        count = rest // size
        rest = rest % 60
        if count:
            parts.append(f"{count}{unit}")
    return "".join(parts)
