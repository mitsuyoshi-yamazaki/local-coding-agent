"""ファイルを書く道具（write_file・edit_file）が共に使う、変更の組み立て・差分・書き込み。

道具は、入力から、書く前と書いた後の中身を組み立てる（FileChange）。下見では、その差分を返して
人に見せ、実行では、組み立て直して書く。中身は改行を \\n に揃えて持ち、書くときにファイルの
改行に戻す。
"""

import difflib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from local_coding_agent.model.chat import ToolDefinition
from local_coding_agent.tools.lines import split_lines
from local_coding_agent.tools.tool import Tool, ToolError, ToolInput

# 新しいファイルの差分で、書く前の側に置く名前
NO_FILE = "/dev/null"
# 差分で、末尾に改行が無い行の後に置く印（git と同じ）
NO_NEWLINE = "\\ No newline at end of file"


@dataclass(frozen=True)
class FileChange:
    """1つのファイルへの変更。"""

    target: Path
    # モデルが渡したパス。差分と結果の文に使う
    shown: str
    # 書く前の中身。新しいファイルなら None
    before: str | None
    after: str
    # ファイルの改行。中身は \n に揃えてあり、書くときにこれに戻す
    newline: str
    # 書いた後に、道具の結果としてモデルに返す文
    result: str


def file_tool(
    definition: ToolDefinition, plan: Callable[[ToolInput, Path], FileChange]
) -> Tool:
    """ファイルを書く道具。下見は変更の差分を返し、実行は変更を組み立て直して書く。
    許可の規則とは、入力の path を照らす。
    """
    return Tool(
        definition=definition,
        kind="edit",
        run=lambda arguments, cwd: write(plan(arguments, cwd)),
        preview=lambda arguments, cwd: diff_text(plan(arguments, cwd)),
        target=lambda arguments: cast(str, arguments["path"]),
    )


def read_current(target: Path, shown: str) -> tuple[str, str] | None:
    """今の中身（改行を \\n に揃えたもの）と、ファイルの改行。ファイルが無ければ None。"""
    try:
        text = target.read_text(encoding="utf-8", newline="")
    except FileNotFoundError:
        return None
    except IsADirectoryError:
        raise ToolError(f"ディレクトリである: {shown}") from None
    except UnicodeDecodeError:
        raise ToolError(f"UTF-8 として読めない: {shown}（書き換えない）") from None
    except ValueError as error:
        # パスに NUL の字があるときなど
        raise ToolError(f"パスとして使えない: {shown}（{error}）") from None
    except OSError as error:
        raise ToolError(f"読めない: {shown}（{error.strerror}）") from None
    crlf = text.count("\r\n")
    if crlf and crlf != text.count("\n"):
        # 書くときに1つの改行へ揃えると、変えていない行の改行まで変わり、差分にも出ないため
        message = f"改行に \\r\\n と \\n が混ざっている: {shown}（書き換えない）"
        raise ToolError(message)
    newline = "\r\n" if crlf else "\n"
    return text.replace("\r\n", "\n"), newline


def checked(change: FileChange) -> FileChange:
    """中身が変わる変更なら、そのまま返す。変わらなければ ToolError。"""
    if change.before == change.after:
        raise ToolError(f"書いても中身が変わらない: {change.shown}")
    return change


def diff_text(change: FileChange) -> str:
    """書く前と後の中身の差分（unified diff。前後3行）。"""
    before = [] if change.before is None else _diff_lines(change.before)
    fromfile = NO_FILE if change.before is None else change.shown
    lines = difflib.unified_diff(
        before, _diff_lines(change.after), fromfile, change.shown, lineterm=""
    )
    return "\n".join(lines)


def _diff_lines(text: str) -> list[str]:
    """差分で比べる行。末尾に改行が無ければ、git と同じく、最後の行の後に印の行を足す。

    印が無いと、末尾の改行だけを変えたときに差分が空になる。
    """
    lines = split_lines(text)
    if not text or text.endswith("\n"):
        return lines
    return [*lines[:-1], lines[-1] + "\n" + NO_NEWLINE]


def write(change: FileChange) -> str:
    """変更を書き、結果の文を返す。親のディレクトリが無ければ作る。"""
    try:
        change.target.parent.mkdir(parents=True, exist_ok=True)
        change.target.write_text(
            change.after.replace("\n", change.newline), encoding="utf-8", newline=""
        )
    except OSError as error:
        raise ToolError(f"書けない: {change.shown}（{error.strerror}）") from None
    return change.result
