"""道具 run_command: シェルのコマンドを走らせ、終了コードと出力を返す。

モデルは、コードを直した後にテストを走らせ、この結果を読んで確かめる。終了コードが 0 で
ないこと（テストの失敗など）と時間切れは、モデルが求めた情報なので、誤りの結果にしない。
誤りにするのは、コマンドを走らせられなかったときだけである。
"""

from pathlib import Path
from typing import cast

from local_coding_agent.model.chat import ToolDefinition
from local_coding_agent.tools.process import Finished, run_shell
from local_coding_agent.tools.tool import Tool, ToolError, ToolInput

DEFAULT_TIMEOUT = 120
MAX_TIMEOUT = 600
# モデルに返す出力の字数の上限。超えたら、先頭と末尾を半分ずつ残す
MAX_OUTPUT = 10_000
NO_OUTPUT = "（出力なし）"

DEFINITION = ToolDefinition(
    name="run_command",
    description=(
        "シェルのコマンドを /bin/sh -c で走らせ、終了コードと出力"
        "（標準出力と標準エラーを合わせたもの）を返す。"
        "コードを直した後に、テストを走らせて確かめるときに使う。"
        "毎回、作業ディレクトリで走る。cd と環境変数は、次のコマンドに残らない。"
        "標準入力は空である。入力を待つコマンドと、終わらないコマンド（サーバなど）は走らせない。"
        f"出力が {MAX_OUTPUT} 字を超えると、間を省く。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "走らせるコマンド"},
            "timeout": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_TIMEOUT,
                "description": (
                    f"終わるのを待つ秒数。過ぎたら止める。既定は {DEFAULT_TIMEOUT}"
                ),
            },
        },
        "required": ["command"],
    },
)


def run(arguments: ToolInput, cwd: Path) -> str:
    """コマンドを走らせ、1行目に終了コードか時間切れ、2行目から出力を書いた文を返す。"""
    command = _command(arguments)
    # 入力は、実行の前に定義と照らしてある
    timeout = cast(int, arguments.get("timeout", DEFAULT_TIMEOUT))
    try:
        finished = run_shell(command, cwd, timeout)
    except OSError as error:
        reason = error.strerror or error
        message = f"走らせられない: {reason}（作業ディレクトリ: {cwd}）"
        raise ToolError(message) from None
    return "\n".join((_status(finished, timeout), _output(finished.output)))


def preview(arguments: ToolInput, cwd: Path) -> str:
    """実行の前に人に見せる、走らせるコマンド。"""
    return f"$ {_command(arguments)}"


def summary(result: str) -> str:
    """画面に出す結果の1行。結果の文の1行目（終了コードか時間切れ）と行数。"""
    lines = result.splitlines()
    return f"{lines[0]}・{len(lines)} 行"


def clip(text: str) -> str:
    """MAX_OUTPUT 字を超えたら、先頭と末尾を半分ずつ残し、間に省いたことの1行を挟む。"""
    if len(text) <= MAX_OUTPUT:
        return text
    half = MAX_OUTPUT // 2
    note = f"（中略: {len(text) - 2 * half} 字。全体は {len(text)} 字）"
    return "\n".join((text[:half], note, text[-half:]))


def _command(arguments: ToolInput) -> str:
    """走らせるコマンド。走らせられないと分かれば ToolError。"""
    command = cast(str, arguments["command"])
    if not command.strip():
        raise ToolError("command が空である")
    if "\0" in command:
        raise ToolError("command に NUL の字がある")
    return command


def _status(finished: Finished, timeout: int) -> str:
    if finished.exit_code is None:
        return f"時間切れ: {timeout} 秒で止めた"
    return f"終了コード: {finished.exit_code}"


def _output(output: str) -> str:
    """モデルに返す出力。末尾の改行を除き、無ければその知らせ、長ければ間を省いたもの。"""
    text = output.rstrip("\n")
    return clip(text) if text else NO_OUTPUT


def target(arguments: ToolInput) -> str:
    """許可の規則と照らすコマンド。"""
    return cast(str, arguments["command"])


TOOL = Tool(
    definition=DEFINITION,
    kind="command",
    run=run,
    preview=preview,
    summary=summary,
    target=target,
)
