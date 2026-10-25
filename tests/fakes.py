"""テストで使う偽物。実物のモデルにも、通信にも繋がない。"""

import io
from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

from local_coding_agent.loop.session import Session
from local_coding_agent.model.chat import ChatRequest, StreamEvent, ToolDefinition
from local_coding_agent.model.messages import Message
from local_coding_agent.tools.tool import Tool, ToolInput

# 台本の1歩。応答の断片か終わりの知らせ、または投げる例外（Ctrl-C や通信の誤りを真似る）
type Step = StreamEvent | BaseException

START = datetime(2026, 10, 24, 15, 30, tzinfo=timezone(timedelta(hours=9)))


class ScriptedModel:
    """決めた台本どおりに応答を返す、偽物のモデル。送られた system prompt・道具の定義・会話を全て覚えておく。"""

    def __init__(self, script: Sequence[Sequence[Step]]) -> None:
        self.script = script
        self.systems: list[str] = []
        self.tools: list[tuple[ToolDefinition, ...]] = []
        self.sent: list[tuple[Message, ...]] = []

    def build_request(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolDefinition],
    ) -> ChatRequest:
        self.systems.append(system)
        self.tools.append(tuple(tools))
        self.sent.append(tuple(messages))
        return ChatRequest(url="http://fake/api/chat", body={"call": len(self.sent)})

    def stream(self, request: ChatRequest) -> Iterator[StreamEvent]:
        for step in self.script[len(self.sent) - 1]:
            if isinstance(step, BaseException):
                raise step
            yield step


class RecordingTrace:
    """書かれた記録を覚えておく、偽物の書き出し先。"""

    def __init__(self) -> None:
        self.records: list[Mapping[str, object]] = []

    def write(self, record: Mapping[str, object]) -> None:
        self.records.append(record)

    def of_type(self, kind: str) -> list[Mapping[str, object]]:
        """type が kind の記録だけ。"""
        return [record for record in self.records if record["type"] == kind]


class ScriptedLines:
    """決めた行を順に返し、尽きたら EOFError（Ctrl-D）を投げる、偽物の入力。

    行の代わりに例外を置くと、それを投げる（Ctrl-C を真似る）。出した問いの文を覚えておく。
    """

    def __init__(self, *lines: str | BaseException) -> None:
        self.remaining = iter(lines)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        line = next(self.remaining, None)
        if line is None:
            raise EOFError
        if isinstance(line, BaseException):
            raise line
        return line


def scripted_lines(*lines: str | BaseException) -> ScriptedLines:
    return ScriptedLines(*lines)


def ticking_clock(step: float = 0.5) -> Callable[[], float]:
    """呼ぶたびに step 秒ずつ進む、偽物の時計。"""
    ticks = iter(range(10_000))
    return lambda: next(ticks) * step


def ticking_now(
    start: datetime, step: timedelta = timedelta(minutes=1)
) -> Callable[[], datetime]:
    """呼ぶたびに step ずつ進む、偽物の今の時刻。"""
    ticks = iter(range(10_000))
    return lambda: start + next(ticks) * step


def fake_tool(
    name: str,
    run: Callable[[ToolInput, Path], str],
    changes: bool = False,
    required: Sequence[str] = (),
    preview: Callable[[ToolInput, Path], str] | None = None,
) -> Tool:
    """偽物の道具。入力の欄は全て文字列とする。"""
    schema = {
        "type": "object",
        "properties": {field: {"type": "string"} for field in required},
        "required": list(required),
    }
    return Tool(ToolDefinition(name, f"{name} の説明", schema), changes, run, preview)


def fake_session(
    model: ScriptedModel,
    tools: tuple[Tool, ...] = (),
    read_line: Callable[[str], str] | None = None,
    trace: RecordingTrace | None = None,
    output: io.StringIO | None = None,
    cwd: Path = Path("/fake/cwd"),
    show_thinking: bool = False,
) -> Session:
    """偽物で組んだ Session。作業ディレクトリは、既定では使わない場所にする。"""
    return Session(
        model=model,
        system="指示",
        tools=tools,
        cwd=cwd,
        read_line=read_line if read_line is not None else ScriptedLines(),
        output=output if output is not None else io.StringIO(),
        trace=trace if trace is not None else RecordingTrace(),
        clock=ticking_clock(),
        now=ticking_now(START),
        show_thinking=show_thinking,
    )
