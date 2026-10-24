"""道具 read_file: ファイルを読み、行番号を付けて返す。

形は cat -n と同じ（右に寄せた行番号・タブ・行）。Claude Code の Read の道具に倣い、既定では
先頭から 2000 行を読み、長いファイルは offset と limit で分けて読ませる。
"""

from pathlib import Path
from typing import cast

from local_coding_agent.model.chat import ToolDefinition
from local_coding_agent.tools.tool import Tool, ToolError, ToolInput, resolve

DEFAULT_LIMIT = 2000
# これより長い行は、ここで切る
MAX_LINE_LENGTH = 2000

DEFINITION = ToolDefinition(
    name="read_file",
    description=(
        "ファイルを読む。行番号を付けて返す（cat -n と同じ形）。"
        f"既定では先頭から {DEFAULT_LIMIT} 行を読む。"
        "長いファイルは offset と limit で続きを読む。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "読むファイル。作業ディレクトリからの相対パスか、絶対パス",
            },
            "offset": {
                "type": "integer",
                "minimum": 1,
                "description": "何行目から読むか。既定は 1",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "description": f"何行読むか。既定は {DEFAULT_LIMIT}",
            },
        },
        "required": ["path"],
    },
)


def run(arguments: ToolInput, cwd: Path) -> str:
    """ファイルの offset 行目から limit 行を、行番号を付けて返す。"""
    # 入力は、実行の前に定義と照らしてある
    path = cast(str, arguments["path"])
    offset = cast(int, arguments.get("offset", 1))
    limit = cast(int, arguments.get("limit", DEFAULT_LIMIT))
    lines = _lines(_read_text(resolve(cwd, path), path))
    if not lines:
        return "（空のファイル）"
    if offset > len(lines):
        raise ToolError(f"offset が行数を超えている（{path} は {len(lines)} 行）")
    chosen = lines[offset - 1 : offset - 1 + limit]
    numbered = [_numbered(offset + index, line) for index, line in enumerate(chosen)]
    return "\n".join([*numbered, *_rest_notice(len(lines), offset + len(chosen))])


def _read_text(target: Path, shown: str) -> str:
    """ファイルの中身。読めなければ、理由を ToolError で知らせる。"""
    try:
        return target.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ToolError(f"ファイルが無い: {shown}") from None
    except IsADirectoryError:
        message = f"ディレクトリである（中身は list_directory で見る）: {shown}"
        raise ToolError(message) from None
    except UnicodeDecodeError:
        raise ToolError(f"UTF-8 として読めない: {shown}") from None
    except ValueError as error:
        # パスに NUL の字があるときなど
        raise ToolError(f"パスとして使えない: {shown}（{error}）") from None
    except OSError as error:
        raise ToolError(f"読めない: {shown}（{error.strerror}）") from None


def _lines(text: str) -> list[str]:
    """行に分ける。read_text は改行を \\n に揃えるので、\\n で分ける。末尾の改行の後は行にしない。"""
    lines = text.split("\n")
    return lines[:-1] if lines[-1] == "" else lines


def _numbered(number: int, line: str) -> str:
    """行番号を付けた1行。長い行は切り、切ったことを書き添える。"""
    if len(line) <= MAX_LINE_LENGTH:
        return f"{number:6}\t{line}"
    notice = f"（この行は {len(line)} 字。{MAX_LINE_LENGTH} 字で切った）"
    return f"{number:6}\t{line[:MAX_LINE_LENGTH]}…{notice}"


def _rest_notice(total: int, next_line: int) -> list[str]:
    """読み残した行があれば、全体の行数と、続きの読み方を知らせる行。"""
    if next_line > total:
        return []
    return [
        "",
        f"（全体は {total} 行。続きは、offset に {next_line} を渡して読む）",
    ]


TOOL = Tool(definition=DEFINITION, changes=False, run=run)
