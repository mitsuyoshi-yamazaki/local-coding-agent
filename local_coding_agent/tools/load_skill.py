"""道具 load_skill: スキル（作業ごとの手順書）を読み込み、中身を返す。

使えるスキルが1つ以上あるときだけ、モデルに渡す。どのスキルがあるかは、system prompt の
「# スキル」の節にある（skills/catalog.py）。名前は、定義の enum で、使えるスキルに限る。
何も変えないので、種類は読む道具である。照らす文字列を持たないので、型を持つ規則には合わない。
"""

from pathlib import Path
from typing import cast

from local_coding_agent.model.chat import ToolDefinition
from local_coding_agent.skills.catalog import SkillCatalog, SkillError, find_skill
from local_coding_agent.skills.content import skill_text
from local_coding_agent.tools.tool import Tool, ToolError, ToolInput

TOOL_NAME = "load_skill"


def definition(catalog: SkillCatalog) -> ToolDefinition:
    """道具の定義。name の enum に、使えるスキルの名前を並べる。"""
    return ToolDefinition(
        name=TOOL_NAME,
        description=(
            "スキル（作業ごとの手順書）を読み込み、中身を返す。"
            "使えるスキルは、指示の「# スキル」の節にある。"
            "依頼がスキルの説明に合えば、作業を始める前に呼ぶ。"
        ),
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "enum": [skill.name for skill in catalog.skills],
                    "description": "スキルの名前",
                },
                "arguments": {
                    "type": "string",
                    "description": (
                        "スキルに渡す引数（本文の $ARGUMENTS に入る）。"
                        "スキルの説明に引数の案内があれば渡す"
                    ),
                },
            },
            "required": ["name"],
        },
    )


def load_skill_tool(catalog: SkillCatalog) -> Tool:
    """一覧のスキルを読み込む道具。"""

    def run(arguments: ToolInput, cwd: Path) -> str:
        # 入力は、実行の前に定義と照らしてある（name は enum のどれか）
        name = cast(str, arguments["name"])
        given = cast(str, arguments.get("arguments", "")).strip()
        skill = find_skill(catalog, name)
        if skill is None:
            raise ToolError(f"知らないスキル: {name}")
        try:
            return skill_text(cwd, skill, given)
        except SkillError as error:
            raise ToolError(f"スキル {name} を使えない: {error}") from None

    return Tool(definition=definition(catalog), kind="read", run=run)
