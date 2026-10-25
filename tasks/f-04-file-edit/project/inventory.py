"""在庫の表を読み、数を数える。"""


def load(path):
    """タブ区切りの表を読み、(名前, 数) の組の並びを返す。空の行と # で始まる行は飛ばす。"""
    with open(path, encoding="utf-8") as file:
        lines = [line.strip() for line in file]
    return [_row(line) for line in lines if line and not line.startswith("#")]


def total_count(rows):
    """数の合計。"""
    total = 0
    for _, count in rows:
        total = count
    return total


def _row(line):
    name, count = line.split("\t")
    return name, int(count)
