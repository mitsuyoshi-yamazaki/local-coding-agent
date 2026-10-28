import tempfile
import unittest
from pathlib import Path

from local_coding_agent.permissions.rules import (
    Rule,
    RuleError,
    inside,
    matches,
    parse_rule,
    resolve_pattern,
    resolve_target,
)
from local_coding_agent.tools.default import DEFAULT_TOOLS

CWD = Path("/work/project")
HOME = Path("/home/me")


def parse(text: str) -> Rule:
    return parse_rule(text, DEFAULT_TOOLS, CWD, HOME)


class ParseRuleTest(unittest.TestCase):
    def test_name_only(self) -> None:
        self.assertEqual(parse("run_command"), Rule("run_command", None, "run_command"))

    def test_command_pattern_is_kept_as_written(self) -> None:
        rule = parse("run_command(rm *)")
        self.assertEqual((rule.tool, rule.pattern), ("run_command", "rm *"))
        self.assertEqual(str(rule), "run_command(rm *)")

    def test_command_pattern_whitespace_is_tidied(self) -> None:
        rule = parse("run_command(git   push\t*)")
        self.assertEqual(rule.pattern, "git push *")
        self.assertEqual(str(rule), "run_command(git   push\t*)")

    def test_pattern_may_contain_parentheses(self) -> None:
        self.assertEqual(parse("run_command(echo (a))").pattern, "echo (a)")

    def test_file_pattern_is_made_absolute(self) -> None:
        rule = parse("read_file(secret.txt)")
        self.assertEqual(rule.pattern, "/work/project/secret.txt")
        self.assertEqual(str(rule), "read_file(secret.txt)")

    def test_errors(self) -> None:
        for text, message in (
            ("run_command()", "型が空である"),
            ("Bash(rm *)", "知らない道具の名前: Bash（使える道具: read_file,"),
            ("run_command(rm *", "規則の形が違う"),
            ("run command", "規則の形が違う"),
            ("", "規則の形が違う"),
        ):
            with self.subTest(text=text), self.assertRaisesRegex(RuleError, message):
                parse(text)


class MatchesTest(unittest.TestCase):
    def test_star_matches_anything_including_slash_and_space(self) -> None:
        self.assertTrue(matches("git *", "git log --oneline -3"))
        self.assertTrue(matches("/work/*.py", "/work/src/deep/a.py"))
        self.assertTrue(matches("a*b", "ab"))

    def test_other_characters_match_only_themselves(self) -> None:
        self.assertTrue(matches("python3 -m unittest", "python3 -m unittest"))
        self.assertFalse(matches("python3 -m unittest", "python3 -m unittest -v"))
        self.assertFalse(matches("a.c", "abc"))
        self.assertFalse(matches("[ab]", "a"))

    def test_trailing_space_star_also_matches_without_arguments(self) -> None:
        self.assertTrue(matches("ls *", "ls"))
        self.assertTrue(matches("ls *", "ls -la"))
        self.assertFalse(matches("ls *", "lsof"))
        self.assertTrue(matches("ls*", "lsof"))

    def test_trailing_slash_star_also_matches_the_directory(self) -> None:
        self.assertTrue(matches("/work/src/*", "/work/src"))
        self.assertTrue(matches("/work/src/*", "/work/src/a/b.py"))
        self.assertFalse(matches("/work/src/*", "/work/srcx"))

    def test_whole_text_must_match(self) -> None:
        self.assertFalse(matches("rm *", "echo; rm x"))


class ResolveTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        # macOS の一時ディレクトリはシンボリックリンクを通るので、解いたものを基点にする
        self.root = Path(directory.name).resolve()
        self.cwd = self.root / "project"
        self.cwd.mkdir()

    def test_target_relative_absolute_and_dot_dot(self) -> None:
        self.assertEqual(resolve_target("a.txt", self.cwd), self.cwd / "a.txt")
        self.assertEqual(
            resolve_target(f"{self.root}/a/../x", self.cwd), self.root / "x"
        )
        self.assertEqual(resolve_target("../out.txt", self.cwd), self.root / "out.txt")

    def test_target_symlink_pointing_outside_is_outside(self) -> None:
        (self.root / "secret.txt").write_text("x", encoding="utf-8")
        (self.cwd / "link.txt").symlink_to(self.root / "secret.txt")
        target = resolve_target("link.txt", self.cwd)
        self.assertEqual(target, self.root / "secret.txt")
        self.assertFalse(inside(target, self.cwd))

    def test_target_with_nul_does_not_raise(self) -> None:
        self.assertEqual(resolve_target("a\0b", self.cwd), self.cwd / "a\0b")

    def test_inside(self) -> None:
        self.assertTrue(inside(self.cwd, self.cwd))
        self.assertTrue(inside(self.cwd / "src" / "a.py", self.cwd))
        self.assertFalse(inside(self.root / "projectx", self.cwd))
        self.assertFalse(inside(self.root, self.cwd))

    def test_pattern_anchors(self) -> None:
        home = self.root / "home"
        self.assertEqual(resolve_pattern("src/*", self.cwd, home), f"{self.cwd}/src/*")
        self.assertEqual(resolve_pattern("./*", self.cwd, home), f"{self.cwd}/*")
        self.assertEqual(resolve_pattern("~/.ssh/*", self.cwd, home), f"{home}/.ssh/*")
        self.assertEqual(resolve_pattern("/*.env", self.cwd, home), "/*.env")
        self.assertEqual(resolve_pattern("../*", self.cwd, home), f"{self.root}/*")

    def test_pattern_directories_before_star_are_resolved(self) -> None:
        (self.root / "real").mkdir()
        (self.root / "alias").symlink_to(self.root / "real")
        self.assertEqual(
            resolve_pattern(f"{self.root}/alias/*.log", self.cwd, self.root),
            f"{self.root}/real/*.log",
        )

    def test_dot_dot_after_symlink_follows_the_link(self) -> None:
        # 道具のパスと同じく、シンボリックリンクを解いてから .. を辿る
        (self.root / "deep" / "inner").mkdir(parents=True)
        (self.cwd / "link").symlink_to(self.root / "deep" / "inner")
        self.assertEqual(
            resolve_pattern("link/../x.txt", self.cwd, self.root),
            f"{self.root}/deep/x.txt",
        )
        self.assertEqual(
            str(resolve_target("link/../x.txt", self.cwd)), f"{self.root}/deep/x.txt"
        )

    def test_pattern_without_star_is_resolved_whole(self) -> None:
        (self.root / "secret.txt").write_text("x", encoding="utf-8")
        (self.cwd / "link.txt").symlink_to(self.root / "secret.txt")
        self.assertEqual(
            resolve_pattern("link.txt", self.cwd, self.root),
            f"{self.root}/secret.txt",
        )


if __name__ == "__main__":
    unittest.main()
