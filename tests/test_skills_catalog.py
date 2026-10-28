import tempfile
import unittest
from pathlib import Path
from unittest import mock

from local_coding_agent.commands.custom import COMMANDS_PATH, Listed
from local_coding_agent.skills.catalog import (
    GUIDE,
    SKILLS_PATH,
    Skill,
    SkillCatalog,
    Unusable,
    describe_skills,
    discover_skills,
    find_skill,
    list_skills,
    skills_record,
    skills_section,
)


class SkillsTestCase(unittest.TestCase):
    """作業ディレクトリを一時ディレクトリにする。"""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cwd = Path(directory.name)

    def write(self, relative: str, data: str | bytes) -> None:
        """置き場からのパスに書く。"""
        path = self.cwd / SKILLS_PATH / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8")


def skill(name: str, description: str) -> Skill:
    return Skill(name, SKILLS_PATH / name / "SKILL.md", description)


class DiscoverTest(SkillsTestCase):
    def test_without_directory_is_empty(self) -> None:
        self.assertEqual(discover_skills(self.cwd), SkillCatalog())

    def test_skills_in_name_order_with_description(self) -> None:
        self.write("review/SKILL.md", "---\ndescription: 読む\n---\n\n本文\n")
        self.write("add-conversion/SKILL.md", "\n変換を足す手順\n\n1. 足す\n")
        self.assertEqual(
            discover_skills(self.cwd),
            SkillCatalog(
                (skill("add-conversion", "変換を足す手順"), skill("review", "読む"))
            ),
        )

    def test_files_in_directory_and_deeper_directories_are_not_skills(self) -> None:
        self.write("README.md", "置き場の説明")
        self.write("group/inner/SKILL.md", "下の段")
        catalog = discover_skills(self.cwd)
        self.assertEqual(catalog.skills, ())
        self.assertEqual(
            catalog.unusable, (Unusable("group/", "SKILL.md が無いので使えない"),)
        )

    def test_unusable_reasons(self) -> None:
        self.write("Foo/SKILL.md", "本文")
        self.write("broken/SKILL.md", b"\xff")
        self.write("empty/SKILL.md", "---\ndescription: 空\n---\n\n")
        self.write("notes/memo.md", "メモ")
        self.write("ok/SKILL.md", "本文")
        catalog = discover_skills(self.cwd)
        self.assertEqual(catalog.skills, (skill("ok", "本文"),))
        decode = (
            "'utf-8' codec can't decode byte 0xff in position 0: invalid start byte"
        )
        self.assertEqual(
            [(item.entry, item.problem) for item in catalog.unusable],
            [
                ("Foo/", "名前に使えない字があるので使えない"),
                ("broken/", f"SKILL.md を読めない: {decode}"),
                ("empty/", "本文が空なので使えない"),
                ("notes/", "SKILL.md が無いので使えない"),
            ],
        )

    def test_symlinked_directory_is_followed(self) -> None:
        self.write("real/SKILL.md", "本文")
        (self.cwd / SKILLS_PATH / "linked").symlink_to(self.cwd / SKILLS_PATH / "real")
        names = [item.name for item in discover_skills(self.cwd).skills]
        self.assertEqual(names, ["linked", "real"])

    def test_unreadable_directory(self) -> None:
        (self.cwd / SKILLS_PATH).mkdir(parents=True)
        error = PermissionError(13, "Permission denied", str(self.cwd))
        with mock.patch.object(Path, "iterdir", side_effect=error):
            catalog = discover_skills(self.cwd)
        self.assertEqual(
            catalog,
            SkillCatalog(
                unusable=(
                    Unusable(
                        ".local-coding-agent/skills/", "読めない: Permission denied"
                    ),
                )
            ),
        )

    def test_find_skill(self) -> None:
        catalog = SkillCatalog((skill("a", "x"),))
        self.assertEqual(find_skill(catalog, "a"), skill("a", "x"))
        self.assertIsNone(find_skill(catalog, "b"))


class SectionTest(unittest.TestCase):
    def test_section_lists_names_and_descriptions(self) -> None:
        catalog = SkillCatalog((skill("a", "一つ目"), skill("b", "二つ目")))
        self.assertEqual(
            skills_section(catalog),
            f"# スキル\n\n{GUIDE}\n\n- a: 一つ目\n- b: 二つ目",
        )

    def test_guide_names_the_tool(self) -> None:
        self.assertIn("load_skill", GUIDE)

    def test_no_section_without_usable_skills(self) -> None:
        unusable = SkillCatalog(unusable=(Unusable("Foo/", "x"),))
        self.assertEqual(skills_section(SkillCatalog()), "")
        self.assertEqual(skills_section(unusable), "")


class DescribeTest(unittest.TestCase):
    def test_start_lines(self) -> None:
        two = (skill("a", "x"), skill("b", "y"))
        broken = (Unusable("Foo/", "x"),)
        for catalog, line in (
            (SkillCatalog(), "スキル: 無し"),
            (SkillCatalog(two), "スキル: 2（a・b）"),
            (
                SkillCatalog(two, broken),
                "スキル: 2（a・b）・使えない 1（/help で理由）",
            ),
            (SkillCatalog(unusable=broken), "スキル: 無し・使えない 1（/help で理由）"),
        ):
            with self.subTest(line=line):
                self.assertEqual(describe_skills(catalog), line)

    def test_trace_record(self) -> None:
        catalog = SkillCatalog((skill("a", "説明"),), (Unusable("Foo/", "理由"),))
        self.assertEqual(
            skills_record(catalog),
            {
                "type": "skills",
                "skills": [
                    {
                        "name": "a",
                        "source": ".local-coding-agent/skills/a/SKILL.md",
                        "description": "説明",
                    }
                ],
                "unusable": [{"entry": "Foo/", "problem": "理由"}],
            },
        )


class ListSkillsTest(SkillsTestCase):
    def test_usable_then_unusable_with_names_taken_by_commands(self) -> None:
        (self.cwd / COMMANDS_PATH).mkdir(parents=True)
        (self.cwd / COMMANDS_PATH / "fix.md").write_text("直す", encoding="utf-8")
        catalog = SkillCatalog(
            (skill("clear", "消す"), skill("fix", "直す手順"), skill("review", "読む")),
            (Unusable("Foo/", "名前に使えない字があるので使えない"),),
        )
        self.assertEqual(
            list_skills(catalog, self.cwd, ("help", "clear")),
            (
                Listed(
                    "/clear",
                    "消す",
                    "組み込みと同じ名前なので /clear では呼べない。モデルは読み込める",
                ),
                Listed(
                    "/fix",
                    "直す手順",
                    "自作のコマンドと同じ名前なので /fix では呼べない。モデルは読み込める",
                ),
                Listed("/review", "読む"),
                Listed("Foo/", "", "名前に使えない字があるので使えない"),
            ),
        )


if __name__ == "__main__":
    unittest.main()
