import io
import unittest
from datetime import datetime, timedelta, timezone

from local_coding_agent.cli import repl
from local_coding_agent.cli.screen import BELL, DIM, RESET
from local_coding_agent.model.chat import (
    Done,
    ModelError,
    OtherFields,
    RawLine,
    TextDelta,
    ThinkingDelta,
)
from local_coding_agent.model.messages import assistant_text, user_text
from tests.fakes import (
    RecordingTrace,
    ScriptedModel,
    Step,
    scripted_lines,
    ticking_clock,
    ticking_now,
)

STOP = Done(done_reason="stop", stats={"prompt_eval_count": 7, "eval_count": 2})
START = datetime(2026, 10, 24, 15, 30, tzinfo=timezone(timedelta(hours=9)))
PLAIN = repl.Display()


def at(minutes: int) -> datetime:
    """偽物の今の時刻で、START から minutes 分の後。偽物は1回呼ぶごとに1分進む。"""
    return START + timedelta(minutes=minutes)


def run_repl(
    lines: list[str],
    script: list[list[Step]],
    display: repl.Display = PLAIN,
) -> tuple[ScriptedModel, RecordingTrace, str]:
    """偽物で REPL を走らせ、モデル・記録・画面の出力を返す。"""
    model = ScriptedModel(script)
    trace = RecordingTrace()
    output = io.StringIO()
    session = repl.Session(
        model=model,
        system="指示",
        read_line=scripted_lines(*lines),
        output=output,
        trace=trace,
        clock=ticking_clock(),
        now=ticking_now(START),
        display=display,
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
        self.assertEqual(model.sent[0], (user_text("私は山田です", at(0)),))
        self.assertEqual(
            model.sent[1],
            (
                user_text("私は山田です", at(0)),
                assistant_text("はい、山田さん。"),
                user_text("私の名前は？", at(1)),
            ),
        )

    def test_cancelled_turn_is_not_added(self) -> None:
        model, trace, output = run_repl(
            ["長い話をして", "短く"],
            [[TextDelta("昔々"), KeyboardInterrupt()], [TextDelta("はい"), STOP]],
        )
        self.assertEqual(model.sent[1], (user_text("短く", at(1)),))
        self.assertEqual(trace.records[1]["status"], "cancelled")
        self.assertEqual(trace.records[1]["text"], "昔々")
        self.assertIn("止めた", output)

    def test_error_turn_is_not_added(self) -> None:
        model, trace, output = run_repl(
            ["こんにちは", "もう一度"],
            [[ModelError("Ollama に繋がらない")], [TextDelta("はい"), STOP]],
        )
        self.assertEqual(model.sent[1], (user_text("もう一度", at(1)),))
        self.assertEqual(trace.records[1]["status"], "error")
        self.assertIn("誤り: Ollama に繋がらない", output)

    def test_stream_without_done_is_error(self) -> None:
        model, trace, _ = run_repl(
            ["a", "b"], [[TextDelta("途中")], [TextDelta("はい"), STOP]]
        )
        self.assertEqual(model.sent[1], (user_text("b", at(1)),))
        self.assertEqual(trace.records[1]["status"], "error")

    def test_blank_lines_are_skipped(self) -> None:
        model, _, _ = run_repl(["", "   ", "a"], [[TextDelta("x"), STOP]])
        self.assertEqual(model.sent, [(user_text("a", at(0)),)])

    def test_continued_lines_are_one_request(self) -> None:
        model, _, _ = run_repl(["一行目\\", "二行目"], [[TextDelta("x"), STOP]])
        self.assertEqual(model.sent, [(user_text("一行目\n二行目", at(0)),)])

    def test_request_with_arrow_key_is_not_sent(self) -> None:
        model, _, output = run_repl(["ab\x1b[Dc", "a"], [[TextDelta("x"), STOP]])
        self.assertEqual(model.sent, [(user_text("a", at(0)),)])
        self.assertIn("（矢印キーなどの、行を編集するキーは使えない。", output)


class SystemPromptAndMetadataTest(unittest.TestCase):
    def test_sends_same_system_prompt_every_turn(self) -> None:
        model, _, _ = run_repl(
            ["a", "b"], [[TextDelta("x"), STOP], [TextDelta("y"), STOP]]
        )
        self.assertEqual(model.systems, ["指示", "指示"])

    def test_messages_keep_the_time_they_were_sent(self) -> None:
        model, _, _ = run_repl(
            ["a", "b"], [[TextDelta("x"), STOP], [TextDelta("y"), STOP]]
        )
        first, reply, second = model.sent[1]
        self.assertEqual(first.sent_at, at(0))
        self.assertIsNone(reply.sent_at)
        self.assertEqual(second.sent_at, at(1))


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


# 推論の文から本文へ進み、終わりの行にほかの欄が載った応答
THINKING_SCRIPT: list[Step] = [
    RawLine('{"thinking": "考え"}'),
    ThinkingDelta("考え"),
    RawLine('{"thinking": "中"}'),
    ThinkingDelta("中"),
    RawLine('{"content": "答え"}'),
    TextDelta("答え"),
    OtherFields({"done_reason": "stop"}),
    STOP,
]


class DebugDisplayTest(unittest.TestCase):
    def test_off_shows_only_text(self) -> None:
        _, _, output = run_repl(["a"], [THINKING_SCRIPT])
        self.assertIn("答え", output)
        self.assertNotIn("考え", output)
        self.assertNotIn("done_reason", output)

    def test_readable_shows_thinking_text_and_fields_on_own_lines(self) -> None:
        _, _, output = run_repl(
            ["a"], [THINKING_SCRIPT], repl.Display(debug="readable")
        )
        self.assertIn('考え中\n答え\n{"done_reason": "stop"}\n[入力 7', output)
        self.assertNotIn('{"thinking"', output)

    def test_raw_shows_received_lines_only(self) -> None:
        _, trace, output = run_repl(["a"], [THINKING_SCRIPT], repl.Display(debug="raw"))
        self.assertIn(
            '{"thinking": "考え"}\n{"thinking": "中"}\n{"content": "答え"}\n[入力 7',
            output,
        )
        self.assertNotIn("考え中", output)
        self.assertEqual(trace.records[1]["text"], "答え")

    def test_color_dims_thinking_only_when_enabled(self) -> None:
        display = repl.Display(color=True, debug="readable")
        _, _, output = run_repl(["a"], [THINKING_SCRIPT], display)
        self.assertIn(f"{DIM}考え{RESET}", output)
        self.assertIn("\n答え", output)
        _, _, plain = run_repl(["a"], [THINKING_SCRIPT], repl.Display(debug="readable"))
        self.assertNotIn(DIM, plain)


class SeparationTest(unittest.TestCase):
    def test_blank_lines_around_reply(self) -> None:
        _, _, output = run_repl(
            ["a", "b"], [[TextDelta("x"), STOP], [TextDelta("y\n"), STOP]]
        )
        numbers = (
            "[入力 7 トークン・出力 2 トークン・最初の文字まで 0.50 秒・全体 1.00 秒]"
        )
        # 端末では、各回の最初の空行の前に、入力の行（> a）がある。最後の改行は Ctrl-D の後のもの
        self.assertEqual(output, f"\nx\n{numbers}\n\n" + f"\ny\n{numbers}\n\n" + "\n")

    def test_numbers_are_dim_but_error_is_not(self) -> None:
        _, _, output = run_repl(
            ["a", "b"],
            [[TextDelta("x"), STOP], [ModelError("繋がらない")]],
            repl.Display(color=True),
        )
        self.assertIn(f"x\n{DIM}[入力 7", output)
        self.assertIn("\n\n誤り: 繋がらない（この回は履歴に足さない）\n\n", output)


class BellTest(unittest.TestCase):
    def test_rings_after_reply_and_error_but_not_cancel(self) -> None:
        _, _, output = run_repl(
            ["a", "b", "c"],
            [
                [TextDelta("x"), STOP],
                [ModelError("繋がらない")],
                [TextDelta("y"), KeyboardInterrupt()],
            ],
            repl.Display(bell=True),
        )
        self.assertEqual(output.count(BELL), 2)
        # 数値の行の後に鳴らす
        self.assertIn(f"全体 1.00 秒]\n{BELL}", output)

    def test_silent_when_disabled(self) -> None:
        _, _, output = run_repl(["a"], [[TextDelta("x"), STOP]])
        self.assertNotIn(BELL, output)


if __name__ == "__main__":
    unittest.main()
