"""会話の場面: 初回の依頼・2回目の依頼・指示の差し替え。"""

from local_coding_agent.cli.repl import _send
from local_coding_agent.context.environment import environment_section
from local_coding_agent.context.system_prompt import (
    build_system_prompt,
    read_instructions,
)
from local_coding_agent.loop.turn import run_turn
from local_coding_agent.model.messages import metadata_text
from local_coding_agent.model.ollama_messages import (
    _assistant,
    chat_request_body,
    to_ollama_messages,
    to_ollama_tools,
)
from tests.request_formats.scenario import Highlight, Scenario, reply

SYSTEM = "messages[0].content"

FIRST_REQUEST = Scenario(
    title="初回の依頼",
    summary=(
        "起動して、依頼を1行打つ。要求には、system prompt（指示・環境の節）と道具の定義と、"
        "依頼の発言が入る。作業ディレクトリにスキルが無いので、「# スキル」の節と load_skill の"
        "道具は無い。"
    ),
    lines=("こんにちは",),
    script=(reply("こんにちは。何を手伝いますか。"),),
    highlights=(
        Highlight(
            "モデルの名前（--model）",
            "field",
            1,
            "model",
            (chat_request_body,),
            contains="qwen3.5:9b",
        ),
        Highlight(
            "応答を流して受けること",
            "field",
            1,
            "stream",
            (chat_request_body,),
            contains="true",
        ),
        Highlight(
            "system prompt を、先頭の system の発言にする",
            "field",
            1,
            "messages[0].role",
            (to_ollama_messages,),
            contains="system",
        ),
        Highlight(
            "指示（既定の文）",
            "text",
            1,
            SYSTEM,
            (read_instructions,),
            contains="あなたは、利用者の端末で動くコーディングエージェントである",
        ),
        Highlight(
            "ハーネスが入れる情報（枠）の、モデルへの説明",
            "text",
            1,
            SYSTEM,
            (read_instructions,),
            contains="# ハーネスが入れる情報",
        ),
        Highlight(
            "環境（作業ディレクトリ・git のリポジトリの中か・OS）",
            "frame",
            1,
            SYSTEM,
            (environment_section, build_system_prompt),
            contains="# 環境",
        ),
        Highlight(
            "道具の定義（名前・説明・入力の形の JSON Schema）",
            "field",
            1,
            "tools",
            (to_ollama_tools,),
            count=5,
        ),
        Highlight(
            "利用者が打った行",
            "text",
            1,
            "messages[1].content",
            (run_turn,),
            contains="こんにちは",
        ),
        Highlight(
            "送った時刻（`<metadata>` の枠）",
            "frame",
            1,
            "messages[1].content",
            (metadata_text,),
            contains="<metadata>\n送った時刻: 2026-10-24 15:30 (+09:00)\n</metadata>\n",
        ),
    ),
)

SECOND_TURN = Scenario(
    title="2回目の依頼",
    summary=(
        "依頼を2回打つ。モデルの API は会話を覚えないので、2回目の要求には、1回目の依頼と"
        "答え（推論を含む）も入る。"
    ),
    lines=("1 + 1 は", "それに 2 を足すと"),
    script=(reply("2 です。", thinking="1 + 1 = 2。"), reply("4 です。")),
    highlights=(
        Highlight(
            "それまでの全ての発言",
            "field",
            2,
            "messages",
            (_send, run_turn),
            count=4,
        ),
        Highlight(
            "前の回の推論",
            "field",
            2,
            "messages[2].thinking",
            (_assistant,),
            contains="1 + 1 = 2。",
        ),
        Highlight(
            "前の回の答え",
            "text",
            2,
            "messages[2].content",
            (_assistant,),
            contains="2 です。",
        ),
        Highlight(
            "発言ごとの送った時刻",
            "frame",
            2,
            "messages[3].content",
            (metadata_text,),
            contains="送った時刻: 2026-10-24 15:31 (+09:00)",
        ),
    ),
)

INSTRUCTIONS_FILE = Scenario(
    title="指示の差し替え（--system-prompt-file）",
    summary=(
        "指示の部分を、ファイルの中身に差し替えて起動する。環境の節は残り、既定の指示"
        "（ハーネスが入れる情報の説明を含む）は送らない。"
    ),
    lines=("こんにちは",),
    script=(reply("こんにちは。"),),
    files={"short.md": "あなたは、短く答える。\n"},
    args=("--system-prompt-file", "{directory}/short.md"),
    highlights=(
        Highlight(
            "指示（ファイルの中身）",
            "text",
            1,
            SYSTEM,
            (read_instructions,),
            contains="あなたは、短く答える。",
        ),
        Highlight(
            "環境の節は残る",
            "frame",
            1,
            SYSTEM,
            (build_system_prompt, environment_section),
            contains="# 環境",
        ),
        Highlight(
            "既定の指示",
            "not-sent",
            1,
            SYSTEM,
            (read_instructions,),
            excludes="# ハーネスが入れる情報",
        ),
    ),
)
