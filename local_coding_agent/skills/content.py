"""スキルの中身: モデルが load_skill で読み込むときと、利用者が /<名前> で呼ぶときに渡す文。

どちらの道でも同じ文を作る。SKILL.md を読むたびに読み直し、前付けを除いた本文に引数を入れる
（自作のコマンドと同じ）。スキルのディレクトリに付いているファイルは、中身を読まず、パスの
一覧だけを添える。モデルは、要るときに read_file で読む。
"""

from collections.abc import Sequence
from pathlib import Path

from local_coding_agent.commands.custom import expand
from local_coding_agent.skills.catalog import Skill, SkillError, read_skill

# 付いているファイルを並べる数の上限
MAX_FILES = 50


def skill_text(cwd: Path, skill: Skill, arguments: str) -> str:
    """スキルの中身。読めない・本文が空・引数を入れた中身が空なら SkillError。

    付いているファイルがあれば、本文の後に、スキルのディレクトリとファイルの一覧を添える。
    """
    command = read_skill(cwd, skill.name, skill.path)
    if not command.body.strip():
        raise SkillError("本文が空")
    body = expand(command, arguments)
    if not body:
        raise SkillError("引数を入れた中身が空")
    files = attached_files(cwd, skill)
    if not files:
        return body
    return f"{body}\n\n{_files_text(skill, files)}"


def attached_files(cwd: Path, skill: Skill) -> tuple[Path, ...]:
    """スキルのディレクトリの中の、SKILL.md のほかのファイル（下のディレクトリも含む）。

    作業ディレクトリからのパスで、名前の順に並べる。. で始まるファイルとディレクトリ
    （.DS_Store など）は除く。ディレクトリの中を見られなければ空。
    """
    directory = cwd / skill.path.parent
    try:
        found = sorted(path for path in directory.rglob("*") if path.is_file())
    except OSError:
        return ()
    skill_file = cwd / skill.path
    return tuple(
        path.relative_to(cwd)
        for path in found
        if path != skill_file and not _hidden(path.relative_to(directory))
    )


def _hidden(relative: Path) -> bool:
    return any(part.startswith(".") for part in relative.parts)


def _files_text(skill: Skill, files: Sequence[Path]) -> str:
    shown = files[:MAX_FILES]
    rest = len(files) - len(shown)
    lines = (
        f"スキルのディレクトリ: {skill.path.parent}/（本文の中の相対パスは、ここからのもの）",
        "付いているファイル（要るときに read_file で読む）:",
        *(f"- {path}" for path in shown),
        *((f"（ほかに {rest} 個。list_directory で見る）",) if rest else ()),
    )
    return "\n".join(lines)
