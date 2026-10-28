import io
import tempfile
import unittest
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path

from local_coding_agent.cli import repl
from local_coding_agent.commands.builtin import CLEARED
from local_coding_agent.commands.custom import COMMANDS_PATH
from local_coding_agent.model.chat import Done, ModelError, TextDelta, ToolCall
from local_coding_agent.model.messages import user_text
from local_coding_agent.permissions.confirm import PROMPT as CONFIRM
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
REPLY: list[Step] = [TextDelta("はい"), STOP]
WRITE = fake_tool("write", lambda arguments, cwd: "書いた", kind="edit")


def at(minutes: int) -> datetime:
    """偽物の今の時刻で、START から minutes 分の後。偽物は1回呼ぶごとに1分進む。"""
    return START + timedelta(minutes=minutes)


class Repl:
    """偽物で REPL を走らせた結果。"""

    def __init__(
        self,
        lines: list[str | BaseException],
        script: list[list[Step]],
        cwd: Path = Path("/fake/cwd"),
    ) -> None:
        self.model = ScriptedModel(script)
        self.trace = RecordingTrace()
        self.output = io.StringIO()
        self.lines = ScriptedLines(*lines)
        session = fake_session(
            self.model, (WRITE,), self.lines, self.trace, self.output, cwd
        )
        repl.run(session)
        self.text = self.output.getvalue()

    def commands(self) -> list[Mapping[str, object]]:
        return self.trace.of_type("command")


class BuiltinInReplTest(unittest.TestCase):
    def test_builtin_does_not_call_model(self) -> None:
        run = Repl(["/help", "/context", "/mode"], [])
        self.assertEqual(run.model.sent, [])
        self.assertEqual(run.trace.of_type("request"), [])
        self.assertIn("組み込みのコマンド:", run.text)
        self.assertIn("許可のモード: ask\n", run.text)
        self.assertEqual([record["kind"] for record in run.commands()], ["builtin"] * 3)

    def test_clear_starts_new_conversation_and_keeps_counting_turns(self) -> None:
        run = Repl(["a", "/clear", "b"], [REPLY, REPLY])
        self.assertEqual(run.model.sent[1], (user_text("b", at(1)),))
        self.assertEqual([r["turn"] for r in run.trace.of_type("request")], [1, 2])
        self.assertIn(CLEARED + "\n", run.text)

    def test_context_after_turn(self) -> None:
        run = Repl(["a", "/context", "/clear", "/context"], [REPLY])
        self.assertIn(
            "[文脈] 発言 2（依頼 1・モデル 1・道具の結果 0）・最後の要求の入力 7 トークン\n",
            run.text,
        )
        self.assertIn(
            "発言 0（依頼 0・モデル 0・道具の結果 0）・最後の要求の入力 まだ無い",
            run.text,
        )

    def test_context_keeps_tokens_when_turn_has_no_finished_response(self) -> None:
        run = Repl(["a", "b", "/context"], [REPLY, [ModelError("繋がらない")]])
        self.assertIn(
            "発言 2（依頼 1・モデル 1・道具の結果 0）・最後の要求の入力 7 トークン",
            run.text,
        )

    def test_mode_changes_next_decision(self) -> None:
        script: list[list[Step]] = [[ToolCall("c", "write", {}), STOP], REPLY] * 2
        asked = Repl(["書いて"], script)
        self.assertIn(CONFIRM, asked.lines.prompts)
        changed = Repl(["/mode accept-edits", "書いて"], script)
        self.assertNotIn(CONFIRM, changed.lines.prompts)
        self.assertIn("[許可] 通す: モード accept-edits", changed.text)
        record = changed.commands()[0]
        self.assertEqual(record["output"], "許可のモード: ask → accept-edits")

    def test_exit_ends_without_reading_more(self) -> None:
        run = Repl(["/exit", "a"], [REPLY])
        self.assertEqual(run.model.sent, [])
        self.assertEqual(run.lines.prompts, ["> "])
        self.assertEqual(run.text, "")

    def test_refused_arguments_do_nothing(self) -> None:
        run = Repl(["a", "/clear all", "b"], [REPLY, REPLY])
        self.assertEqual(len(run.model.sent[1]), 3)
        self.assertIn("/clear は引数を取らない\n", run.text)


class PromptTest(unittest.TestCase):
    def test_ctrl_c_at_prompt_reads_next_line_and_end_of_input_ends(self) -> None:
        run = Repl([KeyboardInterrupt(), "a"], [REPLY])
        self.assertEqual(run.model.sent, [(user_text("a", at(0)),)])
        self.assertEqual(run.lines.prompts, ["> ", "> ", "> "])
        self.assertTrue(run.text.startswith("\n"))
        self.assertTrue(run.text.endswith("]\n\n"))


class UnknownAndRequestTest(unittest.TestCase):
    def test_unknown_command_is_not_sent_and_does_not_count_a_turn(self) -> None:
        run = Repl(["/nope x", "a"], [REPLY])
        self.assertEqual(run.model.sent, [(user_text("a", at(0)),)])
        self.assertEqual(run.trace.of_type("request")[0]["turn"], 1)
        self.assertIn(
            "誤り: 知らないコマンド: /nope（/help で一覧。依頼として送るなら、"
            "行の頭に空白を置く）\n",
            run.text,
        )
        record = run.commands()[0]
        self.assertEqual(
            {key: record[key] for key in ("line", "name", "kind", "turn", "text")},
            {
                "line": "/nope x",
                "name": "nope",
                "kind": "unknown",
                "turn": None,
                "text": None,
            },
        )

    def test_lines_that_are_not_commands_are_requests(self) -> None:
        run = Repl([" /nope", "/tmp/a.txt を読んで"], [REPLY, REPLY])
        self.assertEqual(run.model.sent[0], (user_text(" /nope", at(0)),))
        self.assertEqual(run.model.sent[1][-1], user_text("/tmp/a.txt を読んで", at(1)))
        self.assertEqual(run.commands(), [])


class CustomInReplTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cwd = Path(directory.name)
        (self.cwd / COMMANDS_PATH).mkdir(parents=True)

    def write(self, name: str, data: str | bytes) -> None:
        path = self.cwd / COMMANDS_PATH / name
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8")

    def test_sends_expanded_text_with_command_metadata(self) -> None:
        self.write("fix.md", "---\ndescription: 直す\n---\n\n直せ: $ARGUMENTS\n")
        run = Repl(["/fix a.py"], [REPLY], self.cwd)
        expected = user_text("直せ: a.py", at(0), command="/fix a.py")
        self.assertEqual(run.model.sent, [(expected,)])
        self.assertIn(
            "[コマンド] /fix → .local-coding-agent/commands/fix.md（1 行を依頼として送る）\n",
            run.text,
        )
        record = run.commands()[0]
        self.assertEqual(
            {key: record[key] for key in ("kind", "turn", "source", "text")},
            {
                "kind": "custom",
                "turn": 1,
                "source": str(COMMANDS_PATH / "fix.md"),
                "text": "直せ: a.py",
            },
        )

    def test_custom_turn_continues_history(self) -> None:
        self.write("again.md", "もう一度")
        run = Repl(["a", "/again"], [REPLY, REPLY], self.cwd)
        self.assertEqual(len(run.model.sent[1]), 3)
        self.assertEqual(run.trace.of_type("request")[1]["turn"], 2)

    def test_builtin_wins_over_custom_with_same_name(self) -> None:
        self.write("clear.md", "消さずに送る")
        run = Repl(["a", "/clear", "/help", "b"], [REPLY, REPLY], self.cwd)
        self.assertEqual(run.model.sent[1], (user_text("b", at(1)),))
        self.assertIn(
            "/clear    消さずに送る（組み込みと同じ名前なので呼べない）", run.text
        )

    def test_empty_custom_is_not_sent(self) -> None:
        self.write("empty.md", "---\ndescription: 空\n---\n\n")
        run = Repl(["/empty"], [], self.cwd)
        self.assertEqual(run.model.sent, [])
        self.assertIn("誤り: /empty の中身が空なので送らない\n", run.text)

    def test_empty_custom_with_arguments_is_not_sent(self) -> None:
        self.write("empty.md", "\n")
        self.write("only.md", "$ARGUMENTS")
        run = Repl(["/empty a.py", "/only"], [], self.cwd)
        self.assertEqual(run.model.sent, [])
        self.assertIn("誤り: /empty の中身が空なので送らない\n", run.text)
        self.assertIn("誤り: /only の中身が空なので送らない\n", run.text)
        self.assertEqual([r["turn"] for r in run.commands()], [None, None])

    def test_unreadable_custom_is_not_sent(self) -> None:
        self.write("bad.md", b"\xff")
        run = Repl(["/bad", "a"], [REPLY], self.cwd)
        self.assertEqual(run.model.sent, [(user_text("a", at(0)),)])
        self.assertIn("誤り: /bad を読めない: ", run.text)
        self.assertEqual(run.commands()[0]["kind"], "custom")

    def test_help_lists_custom(self) -> None:
        self.write("fix.md", "---\ndescription: 直す\n---\n本文")
        run = Repl(["/help"], [], self.cwd)
        self.assertIn("自作のコマンド（.local-coding-agent/commands/）:\n", run.text)
        self.assertIn("  /fix      直す\n", run.text)


if __name__ == "__main__":
    unittest.main()
