"""道具 write_file: ファイルを丸ごと書く。無ければ作り、あれば中身を置き換える。"""

from pathlib import Path
from typing import cast

from local_coding_agent.model.chat import ToolDefinition
from local_coding_agent.tools.file_change import (
    FileChange,
    checked,
    file_tool,
    read_current,
)
from local_coding_agent.tools.lines import split_lines
from local_coding_agent.tools.tool import ToolInput, resolve

DEFINITION = ToolDefinition(
    name="write_file",
    description=(
        "ファイルを丸ごと書く。ファイルが無ければ作り（親のディレクトリも作る）、"
        "あれば中身を content で置き換える。既存のファイルの一部を直すときは edit_file を使う。"
        "実行の前に、利用者が差分を見て確かめる。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "書くファイル。作業ディレクトリからの相対パスか、絶対パス",
            },
            "content": {"type": "string", "description": "書く中身の全体"},
        },
        "required": ["path", "content"],
    },
)


def plan(arguments: ToolInput, cwd: Path) -> FileChange:
    """書く前と後の中身を組み立てる。"""
    # 入力は、実行の前に定義と照らしてある
    path = cast(str, arguments["path"])
    content = cast(str, arguments["content"]).replace("\r\n", "\n")
    current = read_current(resolve(cwd, path), path)
    before, newline = (None, "\n") if current is None else current
    verb = "新しいファイルを書いた" if before is None else "上書きした"
    result = f"{verb}: {path}（{len(split_lines(content))} 行）"
    return checked(
        FileChange(resolve(cwd, path), path, before, content, newline, result)
    )


TOOL = file_tool(DEFINITION, plan)
