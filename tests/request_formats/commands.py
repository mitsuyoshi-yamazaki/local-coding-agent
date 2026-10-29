"""コマンドとスキルの場面: 自作のコマンド・スキル（モデルが読み込む・利用者が呼ぶ）・組み込みのコマンド。"""

from local_coding_agent.__main__ import main
from local_coding_agent.cli.repl import _send_skill, handle_line
from local_coding_agent.commands.builtin import _clear, run_builtin
from local_coding_agent.commands.custom import expand, split_front_matter
from local_coding_agent.context.system_prompt import (
    build_system_prompt,
    read_instructions,
)
from local_coding_agent.model.messages import metadata_text
from local_coding_agent.model.ollama_messages import _tool_message
from local_coding_agent.skills.catalog import skills_section
from local_coding_agent.skills.content import skill_text
from local_coding_agent.tools import load_skill
from tests.request_formats.scenario import Highlight, Scenario, call, calls, reply

SYSTEM = "messages[0].content"
REQUEST = "messages[1].content"
SKILL_FILES = {
    ".local-coding-agent/skills/review/SKILL.md": (
        "---\n"
        "description: コードを読み、観点ごとに問題を挙げる。引数は読むファイル\n"
        "---\n"
        "\n"
        "$ARGUMENTS を読み、checklist.md の観点ごとに、当てはまる所を挙げよ。\n"
    ),
    ".local-coding-agent/skills/review/checklist.md": "- 誤り\n- 名前\n",
}
SKILL_BODY = "convert.py を読み、checklist.md の観点ごとに"

CUSTOM_COMMAND = Scenario(
    title="自作のコマンド",
    summary=(
        "自作のコマンドのファイルを置き、/fix で呼ぶ。ハーネスがファイルの本文に引数を入れ、"
        "依頼の発言として送る。呼んだ行は `<metadata>` の枠に入る。"
    ),
    lines=("/fix test_a.py",),
    script=(reply("テストを走らせる。"),),
    files={
        ".local-coding-agent/commands/fix.md": (
            "---\n"
            "description: テストを走らせ、失敗していれば直す\n"
            "---\n"
            "\n"
            "テストを走らせ、失敗していれば直せ。対象: $ARGUMENTS\n"
        )
    },
    highlights=(
        Highlight(
            "呼んだコマンドの行",
            "frame",
            1,
            REQUEST,
            (metadata_text,),
            contains="コマンド: /fix test_a.py",
        ),
        Highlight(
            "コマンドのファイルの本文（$ARGUMENTS に引数を入れたもの）",
            "text",
            1,
            REQUEST,
            (expand,),
            contains="テストを走らせ、失敗していれば直せ。対象: test_a.py",
        ),
        Highlight(
            "コマンドのファイルの前付け（description）",
            "not-sent",
            1,
            REQUEST,
            (split_front_matter,),
            excludes="description",
        ),
        Highlight(
            "自作のコマンドの一覧と説明",
            "not-sent",
            1,
            SYSTEM,
            (build_system_prompt,),
            excludes="テストを走らせ、失敗していれば直す",
        ),
        Highlight(
            "「コマンド: 」の行の、モデルへの説明",
            "text",
            1,
            SYSTEM,
            (read_instructions,),
            contains="「コマンド: 」の行があれば",
        ),
    ),
)

SKILL_BY_MODEL = Scenario(
    title="スキル（モデルが読み込む）",
    summary=(
        "スキルを置き、依頼を打つ。system prompt にスキルの一覧が入り、道具に load_skill が"
        "加わる。モデルが load_skill を呼ぶと、スキルの中身が道具の結果として入る。"
    ),
    lines=("convert.py をレビューして",),
    script=(
        calls(
            call("call_m6v1c8hs", "load_skill", name="review", arguments="convert.py")
        ),
        reply("観点ごとに挙げる。"),
    ),
    files=SKILL_FILES,
    highlights=(
        Highlight(
            "「# スキル」の節と、読み込み方の案内",
            "frame",
            1,
            SYSTEM,
            (skills_section,),
            contains="# スキル",
        ),
        Highlight(
            "スキルの名前と説明",
            "frame",
            1,
            SYSTEM,
            (skills_section,),
            contains="- review: コードを読み、観点ごとに問題を挙げる。引数は読むファイル",
        ),
        Highlight(
            "load_skill の道具（スキルがあるときだけ足す）",
            "field",
            1,
            "tools",
            (main,),
            count=6,
        ),
        Highlight(
            "読み込めるスキルの名前",
            "value",
            1,
            "tools[5].function.parameters.properties.name.enum",
            (load_skill.definition,),
            contains='["review"]',
        ),
        Highlight(
            "スキルの本文（$ARGUMENTS に引数を入れたもの）",
            "text",
            2,
            "messages[3].content",
            (skill_text,),
            contains=SKILL_BODY,
        ),
        Highlight(
            "スキルのディレクトリと、付いているファイルの一覧",
            "frame",
            2,
            "messages[3].content",
            (skill_text,),
            contains=(
                "付いているファイル（要るときに read_file で読む）:\n"
                "- .local-coding-agent/skills/review/checklist.md"
            ),
        ),
        Highlight(
            "スキルの中身は、load_skill の結果",
            "field",
            2,
            "messages[3].tool_name",
            (_tool_message,),
            contains="load_skill",
        ),
    ),
)

SKILL_BY_USER = Scenario(
    title="スキル（利用者が /<名前> で呼ぶ）",
    summary=(
        "スキルを /review で呼ぶ。ハーネスが、load_skill の結果と同じ中身を、依頼の発言として"
        "送る。呼んだ行は `<metadata>` の枠に入る。"
    ),
    lines=("/review convert.py",),
    script=(reply("観点ごとに挙げる。"),),
    files=SKILL_FILES,
    highlights=(
        Highlight(
            "呼んだスキルの行",
            "frame",
            1,
            REQUEST,
            (metadata_text,),
            contains="スキル: /review convert.py",
        ),
        Highlight(
            "スキルの中身（モデルが読み込むときと同じ文）",
            "text",
            1,
            REQUEST,
            (_send_skill, skill_text),
            contains=SKILL_BODY,
        ),
        Highlight(
            "「スキル: 」の行の、モデルへの説明（読み込み直さない）",
            "text",
            1,
            SYSTEM,
            (read_instructions,),
            contains="そのスキルを load_skill で読み込み直さない",
        ),
    ),
)

BUILTINS = Scenario(
    title="組み込みのコマンド",
    summary=(
        "依頼の間に、/help・/mode ask・/context を打ち、続けて依頼を打つ。その後 /clear を打ち、"
        "新しい依頼を打つ。組み込みのコマンドはハーネスの中で処理し、モデルを呼ばない。"
        "/mode で替えた許可のモードも送らない。"
    ),
    lines=(
        "こんにちは",
        "/help",
        "/mode ask",
        "/context",
        "続けて",
        "/clear",
        "新しい話",
    ),
    script=(reply("こんにちは。"), reply("続ける。"), reply("新しい話を聞く。")),
    highlights=(
        Highlight(
            "/help・/mode・/context の行と出力（履歴にも入らない）",
            "not-sent",
            2,
            "messages",
            (handle_line, run_builtin),
            count=4,
        ),
        Highlight(
            "/clear の前の発言（履歴を空にする）",
            "not-sent",
            3,
            "messages",
            (_clear,),
            count=2,
        ),
    ),
)
