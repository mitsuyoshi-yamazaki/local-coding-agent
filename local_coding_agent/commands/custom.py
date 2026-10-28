"""自作のコマンド: 作業ディレクトリの .local-coding-agent/commands/<名前>.md に書いた手順。

呼ぶたびにファイルを読み（書き換えは次に呼んだときから効く）、本文の $ARGUMENTS を引数に
置き換えて、依頼としてモデルに送る。頭の --- の行から次の --- の行までは前付けで、その中の
description の行だけを読む。ファイルの形は次のとおり。

    ---
    description: テストを走らせ、失敗していれば直す
    ---

    テストを走らせよ。対象: $ARGUMENTS
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from local_coding_agent.commands.parse import NAME

COMMANDS_PATH = Path(".local-coding-agent") / "commands"
# 本文の中で、引数に置き換える印
PLACEHOLDER = "$ARGUMENTS"
# 前付けを囲む行
FENCE = "---"


class CommandError(Exception):
    """自作のコマンドのファイルを読めない。"""


@dataclass(frozen=True)
class CustomCommand:
    """読んだ自作のコマンド。"""

    name: str
    # 作業ディレクトリからのパス
    path: Path
    # 前付けの description。無ければ本文の最初の空でない行
    description: str
    # 前付けを除いた本文
    body: str


@dataclass(frozen=True)
class Listed:
    """/help の一覧の、自作のコマンドの1つ。"""

    # 名前の形に合えば /<名前>、合わなければファイルの名前
    label: str
    description: str
    # 呼べないときの理由。呼べるなら None
    problem: str | None = None


def find_custom(cwd: Path, name: str) -> CustomCommand | None:
    """名前のファイルを読む。ファイルが無ければ None、読めなければ CommandError。

    name は、parse.NAME の形に合っているものとする。
    """
    path = COMMANDS_PATH / f"{name}.md"
    if not (cwd / path).is_file():
        return None
    try:
        text = (cwd / path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise CommandError(error_reason(error)) from None
    return parse_custom(name, path, text)


def parse_custom(name: str, path: Path, text: str) -> CustomCommand:
    """ファイルの中身を、前付けの説明と本文に分ける。"""
    front, body = split_front_matter(text)
    description = _description(front) or _first_line(body)
    return CustomCommand(name, path, description, body)


def split_front_matter(text: str) -> tuple[tuple[str, ...], str]:
    """前付けの行（前後の空白を除く）と本文に分ける。

    前付けがあるのは、1行目が --- で、閉じる --- の行があるときだけである。無ければ、全体が本文。
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip() != FENCE:
        return (), text
    closing = next(
        (index for index in range(1, len(lines)) if lines[index].rstrip() == FENCE),
        None,
    )
    if closing is None:
        return (), text
    front = tuple(line.strip() for line in lines[1:closing])
    return front, "".join(lines[closing + 1 :])


def expand(command: CustomCommand, arguments: str) -> str:
    """モデルに送る本文。$ARGUMENTS を全て引数に置き換え、前後の空白を除く。

    本文に $ARGUMENTS が無く、引数があれば、末尾に空の行を挟んで「ARGUMENTS: <引数>」を足す。
    """
    if PLACEHOLDER in command.body:
        return command.body.replace(PLACEHOLDER, arguments).strip()
    if arguments:
        return f"{command.body.strip()}\n\nARGUMENTS: {arguments}".strip()
    return command.body.strip()


def list_custom(cwd: Path, builtin_names: Sequence[str]) -> tuple[Listed, ...]:
    """置き場の .md のファイルを、名前の順に並べる。置き場が無ければ空。

    組み込みと同じ名前のものは、組み込みが勝つので、呼べないものとして並べる。置き場の中を
    見られなければ（権限が無い、など）、置き場を読めないことの1つだけを並べる。
    """
    directory = cwd / COMMANDS_PATH
    if not directory.is_dir():
        return ()
    try:
        paths = sorted(
            path
            for path in directory.iterdir()
            if path.suffix == ".md" and path.is_file()
        )
    except OSError as error:
        return (Listed(f"{COMMANDS_PATH}/", "", f"読めない: {error_reason(error)}"),)
    return tuple(_listed(cwd, path.stem, builtin_names) for path in paths)


def _listed(cwd: Path, name: str, builtin_names: Sequence[str]) -> Listed:
    if not NAME.fullmatch(name):
        return Listed(f"{name}.md", "", "名前に使えない字があるので呼べない")
    try:
        command = find_custom(cwd, name)
    except CommandError as error:
        return Listed(f"/{name}", "", f"読めない: {error}")
    description = command.description if command else ""
    if name in builtin_names:
        return Listed(f"/{name}", description, "組み込みと同じ名前なので呼べない")
    return Listed(f"/{name}", description)


def error_reason(error: OSError | UnicodeDecodeError) -> str:
    """読めない理由の文。OSError の文は手元の絶対パスを含むので、理由だけにする。"""
    if isinstance(error, OSError) and error.strerror:
        return error.strerror
    return str(error)


def _description(front: Sequence[str]) -> str:
    """前付けの description の値。囲みの引用符を外す。無ければ空の文字列。"""
    for line in front:
        key, colon, value = line.partition(":")
        if colon and key.strip() == "description":
            return _unquote(value.strip())
    return ""


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _first_line(body: str) -> str:
    return next((line.strip() for line in body.splitlines() if line.strip()), "")
