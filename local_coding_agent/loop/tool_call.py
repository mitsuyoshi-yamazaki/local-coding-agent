"""ループの1歩: モデルが呼んだ道具を、1つずつ順に実行し、表示し、走行の記録に書く。

実行の前に、道具があるか・入力が定義に合うか・（変更を伴う道具なら）下見を見せて人が許すかを
見る。どこで止まっても、誤りの結果（is_error）としてモデルに返し、ループは続ける。
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass

from local_coding_agent.loop.session import Session
from local_coding_agent.model.messages import ToolResultBlock, ToolUseBlock
from local_coding_agent.permissions.confirm import REFUSED, confirm
from local_coding_agent.tools.input_check import input_problem
from local_coding_agent.tools.tool import Tool, ToolError, find_tool

# 利用者が Ctrl-C で止めたときに、まだ結果の無い呼び出しに入れる結果
STOPPED = "利用者が止めた"


@dataclass(frozen=True)
class ToolRun:
    """道具の呼び出しを1つ処理した結果。"""

    result: ToolResultBlock
    # 人に確かめたか。None は問わなかった、True は許した、False は拒んだ
    confirmed: bool | None = None
    # 道具の関数を実行した時間。実行しなかったら None
    seconds: float | None = None
    # 実行の前に人に見せた下見。見せなかったら None
    preview: str | None = None


@dataclass(frozen=True)
class ToolResults:
    """1回の応答の呼び出しを処理した結果。"""

    # 呼び出しと同じ順の結果
    blocks: tuple[ToolResultBlock, ...]
    # 途中で利用者が Ctrl-C で止めたか
    stopped: bool = False


def run_tool_calls(
    session: Session, uses: Sequence[ToolUseBlock], turn: int, step: int
) -> ToolResults:
    """1回の応答の呼び出しを順に処理し、結果を同じ順で返す。

    途中で Ctrl-C を押されたら、そのときの呼び出しと残りの呼び出しに「利用者が止めた」の
    結果を入れて返す。呼び出しの全てが結果を持つので、そのまま履歴に足せる。
    """
    blocks: tuple[ToolResultBlock, ...] = ()
    for use in uses:
        try:
            blocks = (*blocks, run_tool_call(session, use, turn, step))
        except KeyboardInterrupt:
            rest = uses[len(blocks) :]
            stopped = tuple(_stop(session, other, turn, step) for other in rest)
            return ToolResults((*blocks, *stopped), stopped=True)
    return ToolResults(blocks)


def run_tool_call(
    session: Session, use: ToolUseBlock, turn: int, step: int
) -> ToolResultBlock:
    """呼び出しを1つ処理し、呼び出しと結果を1行ずつ表示する。"""
    session.output.write(f"[道具] {use.name} {_json(dict(use.input))}\n")
    run = execute(session, use)
    session.output.write(f"→ {result_summary(run.result)}\n")
    session.trace.write(tool_record(turn, step, use, run))
    return run.result


def execute(session: Session, use: ToolUseBlock) -> ToolRun:
    """道具を探し、入力を照らし、変更を伴う道具なら下見を見せて人に確かめてから実行する。"""
    tool = find_tool(session.tools, use.name)
    if tool is None:
        names = ", ".join(known.name for known in session.tools)
        return ToolRun(_error(use, f"知らない道具: {use.name}（使える道具: {names}）"))
    problem = input_problem(tool.definition.input_schema, use.input)
    if problem is not None:
        return ToolRun(_error(use, f"入力が定義に合わない: {problem}"))
    if not tool.changes:
        return _run(session, tool, use, preview=None)
    try:
        preview = tool.preview(use.input, session.cwd) if tool.preview else None
    except ToolError as error:
        # 下見で誤りが分かれば（置き換え元が見つからない、など）、人に問わない
        return ToolRun(_error(use, str(error)))
    if preview is not None:
        session.output.write(preview + "\n")
    if not confirm(session.read_line):
        return ToolRun(_error(use, REFUSED), confirmed=False, preview=preview)
    return _run(session, tool, use, preview)


def _run(
    session: Session, tool: Tool, use: ToolUseBlock, preview: str | None
) -> ToolRun:
    """道具の関数を実行し、時間を測る。"""
    started = session.clock()
    try:
        result = ToolResultBlock(use.id, tool.run(use.input, session.cwd))
    except ToolError as error:
        result = _error(use, str(error))
    confirmed = True if tool.changes else None
    return ToolRun(result, confirmed, session.clock() - started, preview)


def _stop(session: Session, use: ToolUseBlock, turn: int, step: int) -> ToolResultBlock:
    """止めたときの、まだ結果の無い呼び出しの結果。走行の記録にも書く。"""
    run = ToolRun(_error(use, STOPPED))
    session.trace.write(tool_record(turn, step, use, run))
    return run.result


def _error(use: ToolUseBlock, text: str) -> ToolResultBlock:
    return ToolResultBlock(use.id, text, is_error=True)


def result_summary(result: ToolResultBlock) -> str:
    """結果の1行。誤りならその文、そうでなければ結果の文の行数。"""
    if result.is_error:
        return f"誤り: {result.content}"
    return f"{len(result.content.splitlines())} 行"


def tool_record(
    turn: int, step: int, use: ToolUseBlock, run: ToolRun
) -> dict[str, object]:
    """道具の呼び出し1つの、走行の記録。"""
    return {
        "type": "tool",
        "turn": turn,
        "step": step,
        "id": use.id,
        "name": use.name,
        "input": dict(use.input),
        "confirmed": run.confirmed,
        "result": run.result.content,
        "is_error": run.result.is_error,
        "seconds": run.seconds,
        "preview": run.preview,
    }


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)
