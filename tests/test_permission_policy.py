import tempfile
import unittest
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from local_coding_agent.permissions.policy import (
    DENIED_NOTE,
    Decision,
    Mode,
    Permissions,
    decide,
    denial,
)
from local_coding_agent.permissions.rules import Rule, parse_rule
from local_coding_agent.tools import edit_file, list_directory, read_file, run_command
from local_coding_agent.tools.default import DEFAULT_TOOLS
from local_coding_agent.tools.tool import Tool, ToolInput
from tests.fakes import fake_tool


def nothing(arguments: ToolInput, cwd: Path) -> str:
    return ""


class PolicyTestCase(unittest.TestCase):
    """一時ディレクトリの中の project を作業ディレクトリにする。"""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.cwd = self.root / "project"
        self.cwd.mkdir()

    def permissions(
        self,
        mode: Mode = "allow-all",
        allow: Sequence[str] = (),
        ask: Sequence[str] = (),
        deny: Sequence[str] = (),
    ) -> Permissions:
        def rules(texts: Sequence[str]) -> tuple[Rule, ...]:
            return tuple(
                parse_rule(t, DEFAULT_TOOLS, self.cwd, self.root) for t in texts
            )

        return Permissions(mode, rules(allow), rules(ask), rules(deny))

    def decide(
        self, permissions: Permissions, tool: Tool, arguments: ToolInput
    ) -> Decision:
        return decide(permissions, tool, arguments, self.cwd)

    def command(self, permissions: Permissions, command: str) -> Decision:
        return self.decide(permissions, run_command.TOOL, {"command": command})


class ModeTest(PolicyTestCase):
    def test_table(self) -> None:
        outside = str(self.root / "other.txt")
        edit = {"old_string": "a", "new_string": "b"}
        calls = (
            ("read", read_file.TOOL, {"path": "a.txt"}),
            ("read-out", read_file.TOOL, {"path": outside}),
            ("edit", edit_file.TOOL, {"path": "a.txt", **edit}),
            ("edit-out", edit_file.TOOL, {"path": outside, **edit}),
            ("command", run_command.TOOL, {"command": "ls"}),
        )
        expected: dict[Mode, tuple[str, ...]] = {
            "ask": ("allow", "ask", "ask", "ask", "ask"),
            "accept-edits": ("allow", "ask", "allow", "ask", "ask"),
            "allow-all": ("allow", "allow", "allow", "allow", "allow"),
        }
        for mode, verdicts in expected.items():
            for (name, tool, arguments), verdict in zip(calls, verdicts):
                with self.subTest(mode=mode, call=name):
                    decision = self.decide(self.permissions(mode), tool, arguments)
                    self.assertEqual(decision.verdict, verdict)
                    self.assertIsNone(decision.rule)

    def test_reasons(self) -> None:
        ask = self.permissions("ask")
        outside = {"path": str(self.root)}
        self.assertEqual(
            self.decide(ask, list_directory.TOOL, outside),
            Decision("ask", "モード ask・作業ディレクトリの外"),
        )
        self.assertEqual(self.command(ask, "ls"), Decision("ask", "モード ask"))

    def test_list_directory_without_path_is_inside(self) -> None:
        decision = self.decide(self.permissions("ask"), list_directory.TOOL, {})
        self.assertEqual(decision.verdict, "allow")

    def test_dot_dot_leaves_the_working_directory(self) -> None:
        arguments = {"path": "../secret.txt"}
        decision = self.decide(self.permissions("ask"), read_file.TOOL, arguments)
        self.assertEqual(decision.reason, "モード ask・作業ディレクトリの外")

    def test_tool_without_target_counts_as_inside(self) -> None:
        tool = fake_tool("write", nothing, kind="edit")
        decision = self.decide(self.permissions("accept-edits"), tool, {})
        self.assertEqual(decision.verdict, "allow")


class RuleOrderTest(PolicyTestCase):
    def test_deny_beats_ask_and_allow(self) -> None:
        permissions = self.permissions(
            "ask",
            allow=["run_command(git status)"],
            ask=["run_command(git *)"],
            deny=["run_command(git *)"],
        )
        self.assertEqual(
            self.command(permissions, "git status"),
            Decision("deny", "規則 deny: run_command(git *)", "run_command(git *)"),
        )

    def test_ask_beats_more_specific_allow(self) -> None:
        permissions = self.permissions(
            "allow-all", allow=["run_command(git status)"], ask=["run_command(git *)"]
        )
        self.assertEqual(self.command(permissions, "git status").verdict, "ask")

    def test_allow_rule(self) -> None:
        permissions = self.permissions("ask", allow=["run_command(python3 -m *)"])
        self.assertEqual(
            self.command(permissions, "python3 -m unittest"),
            Decision(
                "allow",
                "規則 allow: run_command(python3 -m *)",
                "run_command(python3 -m *)",
            ),
        )

    def test_allow_all_still_obeys_deny_and_ask(self) -> None:
        permissions = self.permissions(
            "allow-all", ask=["run_command(git push *)"], deny=["run_command(rm *)"]
        )
        self.assertEqual(self.command(permissions, "rm -rf build").verdict, "deny")
        self.assertEqual(self.command(permissions, "git push origin").verdict, "ask")
        self.assertEqual(self.command(permissions, "ls").verdict, "allow")

    def test_rules_of_other_tools_do_not_match(self) -> None:
        permissions = self.permissions("ask", deny=["read_file"])
        self.assertEqual(self.command(permissions, "cat a.txt").verdict, "ask")

    def test_name_only_rule_matches_every_call(self) -> None:
        permissions = self.permissions("ask", allow=["run_command"])
        decision = self.command(permissions, "echo $(date) && rm x")
        self.assertEqual(decision.verdict, "allow")

    def test_decision_carries_the_reason_of_the_rule(self) -> None:
        (rule,) = self.permissions(deny=["run_command(rm *)"]).deny
        permissions = Permissions(deny=(replace(rule, reason="ファイルを消さない"),))
        self.assertEqual(
            self.command(permissions, "rm x"),
            Decision(
                "deny",
                "規則 deny: run_command(rm *)",
                "run_command(rm *)",
                "ファイルを消さない",
            ),
        )


class DenialTest(unittest.TestCase):
    def test_reason_and_star_are_explained(self) -> None:
        decision = Decision(
            "deny", "規則 deny: run_command(rm *)", "run_command(rm *)", "消さない"
        )
        self.assertEqual(
            denial(decision),
            "規則で拒んだ: run_command(rm *)（規則の * は任意の文字列を表す）。"
            f"理由: 消さない。{DENIED_NOTE}",
        )

    def test_without_reason(self) -> None:
        decision = Decision(
            "deny", "規則 deny: read_file(secret.txt)", "read_file(secret.txt)"
        )
        self.assertEqual(
            denial(decision), f"規則で拒んだ: read_file(secret.txt)。{DENIED_NOTE}"
        )


class FileRuleTest(PolicyTestCase):
    def test_relative_pattern(self) -> None:
        permissions = self.permissions("allow-all", deny=["read_file(secret.txt)"])
        for path in ("secret.txt", "./secret.txt", str(self.cwd / "secret.txt")):
            with self.subTest(path=path):
                decision = self.decide(permissions, read_file.TOOL, {"path": path})
                self.assertEqual(decision.verdict, "deny")
        decision = self.decide(permissions, read_file.TOOL, {"path": "other.txt"})
        self.assertEqual(decision.verdict, "allow")

    def test_symlink_to_denied_file_is_denied(self) -> None:
        (self.cwd / "secret.txt").write_text("x", encoding="utf-8")
        (self.cwd / "alias.txt").symlink_to(self.cwd / "secret.txt")
        permissions = self.permissions("allow-all", deny=["read_file(secret.txt)"])
        decision = self.decide(permissions, read_file.TOOL, {"path": "alias.txt"})
        self.assertEqual(decision.verdict, "deny")

    def test_allow_outside_by_rule(self) -> None:
        permissions = self.permissions("ask", allow=[f"read_file({self.root}/docs/*)"])
        path = str(self.root / "docs" / "a.md")
        decision = self.decide(permissions, read_file.TOOL, {"path": path})
        self.assertEqual(decision.verdict, "allow")


class CommandRuleTest(PolicyTestCase):
    def test_deny_matches_any_part(self) -> None:
        permissions = self.permissions("allow-all", deny=["run_command(rm *)"])
        for command in ("cd build && rm old.log", "ls; rm x", "echo a | rm -i x"):
            with self.subTest(command=command):
                self.assertEqual(self.command(permissions, command).verdict, "deny")

    def test_allow_needs_every_part(self) -> None:
        permissions = self.permissions(
            "ask", allow=["run_command(python3 -m unittest*)", "run_command(tail *)"]
        )
        decision = self.command(permissions, "python3 -m unittest -v 2>&1 | tail -5")
        self.assertEqual(decision.verdict, "allow")
        self.assertEqual(
            decision.rule, "run_command(python3 -m unittest*)・run_command(tail *)"
        )
        decision = self.command(permissions, "python3 -m unittest; rm -rf build")
        self.assertEqual(decision, Decision("ask", "モード ask"))

    def test_same_rule_for_several_parts_is_named_once(self) -> None:
        permissions = self.permissions("ask", allow=["run_command(echo *)"])
        self.assertEqual(
            self.command(permissions, "echo a && echo b").rule, "run_command(echo *)"
        )

    def test_substitution_is_not_allowed_by_patterns(self) -> None:
        permissions = self.permissions("ask", allow=["run_command(echo *)"])
        for command in ("echo $(rm x)", "echo `rm x`"):
            with self.subTest(command=command):
                self.assertEqual(self.command(permissions, command).verdict, "ask")

    def test_deny_does_not_reach_inside_substitution(self) -> None:
        # 照合の限界: 置換の中の rm は、分けた部分の頭に来ないので合わない
        permissions = self.permissions("allow-all", deny=["run_command(rm *)"])
        self.assertEqual(self.command(permissions, "echo $(rm x)").verdict, "allow")


if __name__ == "__main__":
    unittest.main()
