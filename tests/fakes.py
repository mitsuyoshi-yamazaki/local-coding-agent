"""テストで使う偽物。実物のモデルにも、通信にも繋がない。"""

from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import datetime, timedelta

from local_coding_agent.model.chat import ChatRequest, StreamEvent
from local_coding_agent.model.messages import Message

# 台本の1歩。応答の断片か終わりの知らせ、または投げる例外（Ctrl-C や通信の誤りを真似る）
type Step = StreamEvent | BaseException


class ScriptedModel:
    """決めた台本どおりに応答を返す、偽物のモデル。送られた system prompt と会話を全て覚えておく。"""

    def __init__(self, script: Sequence[Sequence[Step]]) -> None:
        self.script = script
        self.systems: list[str] = []
        self.sent: list[tuple[Message, ...]] = []

    def build_request(self, system: str, messages: Sequence[Message]) -> ChatRequest:
        self.systems.append(system)
        self.sent.append(tuple(messages))
        return ChatRequest(url="http://fake/api/chat", body={"turn": len(self.sent)})

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


def scripted_lines(*lines: str) -> Callable[[str], str]:
    """決めた行を順に返し、尽きたら EOFError（Ctrl-D）を投げる、偽物の入力。"""
    remaining = iter(lines)

    def read_line(prompt: str) -> str:
        try:
            return next(remaining)
        except StopIteration:
            raise EOFError from None

    return read_line


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
