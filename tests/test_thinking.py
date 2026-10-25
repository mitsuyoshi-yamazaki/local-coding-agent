import io
import unittest

from local_coding_agent.loop.model_call import THINKING_END, THINKING_START
from local_coding_agent.loop.turn import THINKING_ONLY, run_turn
from local_coding_agent.model.chat import Done, TextDelta, ThinkingDelta, ToolCall
from local_coding_agent.model.messages import assistant_text, user_text
from tests.fakes import (
    START,
    RecordingTrace,
    ScriptedModel,
    Step,
    fake_session,
    fake_tool,
)

STOP = Done(done_reason="stop", stats={"prompt_eval_count": 7, "eval_count": 2})
NOOP = fake_tool("noop", lambda arguments, cwd: "済んだ")


class Run:
    """偽物で1回の依頼を処理した結果。"""

    def __init__(self, script: list[list[Step]], show_thinking: bool = False) -> None:
        self.model = ScriptedModel(script)
        self.trace = RecordingTrace()
        self.output = io.StringIO()
        session = fake_session(
            self.model,
            (NOOP,),
            trace=self.trace,
            output=self.output,
            show_thinking=show_thinking,
        )
        self.history = run_turn(session, (), "依頼", 1)

    def response(self, step: int) -> dict[str, object]:
        return dict(self.trace.of_type("response")[step - 1])


# 推論の文を2つの断片で出してから、本文で答える応答
THOUGHT: list[Step] = [
    ThinkingDelta("考える。"),
    ThinkingDelta("続き"),
    TextDelta("答え"),
    STOP,
]


class RecordAndHistoryTest(unittest.TestCase):
    def test_thinking_is_hidden_by_default(self) -> None:
        run = Run([THOUGHT])
        output = run.output.getvalue()
        self.assertIn("答え", output)
        self.assertNotIn("考える", output)
        self.assertNotIn(THINKING_START, output)

    def test_thinking_is_recorded_without_option(self) -> None:
        run = Run([THOUGHT])
        self.assertEqual(run.response(1)["thinking"], "考える。続き")
        self.assertEqual(run.response(1)["text"], "答え")

    def test_reply_without_thinking_records_empty_thinking(self) -> None:
        run = Run([[TextDelta("答え"), STOP]])
        self.assertEqual(run.response(1)["thinking"], "")

    def test_thinking_is_not_added_to_history(self) -> None:
        run = Run([THOUGHT])
        self.assertEqual(
            run.history, (user_text("依頼", START), assistant_text("答え"))
        )

    def test_first_token_does_not_count_thinking(self) -> None:
        run = Run([[ThinkingDelta("考える"), STOP]])
        self.assertEqual(
            run.response(1)["measured"],
            {"first_token_seconds": None, "total_seconds": 0.5},
        )


class ShowThinkingTest(unittest.TestCase):
    def test_wraps_thinking_in_marks_before_text(self) -> None:
        run = Run([THOUGHT], show_thinking=True)
        self.assertIn(
            f"{THINKING_START}\n考える。続き\n{THINKING_END}\n答え\n",
            run.output.getvalue(),
        )

    def test_thinking_after_text_starts_on_new_line(self) -> None:
        run = Run(
            [[TextDelta("前"), ThinkingDelta("考え"), TextDelta("後"), STOP]],
            show_thinking=True,
        )
        self.assertIn(
            f"前\n{THINKING_START}\n考え\n{THINKING_END}\n後\n", run.output.getvalue()
        )

    def test_reply_without_thinking_has_no_marks(self) -> None:
        run = Run([[TextDelta("答え"), STOP]], show_thinking=True)
        self.assertNotIn(THINKING_START, run.output.getvalue())

    def test_marks_each_step(self) -> None:
        call = ToolCall(id="c", name="noop", input={})
        run = Run(
            [
                [ThinkingDelta("1"), call, STOP],
                [ThinkingDelta("2"), TextDelta("答え"), STOP],
            ],
            show_thinking=True,
        )
        self.assertEqual(run.output.getvalue().count(THINKING_END), 2)

    def test_ctrl_c_during_thinking_closes_marks_and_records(self) -> None:
        run = Run([[ThinkingDelta("考え"), KeyboardInterrupt()]], show_thinking=True)
        self.assertIn(
            f"{THINKING_START}\n考え\n{THINKING_END}\n\n（止めた）\n",
            run.output.getvalue(),
        )
        self.assertEqual(run.response(1)["status"], "cancelled")
        self.assertEqual(run.response(1)["thinking"], "考え")


class ThinkingOnlyTest(unittest.TestCase):
    def test_reply_without_text_and_calls_shows_notice(self) -> None:
        run = Run([[ThinkingDelta("考える"), STOP]])
        self.assertTrue(run.output.getvalue().endswith(THINKING_ONLY + "\n"))
        self.assertEqual(len(run.model.sent), 1)

    def test_blank_text_counts_as_no_text(self) -> None:
        run = Run([[ThinkingDelta("考える"), TextDelta("\n\n"), STOP]])
        self.assertIn(THINKING_ONLY, run.output.getvalue())

    def test_reply_with_text_has_no_notice(self) -> None:
        run = Run([THOUGHT])
        self.assertNotIn(THINKING_ONLY, run.output.getvalue())

    def test_reply_with_calls_has_no_notice(self) -> None:
        call = ToolCall(id="c", name="noop", input={})
        run = Run([[ThinkingDelta("考える"), call, STOP], [TextDelta("答え"), STOP]])
        self.assertNotIn(THINKING_ONLY, run.output.getvalue())


if __name__ == "__main__":
    unittest.main()
