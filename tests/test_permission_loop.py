"""許可の判定を、台本どおりに道具を呼ぶ偽物のモデルのループに掛ける。"""

import io
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path

from local_coding_agent.loop.turn import run_turn
from local_coding_agent.model.chat import Done, ToolCall
from local_coding_agent.model.messages import ToolResultBlock
from local_coding_agent.permissions.confirm import PROMPT
from local_coding_agent.permissions.policy import DENIED_NOTE, Mode, Permissions
from local_coding_agent.permissions.rules import Rule, parse_rule
from local_coding_agent.tools.default import DEFAULT_TOOLS
from tests.fakes import RecordingTrace, ScriptedLines, ScriptedModel, fake_session

STOP = Done(done_reason="stop", stats={})


class PermissionInLoopTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cwd = Path(directory.name).resolve()
        (self.cwd / "a.txt").write_text("a\n", encoding="utf-8")

    def run_call(
        self,
        call: ToolCall,
        mode: Mode = "allow-all",
        lines: Sequence[str] = (),
        allow: Sequence[str] = (),
        deny: Sequence[str] = (),
        reasons: Mapping[str, str] | None = None,
    ) -> None:
        """道具を1つ呼んで終わる回を、モードと規則を変えて走らせる。

        reasons は、規則の文字列から、その規則の理由への対応。
        """

        def rules(texts: Sequence[str]) -> tuple[Rule, ...]:
            parsed = (parse_rule(t, DEFAULT_TOOLS, self.cwd, self.cwd) for t in texts)
            return tuple(
                replace(rule, reason=(reasons or {}).get(str(rule))) for rule in parsed
            )

        permissions = Permissions(mode, rules(allow), (), rules(deny))
        self.model = ScriptedModel([[call, STOP], [STOP]])
        self.read_line = ScriptedLines(*lines)
        self.output = io.StringIO()
        self.trace = RecordingTrace()
        session = fake_session(
            self.model,
            DEFAULT_TOOLS,
            self.read_line,
            self.trace,
            self.output,
            cwd=self.cwd,
            permissions=permissions,
        )
        run_turn(session, (), "依頼", 1)

    def result(self) -> object:
        return self.model.sent[1][-1].content[0]

    def record(self) -> Mapping[str, object]:
        return self.trace.of_type("tool")[0]

    def test_denied_call_is_not_run_previewed_or_asked(self) -> None:
        call = ToolCall("c", "write_file", {"path": "a.txt", "content": "b\n"})
        self.run_call(call, "ask", deny=["write_file(a.txt)"])
        denied = f"規則で拒んだ: write_file(a.txt)。{DENIED_NOTE}"
        self.assertEqual(self.result(), ToolResultBlock("c", denied, is_error=True))
        self.assertEqual((self.cwd / "a.txt").read_text(encoding="utf-8"), "a\n")
        self.assertEqual(self.read_line.prompts, [])
        output = self.output.getvalue()
        self.assertIn(
            f"[許可] 拒む: 規則 deny: write_file(a.txt)\n→ 誤り: {denied}\n", output
        )
        self.assertNotIn("---", output)
        self.assertEqual(
            self.record()["permission"],
            {
                "decision": "deny",
                "reason": "規則 deny: write_file(a.txt)",
                "rule": "write_file(a.txt)",
                "rule_reason": None,
            },
        )

    def test_reason_of_the_rule_reaches_model_and_screen(self) -> None:
        call = ToolCall("c", "run_command", {"command": "rm a.txt"})
        reasons = {"run_command(rm *)": "ファイルを消さない"}
        self.run_call(call, deny=["run_command(rm *)"], reasons=reasons)
        result = self.result()
        assert isinstance(result, ToolResultBlock)
        self.assertIn("。理由: ファイルを消さない。", result.content)
        self.assertTrue((self.cwd / "a.txt").exists())
        self.assertIn(
            "[許可] 拒む: 規則 deny: run_command(rm *)（理由: ファイルを消さない）\n",
            self.output.getvalue(),
        )
        permission = self.record()["permission"]
        assert isinstance(permission, dict)
        self.assertEqual(permission["rule_reason"], "ファイルを消さない")

    def test_allowed_by_rule_runs_without_asking_and_shows_preview(self) -> None:
        call = ToolCall("c", "run_command", {"command": "echo 走った"})
        self.run_call(call, "ask", allow=["run_command(echo *)"])
        self.assertEqual(self.read_line.prompts, [])
        self.assertIn(
            "$ echo 走った\n[許可] 通す: 規則 allow: run_command(echo *)\n"
            "→ 終了コード: 0・2 行\n",
            self.output.getvalue(),
        )
        self.assertIsNone(self.record()["confirmed"])

    def test_mode_asks_and_records_confirmed(self) -> None:
        call = ToolCall("c", "run_command", {"command": "echo x"})
        self.run_call(call, "ask", lines=("y",))
        self.assertEqual(self.read_line.prompts, [PROMPT])
        self.assertIn("[許可] 問う: モード ask\n", self.output.getvalue())
        record = self.record()
        self.assertIs(record["confirmed"], True)
        self.assertEqual(
            record["permission"],
            {
                "decision": "ask",
                "reason": "モード ask",
                "rule": None,
                "rule_reason": None,
            },
        )

    def test_refused_after_asking(self) -> None:
        call = ToolCall("c", "write_file", {"path": "a.txt", "content": "b\n"})
        self.run_call(call, "ask", lines=("n",))
        self.assertEqual((self.cwd / "a.txt").read_text(encoding="utf-8"), "a\n")
        self.assertIs(self.record()["confirmed"], False)

    def test_reason_typed_at_the_question_reaches_the_model(self) -> None:
        call = ToolCall("c", "write_file", {"path": "a.txt", "content": "b\n"})
        self.run_call(call, "ask", lines=("a.txt は残す",))
        self.assertEqual(
            self.result(),
            ToolResultBlock("c", "利用者が実行を拒んだ。理由: a.txt は残す", True),
        )
        self.assertEqual((self.cwd / "a.txt").read_text(encoding="utf-8"), "a\n")
        self.assertIs(self.record()["confirmed"], False)

    def test_allow_all_runs_edits_without_asking(self) -> None:
        call = ToolCall("c", "write_file", {"path": "a.txt", "content": "b\n"})
        self.run_call(call)
        self.assertEqual(self.read_line.prompts, [])
        self.assertEqual((self.cwd / "a.txt").read_text(encoding="utf-8"), "b\n")
        self.assertIn("+b\n[許可] 通す: モード allow-all\n", self.output.getvalue())

    def test_reading_inside_by_mode_shows_nothing_extra(self) -> None:
        self.run_call(ToolCall("c", "read_file", {"path": "a.txt"}), "ask")
        self.assertNotIn("[許可]", self.output.getvalue())

    def test_reading_outside_asks(self) -> None:
        call = ToolCall("c", "list_directory", {"path": ".."})
        self.run_call(call, "ask")
        self.assertEqual(self.read_line.prompts, [PROMPT])
        self.assertIn(
            "[許可] 問う: モード ask・作業ディレクトリの外\n", self.output.getvalue()
        )
        # 入力の終わり（Ctrl-D）は拒んだとする
        self.assertEqual(
            self.result(), ToolResultBlock("c", "利用者が実行を拒んだ", is_error=True)
        )

    def test_input_error_has_no_permission(self) -> None:
        self.run_call(ToolCall("c", "read_file", {}), deny=["read_file"])
        self.assertIsNone(self.record()["permission"])


if __name__ == "__main__":
    unittest.main()
