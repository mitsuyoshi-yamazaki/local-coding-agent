"""道具の場面: モデルが道具を呼ぶ・道具の結果の種類・止まった回の後の依頼。"""

import json

from local_coding_agent.loop.tool_call import execute
from local_coding_agent.loop.turn import _stopped
from local_coding_agent.model.chat import ModelError
from local_coding_agent.model.ollama_messages import (
    _assistant,
    _tool_call,
    _tool_message,
    _tool_names,
    _user,
)
from local_coding_agent.permissions.confirm import refusal
from local_coding_agent.permissions.policy import denial
from local_coding_agent.tools import read_file, run_command
from local_coding_agent.tools.input_check import input_problem
from tests.request_formats.scenario import Highlight, Scenario, call, calls, reply

NOTES = {"notes.txt": "買うもの: 牛乳\n"}

TOOL_CALL = Scenario(
    title="モデルが道具を呼ぶ",
    summary=(
        "モデルが推論の後に read_file を呼び、ハーネスが実行して結果を返す。2つ目の要求に、"
        "モデルの発言（推論・呼び出し）と、結果の発言が入る。"
    ),
    lines=("notes.txt を読んで",),
    script=(
        calls(
            call("call_k3m9q2xa", "read_file", path="notes.txt"),
            thinking="notes.txt を読めばよい。",
        ),
        reply("牛乳を買う、と書いてある。"),
    ),
    files=NOTES,
    highlights=(
        Highlight(
            "モデルの推論（次の要求で戻す）",
            "field",
            2,
            "messages[2].thinking",
            (_assistant,),
            contains="notes.txt を読めばよい。",
        ),
        Highlight(
            "道具の呼び出し（名前と入力）",
            "field",
            2,
            "messages[2].tool_calls[0].function",
            (_tool_call,),
            contains='"name": "read_file", "arguments": {"path": "notes.txt"}',
        ),
        Highlight(
            "呼び出しの id（モデルの API が付けたもの）",
            "field",
            2,
            "messages[2].tool_calls[0].id",
            (_tool_call,),
            contains="call_k3m9q2xa",
        ),
        Highlight(
            "道具の結果を、tool の発言にする",
            "field",
            2,
            "messages[3].role",
            (_user, _tool_message),
            contains="tool",
        ),
        Highlight(
            "結果がどの呼び出しのものか",
            "field",
            2,
            "messages[3].tool_call_id",
            (_tool_message,),
            contains="call_k3m9q2xa",
        ),
        Highlight(
            "結果の道具の名前（呼び出しの id から引く）",
            "field",
            2,
            "messages[3].tool_name",
            (_tool_message, _tool_names),
            contains="read_file",
        ),
        Highlight(
            "read_file の結果（行番号・タブ・行）",
            "frame",
            2,
            "messages[3].content",
            (read_file.run,),
            contains="     1\t買うもの: 牛乳",
        ),
    ),
)

_SETTINGS = {
    "permissions": {
        "mode": "ask",
        "allow": ["run_command(echo *)"],
        "deny": [{"rule": "run_command(rm *)", "reason": "消すのは人が行う"}],
    }
}

TOOL_RESULTS = Scenario(
    title="道具の結果の種類",
    summary=(
        "許可のモードを ask にし、規則を2つ置く（echo は通す・rm は理由を添えて拒む）。"
        "モデルが1つの応答で6つの道具を呼び、ハーネスが順に処理する。2行目は、write_file を"
        "実行してよいかの問いへの答え（拒む理由）である。呼び出し1つに、tool の発言が1つ入る。"
    ),
    lines=("notes.txt を片付けて", "残しておきたい"),
    script=(
        calls(
            call("call_p4w8n1zb", "read_file", path="memo.txt"),
            call("call_t6c2v5rd", "read_file"),
            call("call_h9j3x7lm", "run_command", command="rm notes.txt"),
            call("call_b5q1s8ke", "write_file", path="notes.txt", content="（空）"),
            call("call_f2y6g4ua", "run_command", command="echo 片付けた"),
            call("call_n8d3r6wc", "delete_file", path="notes.txt"),
        ),
        reply("片付けられなかった。"),
    ),
    files={
        **NOTES,
        ".local-coding-agent/settings.json": json.dumps(_SETTINGS, ensure_ascii=False),
    },
    highlights=(
        Highlight(
            "呼び出し1つに、tool の発言1つ", "field", 2, "messages", (_user,), count=9
        ),
        Highlight(
            "道具が返した誤り（tool の発言に誤りの欄が無いので、文の頭の印）",
            "frame",
            2,
            "messages[3].content",
            (_tool_message, read_file.run),
            contains="誤り: ファイルが無い: memo.txt",
        ),
        Highlight(
            "入力が定義に合わない",
            "frame",
            2,
            "messages[4].content",
            (execute, input_problem),
            contains="誤り: 入力が定義に合わない: 必須の欄が無い: path",
        ),
        Highlight(
            "規則で拒んだ（合った規則）",
            "frame",
            2,
            "messages[5].content",
            (denial,),
            contains="誤り: 規則で拒んだ: run_command(rm *)",
        ),
        Highlight(
            "利用者が規則に添えた理由",
            "frame",
            2,
            "messages[5].content",
            (denial,),
            contains="理由: 消すのは人が行う。",
        ),
        Highlight(
            "利用者が実行を拒んだ理由（問いへの答え）",
            "frame",
            2,
            "messages[6].content",
            (refusal,),
            contains="誤り: 利用者が実行を拒んだ。理由: 残しておきたい",
        ),
        Highlight(
            "コマンドの終了コード（1行目）と出力",
            "frame",
            2,
            "messages[7].content",
            (run_command.run,),
            contains="終了コード: 0\n片付けた",
        ),
        Highlight(
            "知らない道具",
            "frame",
            2,
            "messages[8].content",
            (execute,),
            contains="誤り: 知らない道具: delete_file",
        ),
    ),
)

STOPPED = Scenario(
    title="止まった回の後の依頼",
    summary=(
        "1回目は、道具の結果の後に Ctrl-C で止める。2回目は、道具の結果の後にモデルとの通信が"
        "切れる。どちらも、済んだ歩み（呼び出しと結果）までを履歴に残し、結果の発言の末尾に"
        "止まったことの知らせを足す。止まった要求（要求 2・要求 4）には応答が無い。"
    ),
    lines=("notes.txt を読んで", "もう一度読んで", "どうなった"),
    script=(
        calls(call("call_e7u2k9pd", "read_file", path="notes.txt")),
        (KeyboardInterrupt(),),
        calls(call("call_w3z8m5qt", "read_file", path="notes.txt")),
        (ModelError("Ollama との通信が切れた: 接続が閉じられた"),),
        reply("2回とも、途中で止まった。"),
    ),
    files=NOTES,
    highlights=(
        Highlight(
            "止まった要求の応答は、履歴に足さない",
            "not-sent",
            3,
            "messages",
            (_stopped,),
            count=6,
        ),
        Highlight(
            "止めた回の知らせ",
            "frame",
            3,
            "messages[4].content",
            (_stopped,),
            contains="（利用者がこの回を途中で止めた）",
        ),
        Highlight(
            "知らせは、tool の発言の後の、別の user の発言になる",
            "field",
            3,
            "messages[4].role",
            (_user,),
            contains="user",
        ),
        Highlight(
            "誤りで止まった回の知らせ",
            "frame",
            5,
            "messages[8].content",
            (_stopped, _user),
            contains="（誤りで、この回が途中で止まった）",
        ),
    ),
)
