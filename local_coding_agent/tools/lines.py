"""行の分け方と、行番号を付けた形（cat -n）。read_file と edit_file が共に使う。"""

# これより長い行は、行番号を付けるときに、ここで切る
MAX_LINE_LENGTH = 2000


def split_lines(text: str) -> list[str]:
    """改行（\\n）で行に分ける。末尾の改行の後は行にしない。空の文字列は行を持たない。"""
    lines = text.split("\n")
    return lines[:-1] if lines[-1] == "" else lines


def numbered(number: int, line: str) -> str:
    """行番号を付けた1行（右に寄せた行番号・タブ・行）。長い行は切り、切ったことを書き添える。"""
    if len(line) <= MAX_LINE_LENGTH:
        return f"{number:6}\t{line}"
    notice = f"（この行は {len(line)} 字。{MAX_LINE_LENGTH} 字で切った）"
    return f"{number:6}\t{line[:MAX_LINE_LENGTH]}…{notice}"
