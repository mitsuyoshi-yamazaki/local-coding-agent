"""端末の REPL。行を1つずつ受け、コマンドならハーネスが処理し、依頼ならループ（loop/turn.py）に渡す。

モデルの API は会話の状態を持たないので、履歴はここで持つ（Conversation）。回ごとに履歴を
ループへ渡し、その回を足した新しい履歴を受け取る。

/ で始まる行（commands/parse.py）は、組み込みのコマンド → 自作のコマンドの順に探す。組み込みは
モデルを呼ばない。自作は、ファイルの中身に引数を入れた文を、依頼としてループに渡す。
"""

from dataclasses import replace
from pathlib import Path
from typing import Literal

from local_coding_agent.cli.conversation import Conversation
from local_coding_agent.commands.builtin import find_builtin, run_builtin
from local_coding_agent.commands.custom import (
    CommandError,
    CustomCommand,
    expand,
    find_custom,
)
from local_coding_agent.commands.parse import CommandLine, parse_command
from local_coding_agent.loop.session import Session
from local_coding_agent.loop.turn import run_turn

PROMPT = "> "

# 走行の記録の、コマンドの件の kind
type CommandKind = Literal["builtin", "custom", "unknown"]


def run(session: Session) -> None:
    """入力の終わり（Ctrl-D）か /exit まで、行を受けて処理する。"""
    conversation = Conversation(session)
    while not conversation.finished:
        try:
            line = session.read_line(PROMPT)
        except EOFError:
            session.output.write("\n")
            return
        except KeyboardInterrupt:
            session.output.write("\n")
            continue
        if line.strip():
            conversation = handle_line(conversation, line)


def handle_line(conversation: Conversation, line: str) -> Conversation:
    """1行を処理し、新しい Conversation を返す。"""
    command = parse_command(line)
    if command is None:
        return _send(conversation, line)
    builtin = find_builtin(command.name)
    if builtin is not None:
        changed, output = run_builtin(builtin, conversation, command.arguments)
        _show(conversation, command, "builtin", output)
        return changed
    try:
        custom = find_custom(conversation.session.cwd, command.name)
    except CommandError as error:
        output = f"誤り: /{command.name} を読めない: {error}"
        _show(conversation, command, "custom", output)
        return conversation
    if custom is None:
        output = (
            f"誤り: 知らないコマンド: /{command.name}"
            "（/help で一覧。依頼として送るなら、行の頭に空白を置く）"
        )
        _show(conversation, command, "unknown", output)
        return conversation
    return _send_custom(conversation, command, custom)


def _send_custom(
    conversation: Conversation, command: CommandLine, custom: CustomCommand
) -> Conversation:
    """自作のコマンドの中身に引数を入れ、依頼として送る。

    本文が空なら、引数があっても送らない（「ARGUMENTS: <引数>」だけの依頼にしない）。
    """
    text = expand(custom, command.arguments)
    if not custom.body.strip() or not text:
        output = f"誤り: /{command.name} の中身が空なので送らない"
        _show(conversation, command, "custom", output, source=custom.path)
        return conversation
    lines = len(text.splitlines())
    output = f"[コマンド] /{command.name} → {custom.path}（{lines} 行を依頼として送る）"
    turn = conversation.next_turn
    _show(
        conversation,
        command,
        "custom",
        output,
        turn=turn,
        source=custom.path,
        text=text,
    )
    return _send(conversation, text, command.line)


def _send(
    conversation: Conversation, text: str, command: str | None = None
) -> Conversation:
    """依頼として回を1つ始める。入力のトークン数は、その回で数えられなければ前の値を保つ。"""
    turn = conversation.next_turn
    result = run_turn(conversation.session, conversation.history, text, turn, command)
    tokens = result.input_tokens
    return replace(
        conversation,
        history=result.history,
        turn=turn,
        input_tokens=conversation.input_tokens if tokens is None else tokens,
    )


def _show(
    conversation: Conversation,
    command: CommandLine,
    kind: CommandKind,
    output: str,
    *,
    turn: int | None = None,
    source: Path | None = None,
    text: str | None = None,
) -> None:
    """コマンドの結果を画面に出し、走行の記録に1件を書く。"""
    session = conversation.session
    if output:
        session.output.write(output + "\n")
    session.trace.write(
        {
            "type": "command",
            "line": command.line,
            "name": command.name,
            "kind": kind,
            "turn": turn,
            "source": None if source is None else str(source),
            "text": text,
            "output": output,
        }
    )
