"""打った行が slash command かを見分け、名前と引数に分ける。

行の頭（前に空白が無い）が / で、/ から空白までの語が /<名前> の形なら、コマンドである。
それ以外の行（/tmp/a.txt を読んで、など）は、依頼としてモデルに送る。
"""

import re
from dataclasses import dataclass

# コマンドの名前の形。英小文字か数字で始まり、英小文字・数字・-・_ が続く。
# . と / を含まないので、自作のコマンドの名前は、置き場のディレクトリの外のファイルを指せない
NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
# / と、空白までの語と、残り
_LINE = re.compile(r"/(\S*)(.*)", re.DOTALL)


@dataclass(frozen=True)
class CommandLine:
    """コマンドとみなした行。"""

    # 打った行（末尾の空白を除く）。例: /fix test_a.py
    line: str
    name: str
    # 名前の後ろの文。前後の空白を除く。無ければ空の文字列
    arguments: str


def parse_command(line: str) -> CommandLine | None:
    """行がコマンドなら、名前と引数に分ける。コマンドでなければ None。"""
    match = _LINE.fullmatch(line)
    if match is None or not NAME.fullmatch(match[1]):
        return None
    return CommandLine(line.rstrip(), match[1], match[2].strip())
