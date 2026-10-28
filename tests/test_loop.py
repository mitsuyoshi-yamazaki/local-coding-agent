import io
import unittest
from collections.abc import Mapping
from pathlib import Path

from local_coding_agent.loop.tool_call import STOPPED
from local_coding_agent.loop.turn import CANCELLED_NOTE, ERROR_NOTE, run_turn
from local_coding_agent.model.chat import Done, ModelError, TextDelta, ToolCall
from local_coding_agent.model.messages import (
    Message,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    assistant_message,
    assistant_text,
    tool_results,
    user_text,
)
from local_coding_agent.permissions.confirm import PROMPT, REFUSED
from local_coding_agent.tools.tool import Tool, ToolError
from tests.fakes import (
    START,
    RecordingTrace,
    ScriptedLines,
    ScriptedModel,
    Step,
    fake_session,
    fake_tool,
)

STOP = Done(done_reason="stop", stats={"prompt_eval_count": 7, "eval_count": 2})


def echo(arguments: Mapping[str, object], cwd: Path) -> str:
    return f"echo: {arguments.get('text', '')}"


def interrupted(arguments: Mapping[str, object], cwd: Path) -> str:
    raise KeyboardInterrupt


def failing(arguments: Mapping[str, object], cwd: Path) -> str:
    raise ToolError("読めない")


ECHO = fake_tool("echo", echo)


def call(name: str, call_id: str | None = None, **arguments: object) -> ToolCall:
    return ToolCall(id=call_id, name=name, input=arguments)


class Run:
    """偽物で1回の依頼を処理した結果。"""

    def __init__(
        self,
        script: list[list[Step]],
        tools: tuple[Tool, ...] = (ECHO,),
        lines: tuple[str | BaseException, ...] = (),
        history: tuple[Message, ...] = (),
    ) -> None:
        self.model = ScriptedModel(script)
        self.trace = RecordingTrace()
        self.output = io.StringIO()
        self.read_line = ScriptedLines(*lines)
        session = fake_session(
            self.model, tools, self.read_line, self.trace, self.output
        )
        self.history = run_turn(session, history, "依頼", 1)

    def results(self, call_number: int) -> tuple[object, ...]:
        """call_number 回目に呼んだときに送った、最後の発言の塊。"""
        return self.model.sent[call_number - 1][-1].content


class LoopTest(unittest.TestCase):
    def test_tool_result_is_added_and_model_is_called_again(self) -> None:
        run = Run(
            [
                [TextDelta("見る。"), call("echo", "call_a", text="x"), STOP],
                [TextDelta("答え"), STOP],
            ]
        )
        use = ToolUseBlock("call_a", "echo", {"text": "x"})
        expected = (
            user_text("依頼", START),
            assistant_message("見る。", [use]),
            tool_results([ToolResultBlock("call_a", "echo: x")]),
        )
        self.assertEqual(run.model.sent, [expected[:1], expected])
        self.assertEqual(run.history, (*expected, assistant_text("答え")))

    def test_sends_tool_definitions_every_call(self) -> None:
        run = Run([[call("echo"), STOP], [STOP]])
        self.assertEqual(run.model.tools, [(ECHO.definition,), (ECHO.definition,)])

    def test_response_without_tool_calls_ends_turn(self) -> None:
        run = Run([[TextDelta("答え"), STOP]])
        self.assertEqual(len(run.model.sent), 1)
        self.assertEqual(
            run.history, (user_text("依頼", START), assistant_text("答え"))
        )

    def test_keeps_earlier_history(self) -> None:
        earlier = (user_text("前"), assistant_text("前の答え"))
        run = Run([[TextDelta("答え"), STOP]], history=earlier)
        self.assertEqual(run.history[:2], earlier)

    def test_calls_in_one_response_run_in_order_with_ids(self) -> None:
        run = Run([[call("echo", text="1"), call("echo", text="2"), STOP], [STOP]])
        self.assertEqual(
            run.results(2),
            (
                ToolResultBlock("call_1_1_0", "echo: 1"),
                ToolResultBlock("call_1_1_1", "echo: 2"),
            ),
        )

    def test_loops_while_model_calls_tools(self) -> None:
        run = Run([[call("echo"), STOP], [call("echo"), STOP], [STOP]])
        self.assertEqual(len(run.model.sent), 3)
        self.assertEqual(len(run.history), 6)


class ToolErrorTest(unittest.TestCase):
    def test_unknown_tool(self) -> None:
        run = Run([[call("nope", "c"), STOP], [STOP]])
        self.assertEqual(
            run.results(2),
            (ToolResultBlock("c", "知らない道具: nope（使える道具: echo）", True),),
        )

    def test_input_not_matching_definition(self) -> None:
        tool = fake_tool("echo", echo, required=("text",))
        run = Run([[call("echo", "c"), STOP], [STOP]], tools=(tool,))
        self.assertEqual(
            run.results(2),
            (ToolResultBlock("c", "入力が定義に合わない: 必須の欄が無い: text", True),),
        )

    def test_tool_error_becomes_error_result(self) -> None:
        tool = fake_tool("fail", failing)
        run = Run([[call("fail", "c"), STOP], [STOP]], tools=(tool,))
        self.assertEqual(run.results(2), (ToolResultBlock("c", "読めない", True),))


class ConfirmInLoopTest(unittest.TestCase):
    def test_changing_tool_runs_when_allowed(self) -> None:
        tool = fake_tool("write", echo, kind="edit")
        run = Run([[call("write", "c"), STOP], [STOP]], (tool,), ("y",))
        self.assertEqual(run.read_line.prompts, [PROMPT])
        self.assertEqual(run.results(2), (ToolResultBlock("c", "echo: "),))
        self.assertIs(run.trace.of_type("tool")[0]["confirmed"], True)

    def test_refused_tool_is_not_run_and_loop_continues(self) -> None:
        tool = fake_tool("write", interrupted, kind="edit")
        run = Run(
            [[call("write", "c"), STOP], [TextDelta("分かった"), STOP]], (tool,), ("n",)
        )
        self.assertEqual(run.results(2), (ToolResultBlock("c", REFUSED, True),))
        self.assertEqual(run.history[-1], assistant_text("分かった"))
        record = run.trace.of_type("tool")[0]
        self.assertIs(record["confirmed"], False)
        self.assertIsNone(record["seconds"])

    def test_read_only_tool_is_not_confirmed(self) -> None:
        run = Run([[call("echo"), STOP], [STOP]])
        self.assertEqual(run.read_line.prompts, [])
        self.assertIsNone(run.trace.of_type("tool")[0]["confirmed"])


def shown(arguments: Mapping[str, object], cwd: Path) -> str:
    return "--- 差分"


def not_found(arguments: Mapping[str, object], cwd: Path) -> str:
    raise ToolError("置き換え元が見つからない")


class PreviewInLoopTest(unittest.TestCase):
    def test_preview_is_shown_before_asking(self) -> None:
        tool = fake_tool("write", echo, kind="edit", preview=shown)
        run = Run([[call("write", "c"), STOP], [STOP]], (tool,), ("y",))
        self.assertIn(
            "[道具] write {}\n--- 差分\n[許可] 問う: モード ask\n→ 1 行\n",
            run.output.getvalue(),
        )
        self.assertEqual(run.read_line.prompts, [PROMPT])
        self.assertEqual(run.trace.of_type("tool")[0]["preview"], "--- 差分")

    def test_refused_records_the_preview(self) -> None:
        tool = fake_tool("write", interrupted, kind="edit", preview=shown)
        run = Run([[call("write", "c"), STOP], [STOP]], (tool,), ("n",))
        record = run.trace.of_type("tool")[0]
        self.assertEqual((record["confirmed"], record["preview"]), (False, "--- 差分"))

    def test_preview_error_is_returned_without_asking(self) -> None:
        tool = fake_tool("write", interrupted, kind="edit", preview=not_found)
        run = Run([[call("write", "c"), STOP], [STOP]], (tool,))
        self.assertEqual(run.read_line.prompts, [])
        self.assertEqual(
            run.results(2), (ToolResultBlock("c", "置き換え元が見つからない", True),)
        )
        record = run.trace.of_type("tool")[0]
        self.assertEqual((record["confirmed"], record["preview"]), (None, None))


class CancelAndErrorTest(unittest.TestCase):
    """止めた回と誤りの回は、済んだ歩みまでを履歴に残す。済んだ歩みが無ければ足さない。"""

    earlier = (user_text("前"), assistant_text("前の答え"))
    request = user_text("依頼", START)
    use = ToolUseBlock("c", "echo", {"text": "x"})

    def kept(self, *last: ToolResultBlock | TextBlock) -> tuple[Message, ...]:
        """依頼と、echo を呼んだ1歩を残した履歴。最後の発言の塊は last。"""
        reply = assistant_message("", [self.use])
        return (*self.earlier, self.request, reply, Message("user", last))

    def test_ctrl_c_during_first_model_call_keeps_nothing(self) -> None:
        run = Run([[TextDelta("途中"), KeyboardInterrupt()]], history=self.earlier)
        self.assertEqual(run.history, self.earlier)
        self.assertEqual(run.trace.of_type("response")[0]["status"], "cancelled")
        self.assertIn("（止めた）\n（この回は履歴に足さない）\n", run.output.getvalue())

    def test_model_error_in_first_call_keeps_nothing(self) -> None:
        run = Run([[ModelError("繋がらない")]], history=self.earlier)
        self.assertEqual(run.history, self.earlier)
        self.assertIn(
            "誤り: 繋がらない\n（この回は履歴に足さない）\n", run.output.getvalue()
        )

    def test_ctrl_c_during_second_model_call_keeps_finished_steps(self) -> None:
        run = Run(
            [
                [call("echo", "c", text="x"), STOP],
                [TextDelta("途中"), KeyboardInterrupt()],
            ],
            history=self.earlier,
        )
        done = ToolResultBlock("c", "echo: x")
        self.assertEqual(run.history, self.kept(done, TextBlock(CANCELLED_NOTE)))
        self.assertIn(
            "（止めた）\n（済んだ歩みまでを履歴に残す）\n", run.output.getvalue()
        )

    def test_model_error_in_second_call_keeps_finished_steps(self) -> None:
        run = Run(
            [[call("echo", "c", text="x"), STOP], [ModelError("繋がらない")]],
            history=self.earlier,
        )
        done = ToolResultBlock("c", "echo: x")
        self.assertEqual(run.history, self.kept(done, TextBlock(ERROR_NOTE)))
        self.assertIn(
            "誤り: 繋がらない\n（済んだ歩みまでを履歴に残す）\n", run.output.getvalue()
        )

    def test_ctrl_c_during_tool_stops_the_rest(self) -> None:
        slow = fake_tool("slow", interrupted)
        run = Run(
            [[call("echo", "a"), call("slow", "b"), call("echo", "c"), STOP], [STOP]],
            (ECHO, slow),
            history=self.earlier,
        )
        self.assertEqual(len(run.model.sent), 1)
        self.assertEqual(
            run.history[-1].content,
            (
                ToolResultBlock("a", "echo: "),
                ToolResultBlock("b", STOPPED, True),
                ToolResultBlock("c", STOPPED, True),
                TextBlock(CANCELLED_NOTE),
            ),
        )
        results = [record["result"] for record in run.trace.of_type("tool")]
        self.assertEqual(results, ["echo: ", STOPPED, STOPPED])
        self.assertIn(
            "（止めた）\n（済んだ歩みまでを履歴に残す）\n", run.output.getvalue()
        )

    def test_ctrl_c_during_confirm(self) -> None:
        tool = fake_tool("write", echo, kind="edit")
        run = Run(
            [[call("write", "c"), STOP], [STOP]],
            (tool,),
            (KeyboardInterrupt(),),
            self.earlier,
        )
        self.assertEqual(len(run.model.sent), 1)
        self.assertEqual(
            run.history[-2], assistant_message("", [ToolUseBlock("c", "write", {})])
        )
        self.assertEqual(
            run.history[-1].content,
            (ToolResultBlock("c", STOPPED, True), TextBlock(CANCELLED_NOTE)),
        )


class OutputAndTraceTest(unittest.TestCase):
    def test_prints_calls_and_results(self) -> None:
        run = Run(
            [[call("echo", text="あ"), call("nope"), STOP], [TextDelta("答え"), STOP]]
        )
        output = run.output.getvalue()
        self.assertIn('[道具] echo {"text": "あ"}\n→ 1 行\n', output)
        self.assertIn("[道具] nope {}\n→ 誤り: 知らない道具: nope", output)
        self.assertEqual(output.count("[入力 7 トークン・"), 2)

    def test_records_steps_calls_and_tool_runs(self) -> None:
        run = Run([[call("echo", "c", text="x"), STOP], [TextDelta("答え"), STOP]])
        kinds = [(record["type"], record["step"]) for record in run.trace.records]
        self.assertEqual(
            kinds,
            [
                ("request", 1),
                ("response", 1),
                ("tool", 1),
                ("request", 2),
                ("response", 2),
            ],
        )
        first, second = run.trace.of_type("response")
        self.assertEqual(
            first["tool_calls"], [{"id": "c", "name": "echo", "input": {"text": "x"}}]
        )
        self.assertEqual(second["tool_calls"], [])
        self.assertEqual(
            run.trace.of_type("tool")[0],
            {
                "type": "tool",
                "turn": 1,
                "step": 1,
                "id": "c",
                "name": "echo",
                "input": {"text": "x"},
                "confirmed": None,
                "result": "echo: x",
                "is_error": False,
                "seconds": 0.5,
                "preview": None,
                "permission": {
                    "decision": "allow",
                    "reason": "モード ask",
                    "rule": None,
                    "rule_reason": None,
                },
            },
        )

    def test_first_token_counts_tool_call(self) -> None:
        run = Run([[call("echo"), STOP], [STOP]])
        measured = run.trace.of_type("response")[0]["measured"]
        self.assertEqual(measured, {"first_token_seconds": 0.5, "total_seconds": 1.0})


if __name__ == "__main__":
    unittest.main()
