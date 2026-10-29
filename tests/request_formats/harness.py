"""場面を、起動の入口（__main__.main）から実物のコードに通し、送る直前の要求の本文を集める。

差し替えるのは、モデルの応答（台本）・利用者の入力・時刻・環境の節の中身・家のディレクトリ・
画面だけである。要求は、実物の OllamaChat.build_request で作る。
"""

import io
import json
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from local_coding_agent.__main__ import main
from local_coding_agent.context.environment import Environment
from local_coding_agent.model.chat import ChatRequest, StreamEvent, ToolDefinition
from local_coding_agent.model.messages import Message
from local_coding_agent.model.ollama import OllamaChat
from tests.fakes import START, ScriptedLines, ticking_now
from tests.request_formats.scenario import Scenario, Step

MODEL = "qwen3.5:9b"
# 「# 環境」の節に入れる、決まった環境。手元の機械の値を文書に入れないため
ENVIRONMENT = Environment(
    working_directory=Path("/work/project"),
    in_git_repository=True,
    os="macOS 15.6（Darwin 24.6.0）",
)

type Body = dict[str, object]


class RunError(Exception):
    """場面を走らせられない・台本や見どころと要求が合わない。"""


class ScriptedOllama:
    """要求は実物の OllamaChat で作り、応答は台本で返す。送る本文を覚えておく。"""

    def __init__(self, real: OllamaChat, script: Sequence[Sequence[Step]]) -> None:
        self.real = real
        self.script = script
        self.bodies: list[Body] = []

    def build_request(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolDefinition],
    ) -> ChatRequest:
        return self.real.build_request(system, messages, tools)

    def stream(self, request: ChatRequest) -> Iterator[StreamEvent]:
        # 実物と同じく JSON にしてから読み戻す。送る文字列と同じ中身になる
        body: Body = json.loads(json.dumps(request.body))
        self.bodies.append(body)
        if len(self.bodies) > len(self.script):
            raise RunError(f"台本に無い要求（{len(self.bodies)} 番目）")
        for step in self.script[len(self.bodies) - 1]:
            if isinstance(step, BaseException):
                raise step
            yield step


def run_scenario(scenario: Scenario) -> tuple[Body, ...]:
    """場面を走らせ、送った要求の本文を順に返す。"""
    with tempfile.TemporaryDirectory() as root:
        top = Path(root).resolve()
        cwd, home = top / "project", top / "home"
        cwd.mkdir()
        home.mkdir()
        for name, text in scenario.files.items():
            path = cwd / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        bodies = tuple(_run_main(scenario, cwd, home).bodies)
        _check_no_local_path(scenario, bodies, (root, str(top)))
    if len(bodies) != len(scenario.script):
        used = f"{len(bodies)} / {len(scenario.script)}"
        raise RunError(f"{scenario.title}: 台本の応答を使い切っていない（{used}）")
    return bodies


def _run_main(scenario: Scenario, cwd: Path, home: Path) -> ScriptedOllama:
    made: list[ScriptedOllama] = []

    def make_model(host: str, model: str) -> ScriptedOllama:
        made.append(ScriptedOllama(OllamaChat(host=host, model=model), scenario.script))
        return made[-1]

    args = [arg.replace("{directory}", str(cwd)) for arg in scenario.args]
    errors = io.StringIO()
    with ExitStack() as stack:
        target = "local_coding_agent.__main__"
        stack.enter_context(mock.patch(f"{target}.OllamaChat", make_model))
        stack.enter_context(
            mock.patch(f"{target}.collect_environment", return_value=ENVIRONMENT)
        )
        stack.enter_context(mock.patch(f"{target}.local_now", ticking_now(START)))
        stack.enter_context(mock.patch.object(Path, "home", return_value=home))
        lines = ScriptedLines(*scenario.lines)
        stack.enter_context(mock.patch("builtins.input", lines))
        stack.enter_context(redirect_stdout(io.StringIO()))
        stack.enter_context(redirect_stderr(errors))
        code = main(["--model", MODEL, "--directory", str(cwd), *args])
    if code != 0 or not made:
        raise RunError(f"{scenario.title}: 起動できない: {errors.getvalue()}")
    return made[0]


def _check_no_local_path(
    scenario: Scenario, bodies: Sequence[Body], paths: Sequence[str]
) -> None:
    """手元の一時ディレクトリのパスが、要求に入っていないか。入れば文書に書けない。"""
    text = json.dumps(bodies, ensure_ascii=False)
    for path in paths:
        if path in text:
            raise RunError(f"{scenario.title}: 要求に手元のパスが入った: {path}")
