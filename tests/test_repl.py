import io
import unittest

from local_coding_agent.cli import repl
from local_coding_agent.model.chat import Done, ModelError, TextDelta
from local_coding_agent.model.messages import assistant_text, user_text
from tests.fakes import (
    RecordingTrace,
    ScriptedModel,
    Step,
    scripted_lines,
    ticking_clock,
)

STOP = Done(done_reason="stop", stats={"prompt_eval_count": 7, "eval_count": 2})


def run_repl(
    lines: list[str], script: list[list[Step]]
) -> tuple[ScriptedModel, RecordingTrace, str]:
    """偽物で REPL を走らせ、モデル・記録・画面の出力を返す。"""
    model = ScriptedModel(script)
    trace = RecordingTrace()
    output = io.StringIO()
    session = repl.Session(
        model=model,
        read_line=scripted_lines(*lines),
        output=output,
        trace=trace,
        clock=ticking_clock(),
    )
    repl.run(session)
    return model, trace, output.getvalue()


class HistoryTest(unittest.TestCase):
    def test_sends_whole_history_every_turn(self) -> None:
        model, _, _ = run_repl(
            ["私は山田です", "私の名前は？"],
            [
                [TextDelta("はい、"), TextDelta("山田さん。"), STOP],
                [TextDelta("山田さん"), STOP],
            ],
        )
        self.assertEqual(model.sent[0], (user_text("私は山田です"),))
        self.assertEqual(
            model.sent[1],
            (
                user_text("私は山田です"),
                assistant_text("はい、山田さん。"),
                user_text("私の名前は？"),
            ),
        )

    def test_cancelled_turn_is_not_added(self) -> None:
        model, trace, output = run_repl(
            ["長い話をして", "短く"],
            [[TextDelta("昔々"), KeyboardInterrupt()], [TextDelta("はい"), STOP]],
        )
        self.assertEqual(model.sent[1], (user_text("短く"),))
        self.assertEqual(trace.records[1]["status"], "cancelled")
        self.assertEqual(trace.records[1]["text"], "昔々")
        self.assertIn("止めた", output)

    def test_error_turn_is_not_added(self) -> None:
        model, trace, output = run_repl(
            ["こんにちは", "もう一度"],
            [[ModelError("Ollama に繋がらない")], [TextDelta("はい"), STOP]],
        )
        self.assertEqual(model.sent[1], (user_text("もう一度"),))
        self.assertEqual(trace.records[1]["status"], "error")
        self.assertIn("誤り: Ollama に繋がらない", output)

    def test_stream_without_done_is_error(self) -> None:
        model, trace, _ = run_repl(
            ["a", "b"], [[TextDelta("途中")], [TextDelta("はい"), STOP]]
        )
        self.assertEqual(model.sent[1], (user_text("b"),))
        self.assertEqual(trace.records[1]["status"], "error")

    def test_blank_lines_are_skipped(self) -> None:
        model, _, _ = run_repl(["", "   ", "a"], [[TextDelta("x"), STOP]])
        self.assertEqual(model.sent, [(user_text("a"),)])


class OutputAndTraceTest(unittest.TestCase):
    def test_streams_text_and_prints_numbers(self) -> None:
        _, _, output = run_repl(["a"], [[TextDelta("こん"), TextDelta("にちは"), STOP]])
        self.assertIn("こんにちは", output)
        self.assertIn("[入力 7 トークン・出力 2 トークン・", output)

    def test_records_request_and_response_in_turn(self) -> None:
        _, trace, _ = run_repl(["a"], [[TextDelta("x"), STOP]])
        request, response = trace.records
        self.assertEqual(request["type"], "request")
        self.assertEqual(request["turn"], 1)
        self.assertEqual(request["url"], "http://fake/api/chat")
        self.assertEqual(response["type"], "response")
        self.assertEqual(response["status"], "done")
        self.assertEqual(response["text"], "x")
        self.assertEqual(response["done_reason"], "stop")
        self.assertEqual(
            response["model_stats"], {"prompt_eval_count": 7, "eval_count": 2}
        )
        self.assertEqual(
            response["measured"], {"first_token_seconds": 0.5, "total_seconds": 1.0}
        )


if __name__ == "__main__":
    unittest.main()
