"""ループの1歩: モデルが呼んだ道具を、1つずつ順に実行し、表示し、走行の記録に書く。

実行の前に、道具があるか・入力が定義に合うか・許可の判定（通す・問う・拒む）を見る。
問うときは、下見を見せて人が許すかを確かめる。どこで止まっても、誤りの結果（is_error）として
モデルに返し、ループは続ける。
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass

from local_coding_agent.loop.session import Session
from local_coding_agent.model.messages import ToolResultBlock, ToolUseBlock
from local_coding_agent.permissions.confirm import REFUSED, confirm
from local_coding_agent.permissions.policy import (
    DENIED,
    VERDICT_WORDS,
    Decision,
    decide,
)
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
    # 許可の判定。判定の前に誤りになったら None
    permission: Decision | None = None


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
    tool = find_tool(session.tools, use.name)
    session.output.write(f"→ {result_summary(run.result, tool)}\n")
    session.trace.write(tool_record(turn, step, use, run))
    return run.result


def execute(session: Session, use: ToolUseBlock) -> ToolRun:
    """道具を探し、入力を照らし、許可を判定する。問うなら、下見を見せて人に確かめてから
    実行する。
    """
    tool = find_tool(session.tools, use.name)
    if tool is None:
        names = ", ".join(known.name for known in session.tools)
        return ToolRun(_error(use, f"知らない道具: {use.name}（使える道具: {names}）"))
    problem = input_problem(tool.definition.input_schema, use.input)
    if problem is not None:
        return ToolRun(_error(use, f"入力が定義に合わない: {problem}"))
    # 下見の前に判定する。拒む呼び出しのために、ファイルを読まないため
    decision = decide(session.permissions, tool, use.input, session.cwd)
    if decision.verdict == "deny":
        _show_decision(session, decision)
        return ToolRun(_error(use, f"{DENIED}: {decision.rule}"), permission=decision)
    try:
        preview = tool.preview(use.input, session.cwd) if tool.preview else None
    except ToolError as error:
        # 下見で誤りが分かれば（置き換え元が見つからない、など）、人に問わない
        return ToolRun(_error(use, str(error)), permission=decision)
    if preview is not None:
        session.output.write(preview + "\n")
    # 読む道具をモードで通すときだけは、何も出さない（F-05 までと同じ表示）
    quiet = tool.kind == "read" and decision.verdict == "allow" and not decision.rule
    if not quiet:
        _show_decision(session, decision)
    if decision.verdict == "allow":
        return _run(session, tool, use, preview, decision)
    if not confirm(session.read_line):
        return ToolRun(_error(use, REFUSED), False, None, preview, decision)
    return _run(session, tool, use, preview, decision, confirmed=True)


def _show_decision(session: Session, decision: Decision) -> None:
    words = VERDICT_WORDS[decision.verdict]
    session.output.write(f"[許可] {words}: {decision.reason}\n")


def _run(
    session: Session,
    tool: Tool,
    use: ToolUseBlock,
    preview: str | None,
    permission: Decision,
    confirmed: bool | None = None,
) -> ToolRun:
    """道具の関数を実行し、時間を測る。"""
    started = session.clock()
    try:
        result = ToolResultBlock(use.id, tool.run(use.input, session.cwd))
    except ToolError as error:
        result = _error(use, str(error))
    seconds = session.clock() - started
    return ToolRun(result, confirmed, seconds, preview, permission)


def _stop(session: Session, use: ToolUseBlock, turn: int, step: int) -> ToolResultBlock:
    """止めたときの、まだ結果の無い呼び出しの結果。走行の記録にも書く。"""
    run = ToolRun(_error(use, STOPPED))
    session.trace.write(tool_record(turn, step, use, run))
    return run.result


def _error(use: ToolUseBlock, text: str) -> ToolResultBlock:
    return ToolResultBlock(use.id, text, is_error=True)


def result_summary(result: ToolResultBlock, tool: Tool | None = None) -> str:
    """結果の1行。誤りならその文。そうでなければ、道具が結果の1行を作る関数を持てば
    その1行、持たなければ結果の文の行数。
    """
    if result.is_error:
        return f"誤り: {result.content}"
    if tool is not None and tool.summary is not None:
        return tool.summary(result.content)
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
        "permission": _permission_record(run.permission),
    }


def _permission_record(decision: Decision | None) -> dict[str, object] | None:
    if decision is None:
        return None
    return {
        "decision": decision.verdict,
        "reason": decision.reason,
        "rule": decision.rule,
    }


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)
