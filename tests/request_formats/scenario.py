"""場面の形: 利用者が打つ行・偽物のモデルの台本・見どころ。

見どころは、ある情報が、要求の本文のどこに、どの伝わり方で入るかである。生成のときに、
その場所に照らした文があるかを確かめる（check.py）。
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Literal

from local_coding_agent.model.chat import (
    Done,
    StreamEvent,
    TextDelta,
    ThinkingDelta,
    ToolCall,
)

type Frame = Literal["field", "frame", "value", "text", "not-sent"]
# 台本の1歩。応答の断片か終わりの知らせ、または投げる例外（Ctrl-C や通信の誤りを真似る）
type Step = StreamEvent | BaseException
# 見どころの情報を作るコード（関数かクラス）
type Maker = Callable[..., object]

FRAME_WORDS: dict[Frame, str] = {
    "field": "Ollama の欄",
    "frame": "ハーネスの枠",
    "value": "ハーネスの値",
    "text": "そのままの文",
    "not-sent": "送らない",
}


@dataclass(frozen=True)
class Highlight:
    """見どころ1つ。"""

    # 何の情報か
    info: str
    frame: Frame
    # 何番目の要求か（1から）
    request: int
    # 本文の中の場所。例: messages[1].content
    path: str
    # 情報を作るコード
    made_by: tuple[Maker, ...] = ()
    # その場所の値（文でなければ JSON にしたもの）が含む文
    contains: str = ""
    # その場所の値が含まない文
    excludes: str = ""
    # その場所の値が並びなら、要素の数
    count: int | None = None


@dataclass(frozen=True)
class Scenario:
    """場面1つ。起動して、行を順に打ち、入力の終わりで終える。"""

    title: str
    # 利用者が何をし、何が分かるか
    summary: str
    # 打つ行。実行してよいかの問いへの答えも、問われる順に入れる
    lines: tuple[str, ...]
    # 要求ごとの応答
    script: tuple[tuple[Step, ...], ...]
    highlights: tuple[Highlight, ...]
    # 作業ディレクトリに置くファイル（作業ディレクトリからのパスと中身）
    files: Mapping[str, str] = field(default_factory=dict)
    # 起動の引数（--model と --directory のほか）。{directory} は作業ディレクトリに替える
    args: tuple[str, ...] = ()


def reply(text: str, thinking: str = "") -> tuple[Step, ...]:
    """本文で答え、道具を呼ばない応答。"""
    return (*_thinking(thinking), TextDelta(text), Done("stop"))


def calls(*uses: ToolCall, thinking: str = "") -> tuple[Step, ...]:
    """道具を呼ぶ応答。"""
    return (*_thinking(thinking), *uses, Done("stop"))


def call(call_id: str, tool: str, /, **arguments: object) -> ToolCall:
    """道具の呼び出し1つ。id は、Ollama が付ける id と同じ形にする。

    入力の欄の名前（load_skill の name など）と重ならないよう、id と道具の名前は位置で渡す。
    """
    return ToolCall(id=call_id, name=tool, input=arguments)


def _thinking(text: str) -> tuple[Step, ...]:
    return (ThinkingDelta(text),) if text else ()
