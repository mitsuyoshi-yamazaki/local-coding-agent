import unittest

from local_coding_agent.permissions.policy import MODES, Permissions, decide
from local_coding_agent.permissions.rules import parse_rule
from local_coding_agent.skills.catalog import SkillCatalog
from local_coding_agent.tools.input_check import input_problem
from local_coding_agent.tools.load_skill import TOOL_NAME, load_skill_tool
from local_coding_agent.tools.tool import ToolError
from tests.test_skills_catalog import SkillsTestCase, skill

CATALOG = SkillCatalog((skill("release", "版を上げる"), skill("review", "読む")))


class DefinitionTest(unittest.TestCase):
    def test_name_is_limited_to_usable_skills(self) -> None:
        tool = load_skill_tool(CATALOG)
        self.assertEqual(tool.name, TOOL_NAME)
        schema = tool.definition.input_schema
        self.assertEqual(schema["required"], ["name"])
        self.assertEqual(
            input_problem(schema, {"name": "x"}),
            'name は次のどれか: release, review（受けた値: "x"）',
        )
        self.assertIsNone(input_problem(schema, {"name": "review", "arguments": "a"}))

    def test_reading_tool_without_target(self) -> None:
        tool = load_skill_tool(CATALOG)
        self.assertEqual(tool.kind, "read")
        self.assertIsNone(tool.target)
        self.assertIsNone(tool.preview)


class PermissionTest(SkillsTestCase):
    def test_mode_lets_it_through_and_name_rule_matches(self) -> None:
        tool = load_skill_tool(CATALOG)
        call = {"name": "review"}
        for mode in MODES:
            with self.subTest(mode=mode):
                decision = decide(Permissions(mode=mode), tool, call, self.cwd)
                self.assertEqual(decision.verdict, "allow")
        rule = parse_rule(TOOL_NAME, (tool,), self.cwd, self.cwd)
        denied = decide(Permissions(deny=(rule,)), tool, call, self.cwd)
        self.assertEqual(denied.verdict, "deny")
        pattern = parse_rule(f"{TOOL_NAME}(review)", (tool,), self.cwd, self.cwd)
        passed = decide(Permissions(deny=(pattern,)), tool, call, self.cwd)
        self.assertEqual(passed.verdict, "allow")


class RunTest(SkillsTestCase):
    def test_returns_the_content(self) -> None:
        self.write("review/SKILL.md", "---\ndescription: 読む\n---\n対象: $ARGUMENTS\n")
        tool = load_skill_tool(CATALOG)
        result = tool.run({"name": "review", "arguments": " a.py "}, self.cwd)
        self.assertEqual(result, "対象: a.py")
        self.assertEqual(tool.run({"name": "review"}, self.cwd), "対象:")

    def test_unusable_skill_is_an_error(self) -> None:
        self.write("review/SKILL.md", "---\ndescription: 読む\n---\n")
        tool = load_skill_tool(CATALOG)
        with self.assertRaisesRegex(ToolError, "^スキル review を使えない: 本文が空$"):
            tool.run({"name": "review"}, self.cwd)
        with self.assertRaisesRegex(ToolError, "^スキル release を使えない: SKILL.md"):
            tool.run({"name": "release"}, self.cwd)

    def test_name_outside_catalog(self) -> None:
        tool = load_skill_tool(CATALOG)
        with self.assertRaisesRegex(ToolError, "知らないスキル: x"):
            tool.run({"name": "x"}, self.cwd)


if __name__ == "__main__":
    unittest.main()
