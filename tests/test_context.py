import tempfile
import unittest
from pathlib import Path

from local_coding_agent.context.environment import (
    Environment,
    environment_section,
    in_git_repository,
    os_description,
)
from local_coding_agent.context.system_prompt import (
    DEFAULT_INSTRUCTIONS,
    build_system_prompt,
    read_instructions,
)
from local_coding_agent.loop.turn import CANCELLED_NOTE
from local_coding_agent.model.ollama_messages import ERROR_PREFIX
from local_coding_agent.tools.default import DEFAULT_TOOLS


class EnvironmentSectionTest(unittest.TestCase):
    def test_lists_environment(self) -> None:
        environment = Environment(
            working_directory=Path("/work/project"),
            in_git_repository=True,
            os="macOS 15.6（Darwin 24.6.0）",
        )
        self.assertEqual(
            environment_section(environment),
            "# 環境\n"
            "\n"
            "- 作業ディレクトリ: /work/project\n"
            "- 作業ディレクトリは git のリポジトリの中か: はい\n"
            "- OS: macOS 15.6（Darwin 24.6.0）",
        )

    def test_outside_git_repository(self) -> None:
        environment = Environment(Path("/work"), False, "Linux 6.8.0")
        self.assertIn(
            "git のリポジトリの中か: いいえ", environment_section(environment)
        )


class InGitRepositoryTest(unittest.TestCase):
    def test_git_directory_in_parent(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / ".git").mkdir()
            inner = Path(root) / "src" / "pkg"
            inner.mkdir(parents=True)
            self.assertTrue(in_git_repository(inner))

    def test_git_file_of_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / ".git").write_text("gitdir: /elsewhere\n")
            self.assertTrue(in_git_repository(Path(root)))

    def test_filesystem_root_is_outside(self) -> None:
        self.assertFalse(in_git_repository(Path("/")))


class OsDescriptionTest(unittest.TestCase):
    def test_macos_has_product_version(self) -> None:
        self.assertEqual(
            os_description("Darwin", "24.6.0", "15.6"), "macOS 15.6（Darwin 24.6.0）"
        )

    def test_other_os(self) -> None:
        self.assertEqual(os_description("Linux", "6.8.0", ""), "Linux 6.8.0")


class SystemPromptTest(unittest.TestCase):
    def test_joins_instructions_and_environment(self) -> None:
        self.assertEqual(
            build_system_prompt("指示。\n", "# 環境\n\n- OS: x"),
            "指示。\n\n# 環境\n\n- OS: x",
        )

    def test_empty_instructions_leave_environment_only(self) -> None:
        self.assertEqual(build_system_prompt("\n", "# 環境"), "# 環境")

    def test_default_instructions_without_file(self) -> None:
        self.assertEqual(read_instructions(None), DEFAULT_INSTRUCTIONS)

    def test_reads_instructions_file(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "long.md"
            path.write_text("長い指示", encoding="utf-8")
            self.assertEqual(read_instructions(path), "長い指示")

    def test_default_instructions_explain_what_harness_adds(self) -> None:
        self.assertIn("# 環境", DEFAULT_INSTRUCTIONS)
        self.assertIn("<metadata>", DEFAULT_INSTRUCTIONS)
        # 誤りの結果の印（model/ollama_messages.py の ERROR_PREFIX）
        self.assertIn(f"「{ERROR_PREFIX}」で始まる", DEFAULT_INSTRUCTIONS)
        # 回が途中で止まったことの知らせ（loop/turn.py）
        self.assertIn(f"「{CANCELLED_NOTE}」", DEFAULT_INSTRUCTIONS)

    def test_default_instructions_name_the_default_tools(self) -> None:
        for tool in DEFAULT_TOOLS:
            with self.subTest(tool=tool.name):
                self.assertIn(tool.name, DEFAULT_INSTRUCTIONS)


if __name__ == "__main__":
    unittest.main()
