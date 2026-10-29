"""文書の、場面に依らない文: 始めの説明・伝わり方の意味・送らない欄・場面の節の説明。"""

from tests.fakes import START
from tests.request_formats.harness import ENVIRONMENT
from tests.request_formats.scenario import Frame

GENERATE = ".venv/bin/python -m tests.request_formats"

HEAD = (
    "# モデルへ送る要求の形",
    "",
    (
        "エージェントは、モデルを呼ぶたびに、[Ollama](technologies/ollama.md) の `/api/chat` へ"
        " JSON を1つ送る。この文書では、これを要求と呼ぶ。要求には、system prompt（モデルへの指示）・"
        "道具の定義・それまでの会話の全ての発言が入る（[コーディングエージェントの仕組み]"
        "(how-coding-agents-work.md)）。"
    ),
    "",
    (
        "この文書は、利用者が使う機能の情報が、要求のどの欄に、どの形で入るかを、場面ごとに示す。"
        "情報は、Ollama の API が決めた欄に入るか、ハーネス（このエージェントのプログラム）が"
        "決めた形で、欄の中の文に入る。"
    ),
    "",
    (
        "この文書は生成したもので、手で直さない。場面は [tests/request_formats/]"
        "(../tests/request_formats/) にある。場面ごとに、起動の入口（`local_coding_agent/__main__.py`"
        " の `main`）から実物のコードを通し、送る直前の要求の本文を取った（実測）。差し替えたのは、"
        "モデルの応答（場面ごとの台本）・利用者の入力・時刻・環境の節の中身・家のディレクトリ・"
        f"画面の出力だけである。生成し直すコマンドは `{GENERATE}` である。テスト"
        " `tests/test_request_formats.py` が、この文書が今のコードから生成したものと同じかを確かめる。"
    ),
    "",
)

FRAME_MEANINGS: tuple[tuple[Frame, str], ...] = (
    (
        "field",
        (
            "Ollama の API が決めた欄（`role`・`tools`・`tool_calls`・`thinking`・`tool_name`・"
            "`tool_call_id` など）に入る。Ollama は、発言の並びを、モデルごとの雛形（Modelfile の"
            " `TEMPLATE`）で1つの文に組み立てる。役割や道具の呼び出しは、モデルが学習した形の印になる"
        ),
    ),
    (
        "frame",
        (
            "Ollama の欄の中の文に、ハーネスが決めた形（見出し・タグ・印・行の形）で入る。Ollama と"
            "モデルにとっては、文の一部である。モデルは、既定の指示の「# ハーネスが入れる情報」の"
            "説明と、文の形から意味を読み取る"
        ),
    ),
    (
        "value",
        (
            "道具の定義の入力の形（JSON Schema）の中に、ハーネスがその時の状況に合わせて入れた値。"
            "ハーネスは、モデルの呼び出しの入力を、この値と照らす"
        ),
    ),
    (
        "text",
        (
            "利用者・ファイル（指示・コマンド・スキル）・ハーネスの既定の指示が書いた文が、"
            "形を変えずに入る"
        ),
    ),
    ("not-sent", "要求に入らない。ハーネスの中だけで扱う"),
)

NOT_SENT = (
    ("think", "推論をするか・推論の強さ。送らないので、モデルの既定に従う"),
    ("format", "出力の形の指定（JSON Schema など）"),
    ("truncate", "文脈の長さを超えたときに、古い発言から切り詰めるか"),
    ("keep_alive", "応答の後に、モデルをメモリに置いておく時間"),
)

SCENARIOS_HEAD = (
    "## 場面",
    "",
    (
        "場面ごとに、打つ行・作業ディレクトリに置くファイル・見どころ・送った要求を示す。要求は、"
        "前の要求（場面の最初の要求では、場面 1 の最初の要求）と同じ所を省き、そう書く。改行を"
        "含む文は、JSON の中では ⟨文 1⟩ のように書き、JSON の後にそのまま示す。"
    ),
    "",
    (
        f"時刻は {START:%Y-%m-%d %H:%M} から、依頼ごとに1分ずつ進めた。環境の節の作業ディレクトリは"
        f" `{ENVIRONMENT.working_directory}`、OS は `{ENVIRONMENT.os}` に差し替えた。道具の呼び出しの"
        " id は台本に書いた値で、Ollama が付ける id と同じ形にした。"
    ),
    "",
)
