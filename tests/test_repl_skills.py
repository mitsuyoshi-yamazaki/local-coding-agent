import io
import unittest
from collections.abc import Mapping

from local_coding_agent.cli import repl
from local_coding_agent.commands.builtin import CLEARED
from local_coding_agent.commands.custom import COMMANDS_PATH
from local_coding_agent.model.chat import Done, TextDelta, ToolCall
from local_coding_agent.model.messages import (
    Message,
    ToolResultBlock,
    ToolUseBlock,
    assistant_message,
    tool_results,
    user_text,
)
from local_coding_agent.skills.catalog import (
    SKILLS_PATH,
    SkillCatalog,
    discover_skills,
)
from local_coding_agent.tools.load_skill import load_skill_tool
from tests.fakes import RecordingTrace, ScriptedLines, ScriptedModel, Step, fake_session
from tests.test_repl_commands import at
from tests.test_skills_catalog import SkillsTestCase

STOP = Done(done_reason="stop", stats={"prompt_eval_count": 7, "eval_count": 2})
REPLY: list[Step] = [TextDelta("はい"), STOP]
REVIEW = "---\ndescription: 読む\n---\n\n対象を読め: $ARGUMENTS\n"


class SkillRepl(SkillsTestCase):
    """スキルの置き場を持つ作業ディレクトリで、偽物の REPL を走らせる。"""

    def run_repl(
        self,
        lines: list[str],
        script: list[list[Step]],
        catalog: SkillCatalog | None = None,
    ) -> None:
        """catalog が無ければ、起動のときと同じく、走らせる前にスキルを探す。"""
        found = discover_skills(self.cwd) if catalog is None else catalog
        self.model = ScriptedModel(script)
        self.trace = RecordingTrace()
        output = io.StringIO()
        tools = (load_skill_tool(found),)
        reader = ScriptedLines(*lines)
        session = fake_session(
            self.model, tools, reader, self.trace, output, self.cwd, skills=found
        )
        repl.run(session)
        self.text = output.getvalue()

    def commands(self) -> list[Mapping[str, object]]:
        return self.trace.of_type("command")


class UserCallsSkillTest(SkillRepl):
    def test_sends_content_with_skill_metadata(self) -> None:
        self.write("review/SKILL.md", REVIEW)
        self.run_repl(["/review a.py"], [REPLY])
        expected = user_text("対象を読め: a.py", at(0), skill="/review a.py")
        self.assertEqual(self.model.sent, [(expected,)])
        self.assertIn(
            "[スキル] /review → .local-coding-agent/skills/review/SKILL.md"
            "（1 行を依頼として送る）\n",
            self.text,
        )
        record = self.commands()[0]
        self.assertEqual(
            {key: record[key] for key in ("kind", "turn", "source", "text")},
            {
                "kind": "skill",
                "turn": 1,
                "source": str(SKILLS_PATH / "review" / "SKILL.md"),
                "text": "対象を読め: a.py",
            },
        )

    def test_sent_content_lists_attached_files(self) -> None:
        self.write("review/SKILL.md", REVIEW)
        self.write("review/checklist.md", "観点")
        self.run_repl(["/review"], [REPLY])
        (sent,) = self.model.sent
        self.assertIn("- .local-coding-agent/skills/review/checklist.md", str(sent))
        self.assertIn("（5 行を依頼として送る）", self.text)

    def test_custom_command_and_builtin_win(self) -> None:
        self.write("review/SKILL.md", REVIEW)
        self.write("clear/SKILL.md", "消さずに送る")
        (self.cwd / COMMANDS_PATH).mkdir(parents=True)
        (self.cwd / COMMANDS_PATH / "review.md").write_text("自作", encoding="utf-8")
        self.run_repl(["/review", "/clear"], [REPLY])
        sent = user_text("自作", at(0), command="/review")
        self.assertEqual(self.model.sent, [(sent,)])
        self.assertIn(CLEARED, self.text)
        self.assertEqual([r["kind"] for r in self.commands()], ["custom", "builtin"])

    def test_skill_that_became_empty_after_start_is_not_sent(self) -> None:
        self.write("review/SKILL.md", REVIEW)
        catalog = discover_skills(self.cwd)
        self.write("review/SKILL.md", "---\ndescription: 読む\n---\n")
        self.run_repl(["/review", "a"], [REPLY], catalog)
        self.assertEqual(self.model.sent, [(user_text("a", at(0)),)])
        self.assertIn("誤り: /review のスキルを使えない: 本文が空\n", self.text)
        record = self.commands()[0]
        self.assertEqual(
            (record["kind"], record["turn"], record["text"]), ("skill", None, None)
        )
        self.assertEqual(self.trace.of_type("request")[0]["turn"], 1)

    def test_skill_added_after_start_is_unknown(self) -> None:
        catalog = discover_skills(self.cwd)
        self.write("late/SKILL.md", "遅れて足した")
        self.run_repl(["/late"], [], catalog)
        self.assertEqual(self.model.sent, [])
        self.assertIn("誤り: 知らないコマンド: /late", self.text)

    def test_help_lists_skills(self) -> None:
        self.write("review/SKILL.md", REVIEW)
        self.write("Foo/SKILL.md", "本文")
        self.run_repl(["/help"], [])
        self.assertIn(
            "スキル（.local-coding-agent/skills/。/<名前> で呼ぶか、モデルが読み込む）:\n"
            "  /review   読む\n"
            "  Foo/      （名前に使えない字があるので使えない）",
            self.text,
        )


class ModelLoadsSkillTest(SkillRepl):
    def test_content_comes_back_as_tool_result_and_stays_in_history(self) -> None:
        self.write("review/SKILL.md", REVIEW)
        given = {"name": "review", "arguments": "a.py"}
        call = ToolCall("c1", "load_skill", given)
        self.run_repl(["レビューして", "次"], [[call, STOP], REPLY, REPLY])
        loaded: tuple[Message, ...] = (
            user_text("レビューして", at(0)),
            assistant_message("", [ToolUseBlock("c1", "load_skill", given)]),
            tool_results([ToolResultBlock("c1", "対象を読め: a.py")]),
        )
        self.assertEqual(self.model.sent[1], loaded)
        # 後の回でも、読み込んだ中身は履歴に残って送られる
        self.assertEqual(self.model.sent[2][:3], loaded)
        (tool,) = self.trace.of_type("tool")
        self.assertEqual(tool["result"], "対象を読め: a.py")
        self.assertIn(
            '[道具] load_skill {"name": "review", "arguments": "a.py"}\n', self.text
        )
        # 読む道具をモードで通すので、許可の行は出ない（F-06 と同じ）
        self.assertNotIn("[許可]", self.text)


if __name__ == "__main__":
    unittest.main()
