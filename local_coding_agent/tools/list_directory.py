"""道具 list_directory: ディレクトリの中身を1段だけ見る。"""

from pathlib import Path
from typing import cast

from local_coding_agent.model.chat import ToolDefinition
from local_coding_agent.tools.tool import Tool, ToolError, ToolInput, resolve

DEFINITION = ToolDefinition(
    name="list_directory",
    description=(
        "ディレクトリの中身を1段だけ見る。名前を1行に1つ、名前の順に返す。"
        "ディレクトリの名前の末尾には / を付ける。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "見るディレクトリ。作業ディレクトリからの相対パスか、絶対パス。"
                    "既定は作業ディレクトリ"
                ),
            },
        },
    },
)


def run(arguments: ToolInput, cwd: Path) -> str:
    """中の名前を、1行に1つ、名前の順に返す。"""
    # 入力は、実行の前に定義と照らしてある
    path = cast(str, arguments.get("path", "."))
    names = [_name(entry) for entry in _entries(resolve(cwd, path), path)]
    return "\n".join(names) if names else "（空のディレクトリ）"


def _entries(target: Path, shown: str) -> list[Path]:
    """中のファイルとディレクトリ。見られなければ、理由を ToolError で知らせる。"""
    try:
        return sorted(target.iterdir(), key=lambda entry: entry.name)
    except FileNotFoundError:
        raise ToolError(f"ディレクトリが無い: {shown}") from None
    except NotADirectoryError:
        message = (
            f"ディレクトリではなくファイルである（中身は read_file で読む）: {shown}"
        )
        raise ToolError(message) from None
    except ValueError as error:
        # パスに NUL の字があるときなど
        raise ToolError(f"パスとして使えない: {shown}（{error}）") from None
    except OSError as error:
        raise ToolError(f"見られない: {shown}（{error.strerror}）") from None


def _name(entry: Path) -> str:
    return f"{entry.name}/" if entry.is_dir() else entry.name


def target(arguments: ToolInput) -> str:
    """許可の規則と照らすパス。無ければ作業ディレクトリ。"""
    return cast(str, arguments.get("path", "."))


TOOL = Tool(definition=DEFINITION, kind="read", run=run, target=target)
