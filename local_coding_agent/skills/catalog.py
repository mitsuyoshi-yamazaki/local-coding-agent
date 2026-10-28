"""スキルの一覧: 起動のときに、作業ディレクトリの .local-coding-agent/skills/<名前>/SKILL.md を探す。

スキルは作業ごとの手順書である。SKILL.md の形は自作のコマンドのファイル（commands/custom.py）と
同じなので、同じ読み手で読む。モデルへの指示には、名前と説明だけを入れる（「# スキル」の節）。
本文は、モデルが load_skill の道具で読み込むときと、利用者が /<名前> で呼ぶときに読む
（skills/content.py）。
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from local_coding_agent.commands.custom import (
    COMMANDS_PATH,
    CustomCommand,
    Listed,
    error_reason,
    parse_custom,
)
from local_coding_agent.commands.parse import NAME

SKILLS_PATH = Path(".local-coding-agent") / "skills"
SKILL_FILE = "SKILL.md"
# 「# スキル」の節の、一覧の前に置く文
GUIDE = (
    "スキルは、作業ごとの手順書である。下に、作業ディレクトリに置かれたスキルの名前と説明を"
    "並べる。依頼がスキルの説明に合えば、作業を始める前に load_skill の道具でそのスキルを"
    "読み込み、本文の手順に従う。合うスキルが無ければ、読み込まない。"
)


class SkillError(Exception):
    """スキルの SKILL.md を読めない・中身が空。"""


@dataclass(frozen=True)
class Skill:
    """使えるスキル1つ。"""

    # ディレクトリの名前
    name: str
    # SKILL.md の、作業ディレクトリからのパス
    path: Path
    # 前付けの description。無ければ本文の最初の空でない行
    description: str


@dataclass(frozen=True)
class Unusable:
    """使えないスキル1つ。"""

    # ディレクトリの名前に / を付けたもの。置き場の中を見られなければ、置き場のパス
    entry: str
    problem: str


@dataclass(frozen=True)
class SkillCatalog:
    """起動のときに探したスキル。どちらも名前の順。"""

    skills: tuple[Skill, ...] = ()
    unusable: tuple[Unusable, ...] = ()


def discover_skills(cwd: Path) -> SkillCatalog:
    """置き場の下の一段のディレクトリを、使えるものと使えないものに分ける。置き場が無ければ空。"""
    directory = cwd / SKILLS_PATH
    if not directory.is_dir():
        return SkillCatalog()
    try:
        entries = sorted(path.name for path in directory.iterdir() if path.is_dir())
    except OSError as error:
        problem = f"読めない: {error_reason(error)}"
        return SkillCatalog(unusable=(Unusable(f"{SKILLS_PATH}/", problem),))
    found = tuple(_examine(cwd, name) for name in entries)
    return SkillCatalog(
        tuple(item for item in found if isinstance(item, Skill)),
        tuple(item for item in found if isinstance(item, Unusable)),
    )


def _examine(cwd: Path, name: str) -> Skill | Unusable:
    entry = f"{name}/"
    if not NAME.fullmatch(name):
        return Unusable(entry, "名前に使えない字があるので使えない")
    path = SKILLS_PATH / name / SKILL_FILE
    if not (cwd / path).is_file():
        return Unusable(entry, f"{SKILL_FILE} が無いので使えない")
    try:
        command = read_skill(cwd, name, path)
    except SkillError as error:
        return Unusable(entry, str(error))
    if not command.body.strip():
        return Unusable(entry, "本文が空なので使えない")
    return Skill(name, path, command.description)


def read_skill(cwd: Path, name: str, path: Path) -> CustomCommand:
    """SKILL.md を読み、前付けの説明と本文に分ける。読めなければ SkillError。"""
    try:
        text = (cwd / path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SkillError(f"{SKILL_FILE} を読めない: {error_reason(error)}") from None
    return parse_custom(name, path, text)


def find_skill(catalog: SkillCatalog, name: str) -> Skill | None:
    """使えるスキルを名前で探す。無ければ None。"""
    return next((skill for skill in catalog.skills if skill.name == name), None)


def skills_section(catalog: SkillCatalog) -> str:
    """system prompt の「# スキル」の節。使えるスキルが無ければ空の文字列。"""
    if not catalog.skills:
        return ""
    rows = "\n".join(f"- {skill.name}: {skill.description}" for skill in catalog.skills)
    return f"# スキル\n\n{GUIDE}\n\n{rows}"


def describe_skills(catalog: SkillCatalog) -> str:
    """起動のときに出す1行。"""
    skills, unusable = catalog.skills, catalog.unusable
    names = "・".join(skill.name for skill in skills)
    found = f"{len(skills)}（{names}）" if skills else "無し"
    problems = f"・使えない {len(unusable)}（/help で理由）" if unusable else ""
    return f"スキル: {found}{problems}"


def skills_record(catalog: SkillCatalog) -> dict[str, object]:
    """走行の記録に、起動のときに書く1件。"""
    return {
        "type": "skills",
        "skills": [
            {
                "name": skill.name,
                "source": str(skill.path),
                "description": skill.description,
            }
            for skill in catalog.skills
        ],
        "unusable": [
            {"entry": item.entry, "problem": item.problem} for item in catalog.unusable
        ],
    }


def list_skills(
    catalog: SkillCatalog, cwd: Path, builtin_names: Sequence[str]
) -> tuple[Listed, ...]:
    """/help の一覧。使えるスキル、使えないスキルの順に並べる。

    組み込みか自作のコマンドと同じ名前のスキルは、/<名前> では呼べない（先に探すほうが勝つ）。
    モデルは load_skill で読み込める。自作のコマンドと同じ名前かは、呼んだときに見る。
    """
    usable = tuple(_listed(skill, cwd, builtin_names) for skill in catalog.skills)
    broken = tuple(Listed(item.entry, "", item.problem) for item in catalog.unusable)
    return (*usable, *broken)


def _listed(skill: Skill, cwd: Path, builtin_names: Sequence[str]) -> Listed:
    label = f"/{skill.name}"
    if skill.name in builtin_names:
        taken = "組み込み"
    elif (cwd / COMMANDS_PATH / f"{skill.name}.md").is_file():
        taken = "自作のコマンド"
    else:
        return Listed(label, skill.description)
    problem = f"{taken}と同じ名前なので {label} では呼べない。モデルは読み込める"
    return Listed(label, skill.description, problem)
