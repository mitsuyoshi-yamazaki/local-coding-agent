import unittest
from pathlib import Path

from local_coding_agent.skills.catalog import SKILLS_PATH, SkillError
from local_coding_agent.skills.content import MAX_FILES, attached_files, skill_text
from tests.test_skills_catalog import SkillsTestCase, skill

REVIEW = skill("review", "読む")


class SkillTextTest(SkillsTestCase):
    def test_body_without_front_matter_and_with_arguments(self) -> None:
        self.write(
            "review/SKILL.md", "---\ndescription: 読む\n---\n\n対象: $ARGUMENTS\n"
        )
        self.assertEqual(skill_text(self.cwd, REVIEW, "a.py"), "対象: a.py")

    def test_arguments_without_placeholder_go_to_the_end(self) -> None:
        self.write("review/SKILL.md", "読め。\n")
        self.assertEqual(
            skill_text(self.cwd, REVIEW, "a.py"), "読め。\n\nARGUMENTS: a.py"
        )
        self.assertEqual(skill_text(self.cwd, REVIEW, ""), "読め。")

    def test_attached_files_follow_the_body(self) -> None:
        self.write("review/SKILL.md", "checklist.md に沿って読め。")
        self.write("review/checklist.md", "観点")
        self.write("review/scripts/count.py", "print(1)")
        self.assertEqual(
            skill_text(self.cwd, REVIEW, ""),
            "checklist.md に沿って読め。\n"
            "\n"
            "スキルのディレクトリ: .local-coding-agent/skills/review/"
            "（本文の中の相対パスは、ここからのもの）\n"
            "付いているファイル（要るときに read_file で読む）:\n"
            "- .local-coding-agent/skills/review/checklist.md\n"
            "- .local-coding-agent/skills/review/scripts/count.py",
        )

    def test_reads_every_time(self) -> None:
        self.write("review/SKILL.md", "一つ目")
        self.assertEqual(skill_text(self.cwd, REVIEW, ""), "一つ目")
        self.write("review/SKILL.md", "二つ目")
        self.assertEqual(skill_text(self.cwd, REVIEW, ""), "二つ目")

    def test_errors(self) -> None:
        for data, message in (
            (b"\xff", "SKILL.md を読めない: 'utf-8' codec"),
            ("---\ndescription: 空\n---\n", "本文が空"),
            ("$ARGUMENTS\n", "引数を入れた中身が空"),
        ):
            with self.subTest(message=message):
                self.write("review/SKILL.md", data)
                with self.assertRaisesRegex(SkillError, message):
                    skill_text(self.cwd, REVIEW, "")

    def test_missing_file(self) -> None:
        with self.assertRaisesRegex(SkillError, "SKILL.md を読めない: No such file"):
            skill_text(self.cwd, REVIEW, "")


class AttachedFilesTest(SkillsTestCase):
    def test_without_other_files(self) -> None:
        self.write("review/SKILL.md", "本文")
        self.assertEqual(attached_files(self.cwd, REVIEW), ())

    def test_files_in_name_order_without_skill_file(self) -> None:
        self.write("review/SKILL.md", "本文")
        self.write("review/b.md", "")
        self.write("review/a/z.md", "")
        directory = SKILLS_PATH / "review"
        self.assertEqual(
            attached_files(self.cwd, REVIEW),
            (directory / "a" / "z.md", directory / "b.md"),
        )

    def test_hidden_files_and_directories_are_left_out(self) -> None:
        self.write("review/SKILL.md", "本文")
        self.write("review/.DS_Store", "")
        self.write("review/.cache/x.md", "")
        self.write("review/checklist.md", "")
        # 置き場の .local-coding-agent は . で始まるが、スキルのディレクトリより上なので見ない
        self.assertEqual(
            attached_files(self.cwd, REVIEW),
            (SKILLS_PATH / "review" / "checklist.md",),
        )

    def test_long_list_is_cut(self) -> None:
        self.write("review/SKILL.md", "本文")
        for index in range(MAX_FILES + 2):
            self.write(f"review/f{index:03}.md", "")
        text = skill_text(self.cwd, REVIEW, "")
        self.assertEqual(text.count("\n- "), MAX_FILES)
        self.assertIn(f"f{MAX_FILES - 1:03}.md\n", text)
        self.assertTrue(text.endswith("\n（ほかに 2 個。list_directory で見る）"))

    def test_other_skills_are_not_attached(self) -> None:
        self.write("review/SKILL.md", "本文")
        self.write("release/SKILL.md", "本文")
        self.assertEqual(attached_files(self.cwd, REVIEW), ())

    def test_paths_are_relative_to_working_directory(self) -> None:
        self.write("review/SKILL.md", "本文")
        self.write("review/x.md", "")
        (path,) = attached_files(self.cwd, REVIEW)
        self.assertFalse(path.is_absolute())
        self.assertTrue((self.cwd / path).is_file())
        self.assertEqual(path, Path(".local-coding-agent/skills/review/x.md"))


if __name__ == "__main__":
    unittest.main()
