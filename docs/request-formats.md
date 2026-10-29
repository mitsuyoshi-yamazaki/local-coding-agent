# モデルへ送る要求の形

エージェントは、モデルを呼ぶたびに、[Ollama](technologies/ollama.md) の `/api/chat` へ JSON を1つ送る。この文書では、これを要求と呼ぶ。要求には、system prompt（モデルへの指示）・道具の定義・それまでの会話の全ての発言が入る（[コーディングエージェントの仕組み](how-coding-agents-work.md)）。

この文書は、利用者が使う機能の情報が、要求のどの欄に、どの形で入るかを、場面ごとに示す。情報は、Ollama の API が決めた欄に入るか、ハーネス（このエージェントのプログラム）が決めた形で、欄の中の文に入る。

この文書は生成したもので、手で直さない。場面は [tests/request_formats/](../tests/request_formats/) にある。場面ごとに、起動の入口（`local_coding_agent/__main__.py` の `main`）から実物のコードを通し、送る直前の要求の本文を取った（実測）。差し替えたのは、モデルの応答（場面ごとの台本）・利用者の入力・時刻・環境の節の中身・家のディレクトリ・画面の出力だけである。生成し直すコマンドは `.venv/bin/python -m tests.request_formats` である。テスト `tests/test_request_formats.py` が、この文書が今のコードから生成したものと同じかを確かめる。

## 伝わり方の種類

| 伝わり方 | 意味 |
|---|---|
| Ollama の欄 | Ollama の API が決めた欄（`role`・`tools`・`tool_calls`・`thinking`・`tool_name`・`tool_call_id` など）に入る。Ollama は、発言の並びを、モデルごとの雛形（Modelfile の `TEMPLATE`）で1つの文に組み立てる。役割や道具の呼び出しは、モデルが学習した形の印になる |
| ハーネスの枠 | Ollama の欄の中の文に、ハーネスが決めた形（見出し・タグ・印・行の形）で入る。Ollama とモデルにとっては、文の一部である。モデルは、既定の指示の「# ハーネスが入れる情報」の説明と、文の形から意味を読み取る |
| ハーネスの値 | 道具の定義の入力の形（JSON Schema）の中に、ハーネスがその時の状況に合わせて入れた値。ハーネスは、モデルの呼び出しの入力を、この値と照らす |
| そのままの文 | 利用者・ファイル（指示・コマンド・スキル）・ハーネスの既定の指示が書いた文が、形を変えずに入る |
| 送らない | 要求に入らない。ハーネスの中だけで扱う |

## 送る欄

要求の本文の一番上の欄は、どの場面でも次のとおりである。

- 送る欄: `model`・`messages`・`stream`・`tools`
- [Ollama](technologies/ollama.md) の `/api/chat` にあり、送らない欄:
  - `think`: 推論をするか・推論の強さ。送らないので、モデルの既定に従う
  - `format`: 出力の形の指定（JSON Schema など）
  - `truncate`: 文脈の長さを超えたときに、古い発言から切り詰めるか
  - `keep_alive`: 応答の後に、モデルをメモリに置いておく時間

## 一覧

場面ごとの見どころ（ある情報が、要求のどこに、どの伝わり方で入るか）の全てである。照らした文は、生成のときに、その場所にあることを確かめた文である。

| 場面 | 情報 | 伝わり方 | 場所 | 照らした文 |
|---|---|---|---|---|
| 1. 初回の依頼 | モデルの名前（--model） | Ollama の欄 | 要求 1 の `model` | `qwen3.5:9b` |
| 1. 初回の依頼 | 応答を流して受けること | Ollama の欄 | 要求 1 の `stream` | `true` |
| 1. 初回の依頼 | system prompt を、先頭の system の発言にする | Ollama の欄 | 要求 1 の `messages[0].role` | `system` |
| 1. 初回の依頼 | 指示（既定の文） | そのままの文 | 要求 1 の `messages[0].content` | `あなたは、利用者の端末で動くコーディングエージェントである` |
| 1. 初回の依頼 | ハーネスが入れる情報（枠）の、モデルへの説明 | そのままの文 | 要求 1 の `messages[0].content` | `# ハーネスが入れる情報` |
| 1. 初回の依頼 | 環境（作業ディレクトリ・git のリポジトリの中か・OS） | ハーネスの枠 | 要求 1 の `messages[0].content` | `# 環境` |
| 1. 初回の依頼 | 道具の定義（名前・説明・入力の形の JSON Schema） | Ollama の欄 | 要求 1 の `tools` | 5 個 |
| 1. 初回の依頼 | 利用者が打った行 | そのままの文 | 要求 1 の `messages[1].content` | `こんにちは` |
| 1. 初回の依頼 | 送った時刻（`<metadata>` の枠） | ハーネスの枠 | 要求 1 の `messages[1].content` | `<metadata>\n送った時刻: 2026-10-24 15:30 (+09:00)\n</metadata>\n` |
| 2. モデルが道具を呼ぶ | モデルの推論（次の要求で戻す） | Ollama の欄 | 要求 2 の `messages[2].thinking` | `notes.txt を読めばよい。` |
| 2. モデルが道具を呼ぶ | 道具の呼び出し（名前と入力） | Ollama の欄 | 要求 2 の `messages[2].tool_calls[0].function` | `"name": "read_file", "arguments": {"path": "notes.txt"}` |
| 2. モデルが道具を呼ぶ | 呼び出しの id（モデルの API が付けたもの） | Ollama の欄 | 要求 2 の `messages[2].tool_calls[0].id` | `call_k3m9q2xa` |
| 2. モデルが道具を呼ぶ | 道具の結果を、tool の発言にする | Ollama の欄 | 要求 2 の `messages[3].role` | `tool` |
| 2. モデルが道具を呼ぶ | 結果がどの呼び出しのものか | Ollama の欄 | 要求 2 の `messages[3].tool_call_id` | `call_k3m9q2xa` |
| 2. モデルが道具を呼ぶ | 結果の道具の名前（呼び出しの id から引く） | Ollama の欄 | 要求 2 の `messages[3].tool_name` | `read_file` |
| 2. モデルが道具を呼ぶ | read_file の結果（行番号・タブ・行） | ハーネスの枠 | 要求 2 の `messages[3].content` | `     1\t買うもの: 牛乳` |
| 3. 道具の結果の種類 | 呼び出し1つに、tool の発言1つ | Ollama の欄 | 要求 2 の `messages` | 9 個 |
| 3. 道具の結果の種類 | 道具が返した誤り（tool の発言に誤りの欄が無いので、文の頭の印） | ハーネスの枠 | 要求 2 の `messages[3].content` | `誤り: ファイルが無い: memo.txt` |
| 3. 道具の結果の種類 | 入力が定義に合わない | ハーネスの枠 | 要求 2 の `messages[4].content` | `誤り: 入力が定義に合わない: 必須の欄が無い: path` |
| 3. 道具の結果の種類 | 規則で拒んだ（合った規則） | ハーネスの枠 | 要求 2 の `messages[5].content` | `誤り: 規則で拒んだ: run_command(rm *)` |
| 3. 道具の結果の種類 | 利用者が規則に添えた理由 | ハーネスの枠 | 要求 2 の `messages[5].content` | `理由: 消すのは人が行う。` |
| 3. 道具の結果の種類 | 利用者が実行を拒んだ理由（問いへの答え） | ハーネスの枠 | 要求 2 の `messages[6].content` | `誤り: 利用者が実行を拒んだ。理由: 残しておきたい` |
| 3. 道具の結果の種類 | コマンドの終了コード（1行目）と出力 | ハーネスの枠 | 要求 2 の `messages[7].content` | `終了コード: 0\n片付けた` |
| 3. 道具の結果の種類 | 知らない道具 | ハーネスの枠 | 要求 2 の `messages[8].content` | `誤り: 知らない道具: delete_file` |
| 4. 自作のコマンド | 呼んだコマンドの行 | ハーネスの枠 | 要求 1 の `messages[1].content` | `コマンド: /fix test_a.py` |
| 4. 自作のコマンド | コマンドのファイルの本文（$ARGUMENTS に引数を入れたもの） | そのままの文 | 要求 1 の `messages[1].content` | `テストを走らせ、失敗していれば直せ。対象: test_a.py` |
| 4. 自作のコマンド | コマンドのファイルの前付け（description） | 送らない | 要求 1 の `messages[1].content` | `description` を含まない |
| 4. 自作のコマンド | 自作のコマンドの一覧と説明 | 送らない | 要求 1 の `messages[0].content` | `テストを走らせ、失敗していれば直す` を含まない |
| 4. 自作のコマンド | 「コマンド: 」の行の、モデルへの説明 | そのままの文 | 要求 1 の `messages[0].content` | `「コマンド: 」の行があれば` |
| 5. スキル（モデルが読み込む） | 「# スキル」の節と、読み込み方の案内 | ハーネスの枠 | 要求 1 の `messages[0].content` | `# スキル` |
| 5. スキル（モデルが読み込む） | スキルの名前と説明 | ハーネスの枠 | 要求 1 の `messages[0].content` | `- review: コードを読み、観点ごとに問題を挙げる。引数は読むファイル` |
| 5. スキル（モデルが読み込む） | load_skill の道具（スキルがあるときだけ足す） | Ollama の欄 | 要求 1 の `tools` | 6 個 |
| 5. スキル（モデルが読み込む） | 読み込めるスキルの名前 | ハーネスの値 | 要求 1 の `tools[5].function.parameters.properties.name.enum` | `["review"]` |
| 5. スキル（モデルが読み込む） | スキルの本文（$ARGUMENTS に引数を入れたもの） | そのままの文 | 要求 2 の `messages[3].content` | `convert.py を読み、checklist.md の観点ごとに` |
| 5. スキル（モデルが読み込む） | スキルのディレクトリと、付いているファイルの一覧 | ハーネスの枠 | 要求 2 の `messages[3].content` | `付いているファイル（要るときに read_file で読む）:\n- .local-coding-agent/skills/review/checklist.md` |
| 5. スキル（モデルが読み込む） | スキルの中身は、load_skill の結果 | Ollama の欄 | 要求 2 の `messages[3].tool_name` | `load_skill` |
| 6. スキル（利用者が /<名前> で呼ぶ） | 呼んだスキルの行 | ハーネスの枠 | 要求 1 の `messages[1].content` | `スキル: /review convert.py` |
| 6. スキル（利用者が /<名前> で呼ぶ） | スキルの中身（モデルが読み込むときと同じ文） | そのままの文 | 要求 1 の `messages[1].content` | `convert.py を読み、checklist.md の観点ごとに` |
| 6. スキル（利用者が /<名前> で呼ぶ） | 「スキル: 」の行の、モデルへの説明（読み込み直さない） | そのままの文 | 要求 1 の `messages[0].content` | `そのスキルを load_skill で読み込み直さない` |
| 7. 組み込みのコマンド | /help・/mode・/context の行と出力（履歴にも入らない） | 送らない | 要求 2 の `messages` | 4 個 |
| 7. 組み込みのコマンド | /clear の前の発言（履歴を空にする） | 送らない | 要求 3 の `messages` | 2 個 |
| 8. 止まった回の後の依頼 | 止まった要求の応答は、履歴に足さない | 送らない | 要求 3 の `messages` | 6 個 |
| 8. 止まった回の後の依頼 | 止めた回の知らせ | ハーネスの枠 | 要求 3 の `messages[4].content` | `（利用者がこの回を途中で止めた）` |
| 8. 止まった回の後の依頼 | 知らせは、tool の発言の後の、別の user の発言になる | Ollama の欄 | 要求 3 の `messages[4].role` | `user` |
| 8. 止まった回の後の依頼 | 誤りで止まった回の知らせ | ハーネスの枠 | 要求 5 の `messages[8].content` | `（誤りで、この回が途中で止まった）` |
| 9. 2回目の依頼 | それまでの全ての発言 | Ollama の欄 | 要求 2 の `messages` | 4 個 |
| 9. 2回目の依頼 | 前の回の推論 | Ollama の欄 | 要求 2 の `messages[2].thinking` | `1 + 1 = 2。` |
| 9. 2回目の依頼 | 前の回の答え | そのままの文 | 要求 2 の `messages[2].content` | `2 です。` |
| 9. 2回目の依頼 | 発言ごとの送った時刻 | ハーネスの枠 | 要求 2 の `messages[3].content` | `送った時刻: 2026-10-24 15:31 (+09:00)` |
| 10. 指示の差し替え（--system-prompt-file） | 指示（ファイルの中身） | そのままの文 | 要求 1 の `messages[0].content` | `あなたは、短く答える。` |
| 10. 指示の差し替え（--system-prompt-file） | 環境の節は残る | ハーネスの枠 | 要求 1 の `messages[0].content` | `# 環境` |
| 10. 指示の差し替え（--system-prompt-file） | 既定の指示 | 送らない | 要求 1 の `messages[0].content` | `# ハーネスが入れる情報` を含まない |

## 場面

場面ごとに、打つ行・作業ディレクトリに置くファイル・見どころ・送った要求を示す。要求は、前の要求（場面の最初の要求では、場面 1 の最初の要求）と同じ所を省き、そう書く。改行を含む文は、JSON の中では ⟨文 1⟩ のように書き、JSON の後にそのまま示す。

時刻は 2026-10-24 15:30 から、依頼ごとに1分ずつ進めた。環境の節の作業ディレクトリは `/work/project`、OS は `macOS 15.6（Darwin 24.6.0）` に差し替えた。道具の呼び出しの id は台本に書いた値で、Ollama が付ける id と同じ形にした。

### 1. 初回の依頼

起動して、依頼を1行打つ。要求には、system prompt（指示・環境の節）と道具の定義と、依頼の発言が入る。作業ディレクトリにスキルが無いので、「# スキル」の節と load_skill の道具は無い。

打つ行（上から順に）:

1. `こんにちは`

見どころ:

| 情報 | 伝わり方 | 場所 | 照らした文 | 作る所 |
|---|---|---|---|---|
| モデルの名前（--model） | Ollama の欄 | 要求 1 の `model` | `qwen3.5:9b` | [`ollama_messages.chat_request_body`](../local_coding_agent/model/ollama_messages.py) |
| 応答を流して受けること | Ollama の欄 | 要求 1 の `stream` | `true` | [`ollama_messages.chat_request_body`](../local_coding_agent/model/ollama_messages.py) |
| system prompt を、先頭の system の発言にする | Ollama の欄 | 要求 1 の `messages[0].role` | `system` | [`ollama_messages.to_ollama_messages`](../local_coding_agent/model/ollama_messages.py) |
| 指示（既定の文） | そのままの文 | 要求 1 の `messages[0].content` | `あなたは、利用者の端末で動くコーディングエージェントである` | [`system_prompt.read_instructions`](../local_coding_agent/context/system_prompt.py) |
| ハーネスが入れる情報（枠）の、モデルへの説明 | そのままの文 | 要求 1 の `messages[0].content` | `# ハーネスが入れる情報` | [`system_prompt.read_instructions`](../local_coding_agent/context/system_prompt.py) |
| 環境（作業ディレクトリ・git のリポジトリの中か・OS） | ハーネスの枠 | 要求 1 の `messages[0].content` | `# 環境` | [`environment.environment_section`](../local_coding_agent/context/environment.py)・[`system_prompt.build_system_prompt`](../local_coding_agent/context/system_prompt.py) |
| 道具の定義（名前・説明・入力の形の JSON Schema） | Ollama の欄 | 要求 1 の `tools` | 5 個 | [`ollama_messages.to_ollama_tools`](../local_coding_agent/model/ollama_messages.py) |
| 利用者が打った行 | そのままの文 | 要求 1 の `messages[1].content` | `こんにちは` | [`turn.run_turn`](../local_coding_agent/loop/turn.py) |
| 送った時刻（`<metadata>` の枠） | ハーネスの枠 | 要求 1 の `messages[1].content` | `<metadata>\n送った時刻: 2026-10-24 15:30 (+09:00)\n</metadata>\n` | [`messages.metadata_text`](../local_coding_agent/model/messages.py) |

#### 要求 1

- `model`: `"qwen3.5:9b"`
- `stream`: `true`
- `tools`: 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 2 個

`tools`:

```json
[
  {
    "type": "function",
    "function": {
      "name": "read_file",
      "description": "ファイルを読む。行番号を付けて返す（cat -n と同じ形）。既定では先頭から 2000 行を読む。長いファイルは offset と limit で続きを読む。",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "読むファイル。作業ディレクトリからの相対パスか、絶対パス"
          },
          "offset": {
            "type": "integer",
            "minimum": 1,
            "description": "何行目から読むか。既定は 1"
          },
          "limit": {
            "type": "integer",
            "minimum": 1,
            "description": "何行読むか。既定は 2000"
          }
        },
        "required": [
          "path"
        ]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "list_directory",
      "description": "ディレクトリの中身を1段だけ見る。名前を1行に1つ、名前の順に返す。ディレクトリの名前の末尾には / を付ける。",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "見るディレクトリ。作業ディレクトリからの相対パスか、絶対パス。既定は作業ディレクトリ"
          }
        }
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "write_file",
      "description": "ファイルを丸ごと書く。ファイルが無ければ作り（親のディレクトリも作る）、あれば中身を content で置き換える。既存のファイルの一部を直すときは edit_file を使う。",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "書くファイル。作業ディレクトリからの相対パスか、絶対パス"
          },
          "content": {
            "type": "string",
            "description": "書く中身の全体"
          }
        },
        "required": [
          "path",
          "content"
        ]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "edit_file",
      "description": "ファイルの中の old_string を new_string に置き換える。old_string は、read_file の結果から行番号とタブを除き、字下げと空白を含めてそのまま写す。old_string がファイルの中の1か所だけに合うよう、前後の行を含める。合う所を全て置き換えるときは replace_all に true を渡す。そのままでは見つからないときは、行末の空白と字下げのずれを除いて探す。新しいファイルは write_file で作る。",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "直すファイル。作業ディレクトリからの相対パスか、絶対パス"
          },
          "old_string": {
            "type": "string",
            "description": "置き換える元"
          },
          "new_string": {
            "type": "string",
            "description": "置き換えた後"
          },
          "replace_all": {
            "type": "boolean",
            "description": "true なら、合う所を全て置き換える。既定は false"
          }
        },
        "required": [
          "path",
          "old_string",
          "new_string"
        ]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "run_command",
      "description": "シェルのコマンドを /bin/sh -c で走らせ、終了コードと出力（標準出力と標準エラーを合わせたもの）を返す。コードを直した後に、テストを走らせて確かめるときに使う。毎回、作業ディレクトリで走る。cd と環境変数は、次のコマンドに残らない。標準入力は空である。入力を待つコマンドと、終わらないコマンド（サーバなど）は走らせない。出力が 10000 字を超えると、間を省く。",
      "parameters": {
        "type": "object",
        "properties": {
          "command": {
            "type": "string",
            "description": "走らせるコマンド"
          },
          "timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 600,
            "description": "終わるのを待つ秒数。過ぎたら止める。既定は 120"
          }
        },
        "required": [
          "command"
        ]
      }
    }
  }
]
```

`messages`:

```json
[
  {
    "role": "system",
    "content": "⟨文 1⟩"
  },
  {
    "role": "user",
    "content": "⟨文 2⟩"
  }
]
```

⟨文 1⟩（`messages[0].content`）:

```text
あなたは、利用者の端末で動くコーディングエージェントである。利用者のソフトウェア開発を手伝う。

# 答え方

- 利用者が書いた言語で答える
- 簡潔に答える。聞かれていないことを長く書かない
- 分からないことは、分からないと答える。推測で答えるときは、推測だと書く

# できること

- ファイルを読む道具（read_file）と、ディレクトリの中身を見る道具（list_directory）を持つ
- ファイルを書く道具（write_file）と、ファイルの一部を置き換える道具（edit_file）を持つ
- コマンドを走らせる道具（run_command）を持つ
- 道具を実行してよいかは、利用者が設定した許可の規則で、ハーネスが決める。実行の前に利用者が確かめることも、規則で拒まれることもある
- 利用者が実行を拒んだら、理由が付いていればそれに従い、やり方を変えるか、利用者に尋ねる
- 規則で拒まれた操作は、別の道具やコマンドで行わない。要るなら、利用者に尋ねる
- 読んでいないファイルの中身を、読んだように答えない

# 道具の使い方

- ファイルの中身やディレクトリの様子が要るときは、推測せずに道具で確かめる
- パスは、作業ディレクトリからの相対パスか、絶対パスで渡す
- あなたはループの中にいる。道具の結果を読んでから、続けて道具を呼んでよい。一度に複数の道具を呼んでもよい
- 答えに要ることが揃ったら、道具を呼ばずに答える
- 長いファイルは、offset と limit で続きを読む
- 既存のファイルを直す前に、read_file で読む
- 一部を直すときは edit_file を、新しいファイルを作るときと全体を書き直すときは write_file を使う
- edit_file の old_string は、read_file の結果から行番号とタブを除き、字下げと空白を含めてそのまま写す。1か所だけに合うよう、前後の行を含める
- コードを直したら、run_command でテストを走らせて確かめる。失敗したら、出力を読んで直し、もう一度走らせる。通ったことを確かめてから答える
- テストの走らせ方が分からないときは、README などを読んで確かめる
- run_command は、毎回、作業ディレクトリで走る。cd と環境変数は、次のコマンドに残らない
- run_command の標準入力は空である。入力を待つコマンドと、終わらないコマンド（サーバなど）は走らせない

# ハーネスが入れる情報

ハーネス（あなたを動かしているプログラム）は、次の情報を入れる。どれも、利用者が書いたものではない。

- この指示の後の「# 環境」の節: 起動のときの環境
- 「# 環境」の後の「# スキル」の節（あれば）: 作業ディレクトリに置かれたスキルの名前と説明。読み込み方は、その節にある
- 利用者の発言の先頭の <metadata> の中: その発言を送った時刻。「コマンド: 」の行があれば、利用者がそのコマンドを呼び、ハーネスが、コマンドのファイルの中身（引数を入れたもの）を、その発言の本文として送った。「スキル: 」の行があれば、利用者がそのスキルを呼び、ハーネスが、スキルの中身（引数を入れたもの）を、その発言の本文として送った。そのスキルを load_skill で読み込み直さない
- 道具の結果: あなたが呼んだ道具を、ハーネスが実行した結果。誤りのときは「誤り: 」で始まる
- 「規則で拒んだ: 」で始まる誤り: 利用者が設定した許可の規則で、ハーネスが道具を実行しなかった。後ろに、合った規則と、利用者が規則に添えた理由が付く
- 「利用者が実行を拒んだ」の後の「理由: 」: 利用者が、実行の前の問いに答えて書いた、拒んだ理由
- run_command の結果の1行目: コマンドの終了コード（0 なら成功）か、時間切れで止めたこと。2行目からが、コマンドの出力である
- 道具の結果の後の「（利用者がこの回を途中で止めた）」などの知らせ: その回が途中で止まった。止まる前に済んだ道具の結果は、そのまま効いている

# 環境

- 作業ディレクトリ: /work/project
- 作業ディレクトリは git のリポジトリの中か: はい
- OS: macOS 15.6（Darwin 24.6.0）
```

⟨文 2⟩（`messages[1].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:30 (+09:00)
</metadata>
こんにちは
```

### 2. モデルが道具を呼ぶ

モデルが推論の後に read_file を呼び、ハーネスが実行して結果を返す。2つ目の要求に、モデルの発言（推論・呼び出し）と、結果の発言が入る。

打つ行（上から順に）:

1. `notes.txt を読んで`

作業ディレクトリに置くファイル `notes.txt`:

```text
買うもの: 牛乳
```

見どころ:

| 情報 | 伝わり方 | 場所 | 照らした文 | 作る所 |
|---|---|---|---|---|
| モデルの推論（次の要求で戻す） | Ollama の欄 | 要求 2 の `messages[2].thinking` | `notes.txt を読めばよい。` | [`ollama_messages._assistant`](../local_coding_agent/model/ollama_messages.py) |
| 道具の呼び出し（名前と入力） | Ollama の欄 | 要求 2 の `messages[2].tool_calls[0].function` | `"name": "read_file", "arguments": {"path": "notes.txt"}` | [`ollama_messages._tool_call`](../local_coding_agent/model/ollama_messages.py) |
| 呼び出しの id（モデルの API が付けたもの） | Ollama の欄 | 要求 2 の `messages[2].tool_calls[0].id` | `call_k3m9q2xa` | [`ollama_messages._tool_call`](../local_coding_agent/model/ollama_messages.py) |
| 道具の結果を、tool の発言にする | Ollama の欄 | 要求 2 の `messages[3].role` | `tool` | [`ollama_messages._user`](../local_coding_agent/model/ollama_messages.py)・[`ollama_messages._tool_message`](../local_coding_agent/model/ollama_messages.py) |
| 結果がどの呼び出しのものか | Ollama の欄 | 要求 2 の `messages[3].tool_call_id` | `call_k3m9q2xa` | [`ollama_messages._tool_message`](../local_coding_agent/model/ollama_messages.py) |
| 結果の道具の名前（呼び出しの id から引く） | Ollama の欄 | 要求 2 の `messages[3].tool_name` | `read_file` | [`ollama_messages._tool_message`](../local_coding_agent/model/ollama_messages.py)・[`ollama_messages._tool_names`](../local_coding_agent/model/ollama_messages.py) |
| read_file の結果（行番号・タブ・行） | ハーネスの枠 | 要求 2 の `messages[3].content` | `     1\t買うもの: 牛乳` | [`read_file.run`](../local_coding_agent/tools/read_file.py) |

#### 要求 1

- `tools`: 場面 1 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 2 個。messages[0]（system の発言）は場面 1 と同じ

`messages[1]` から:

```json
[
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[1].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:30 (+09:00)
</metadata>
notes.txt を読んで
```

#### 要求 2

- `tools`: 要求 1 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 4 個。要求 1 の 2 個の後に、2 個を足した

`messages[2]` から:

```json
[
  {
    "role": "assistant",
    "content": "",
    "thinking": "notes.txt を読めばよい。",
    "tool_calls": [
      {
        "id": "call_k3m9q2xa",
        "function": {
          "index": 0,
          "name": "read_file",
          "arguments": {
            "path": "notes.txt"
          }
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_name": "read_file",
    "tool_call_id": "call_k3m9q2xa",
    "content": "     1\t買うもの: 牛乳"
  }
]
```

### 3. 道具の結果の種類

許可のモードを ask にし、規則を2つ置く（echo は通す・rm は理由を添えて拒む）。モデルが1つの応答で6つの道具を呼び、ハーネスが順に処理する。2行目は、write_file を実行してよいかの問いへの答え（拒む理由）である。呼び出し1つに、tool の発言が1つ入る。

打つ行（上から順に）:

1. `notes.txt を片付けて`
2. `残しておきたい`

作業ディレクトリに置くファイル `notes.txt`:

```text
買うもの: 牛乳
```

作業ディレクトリに置くファイル `.local-coding-agent/settings.json`:

```text
{"permissions": {"mode": "ask", "allow": ["run_command(echo *)"], "deny": [{"rule": "run_command(rm *)", "reason": "消すのは人が行う"}]}}
```

見どころ:

| 情報 | 伝わり方 | 場所 | 照らした文 | 作る所 |
|---|---|---|---|---|
| 呼び出し1つに、tool の発言1つ | Ollama の欄 | 要求 2 の `messages` | 9 個 | [`ollama_messages._user`](../local_coding_agent/model/ollama_messages.py) |
| 道具が返した誤り（tool の発言に誤りの欄が無いので、文の頭の印） | ハーネスの枠 | 要求 2 の `messages[3].content` | `誤り: ファイルが無い: memo.txt` | [`ollama_messages._tool_message`](../local_coding_agent/model/ollama_messages.py)・[`read_file.run`](../local_coding_agent/tools/read_file.py) |
| 入力が定義に合わない | ハーネスの枠 | 要求 2 の `messages[4].content` | `誤り: 入力が定義に合わない: 必須の欄が無い: path` | [`tool_call.execute`](../local_coding_agent/loop/tool_call.py)・[`input_check.input_problem`](../local_coding_agent/tools/input_check.py) |
| 規則で拒んだ（合った規則） | ハーネスの枠 | 要求 2 の `messages[5].content` | `誤り: 規則で拒んだ: run_command(rm *)` | [`policy.denial`](../local_coding_agent/permissions/policy.py) |
| 利用者が規則に添えた理由 | ハーネスの枠 | 要求 2 の `messages[5].content` | `理由: 消すのは人が行う。` | [`policy.denial`](../local_coding_agent/permissions/policy.py) |
| 利用者が実行を拒んだ理由（問いへの答え） | ハーネスの枠 | 要求 2 の `messages[6].content` | `誤り: 利用者が実行を拒んだ。理由: 残しておきたい` | [`confirm.refusal`](../local_coding_agent/permissions/confirm.py) |
| コマンドの終了コード（1行目）と出力 | ハーネスの枠 | 要求 2 の `messages[7].content` | `終了コード: 0\n片付けた` | [`run_command.run`](../local_coding_agent/tools/run_command.py) |
| 知らない道具 | ハーネスの枠 | 要求 2 の `messages[8].content` | `誤り: 知らない道具: delete_file` | [`tool_call.execute`](../local_coding_agent/loop/tool_call.py) |

#### 要求 1

- `tools`: 場面 1 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 2 個。messages[0]（system の発言）は場面 1 と同じ

`messages[1]` から:

```json
[
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[1].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:30 (+09:00)
</metadata>
notes.txt を片付けて
```

#### 要求 2

- `tools`: 要求 1 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 9 個。要求 1 の 2 個の後に、7 個を足した

`messages[2]` から:

```json
[
  {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "id": "call_p4w8n1zb",
        "function": {
          "index": 0,
          "name": "read_file",
          "arguments": {
            "path": "memo.txt"
          }
        }
      },
      {
        "id": "call_t6c2v5rd",
        "function": {
          "index": 1,
          "name": "read_file",
          "arguments": {}
        }
      },
      {
        "id": "call_h9j3x7lm",
        "function": {
          "index": 2,
          "name": "run_command",
          "arguments": {
            "command": "rm notes.txt"
          }
        }
      },
      {
        "id": "call_b5q1s8ke",
        "function": {
          "index": 3,
          "name": "write_file",
          "arguments": {
            "path": "notes.txt",
            "content": "（空）"
          }
        }
      },
      {
        "id": "call_f2y6g4ua",
        "function": {
          "index": 4,
          "name": "run_command",
          "arguments": {
            "command": "echo 片付けた"
          }
        }
      },
      {
        "id": "call_n8d3r6wc",
        "function": {
          "index": 5,
          "name": "delete_file",
          "arguments": {
            "path": "notes.txt"
          }
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_name": "read_file",
    "tool_call_id": "call_p4w8n1zb",
    "content": "誤り: ファイルが無い: memo.txt"
  },
  {
    "role": "tool",
    "tool_name": "read_file",
    "tool_call_id": "call_t6c2v5rd",
    "content": "誤り: 入力が定義に合わない: 必須の欄が無い: path"
  },
  {
    "role": "tool",
    "tool_name": "run_command",
    "tool_call_id": "call_h9j3x7lm",
    "content": "誤り: 規則で拒んだ: run_command(rm *)（規則の * は任意の文字列を表す）。理由: 消すのは人が行う。利用者がこの操作を禁じている。同じ目的を、別のコマンドや道具で果たそうとしない。要るなら、利用者に尋ねる"
  },
  {
    "role": "tool",
    "tool_name": "write_file",
    "tool_call_id": "call_b5q1s8ke",
    "content": "誤り: 利用者が実行を拒んだ。理由: 残しておきたい"
  },
  {
    "role": "tool",
    "tool_name": "run_command",
    "tool_call_id": "call_f2y6g4ua",
    "content": "⟨文 1⟩"
  },
  {
    "role": "tool",
    "tool_name": "delete_file",
    "tool_call_id": "call_n8d3r6wc",
    "content": "誤り: 知らない道具: delete_file（使える道具: read_file, list_directory, write_file, edit_file, run_command）"
  }
]
```

⟨文 1⟩（`messages[7].content`）:

```text
終了コード: 0
片付けた
```

### 4. 自作のコマンド

自作のコマンドのファイルを置き、/fix で呼ぶ。ハーネスがファイルの本文に引数を入れ、依頼の発言として送る。呼んだ行は `<metadata>` の枠に入る。

打つ行（上から順に）:

1. `/fix test_a.py`

作業ディレクトリに置くファイル `.local-coding-agent/commands/fix.md`:

```text
---
description: テストを走らせ、失敗していれば直す
---

テストを走らせ、失敗していれば直せ。対象: $ARGUMENTS
```

見どころ:

| 情報 | 伝わり方 | 場所 | 照らした文 | 作る所 |
|---|---|---|---|---|
| 呼んだコマンドの行 | ハーネスの枠 | 要求 1 の `messages[1].content` | `コマンド: /fix test_a.py` | [`messages.metadata_text`](../local_coding_agent/model/messages.py) |
| コマンドのファイルの本文（$ARGUMENTS に引数を入れたもの） | そのままの文 | 要求 1 の `messages[1].content` | `テストを走らせ、失敗していれば直せ。対象: test_a.py` | [`custom.expand`](../local_coding_agent/commands/custom.py) |
| コマンドのファイルの前付け（description） | 送らない | 要求 1 の `messages[1].content` | `description` を含まない | [`custom.split_front_matter`](../local_coding_agent/commands/custom.py) |
| 自作のコマンドの一覧と説明 | 送らない | 要求 1 の `messages[0].content` | `テストを走らせ、失敗していれば直す` を含まない | [`system_prompt.build_system_prompt`](../local_coding_agent/context/system_prompt.py) |
| 「コマンド: 」の行の、モデルへの説明 | そのままの文 | 要求 1 の `messages[0].content` | `「コマンド: 」の行があれば` | [`system_prompt.read_instructions`](../local_coding_agent/context/system_prompt.py) |

#### 要求 1

- `tools`: 場面 1 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 2 個。messages[0]（system の発言）は場面 1 と同じ

`messages[1]` から:

```json
[
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[1].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:30 (+09:00)
コマンド: /fix test_a.py
</metadata>
テストを走らせ、失敗していれば直せ。対象: test_a.py
```

### 5. スキル（モデルが読み込む）

スキルを置き、依頼を打つ。system prompt にスキルの一覧が入り、道具に load_skill が加わる。モデルが load_skill を呼ぶと、スキルの中身が道具の結果として入る。

打つ行（上から順に）:

1. `convert.py をレビューして`

作業ディレクトリに置くファイル `.local-coding-agent/skills/review/SKILL.md`:

```text
---
description: コードを読み、観点ごとに問題を挙げる。引数は読むファイル
---

$ARGUMENTS を読み、checklist.md の観点ごとに、当てはまる所を挙げよ。
```

作業ディレクトリに置くファイル `.local-coding-agent/skills/review/checklist.md`:

```text
- 誤り
- 名前
```

見どころ:

| 情報 | 伝わり方 | 場所 | 照らした文 | 作る所 |
|---|---|---|---|---|
| 「# スキル」の節と、読み込み方の案内 | ハーネスの枠 | 要求 1 の `messages[0].content` | `# スキル` | [`catalog.skills_section`](../local_coding_agent/skills/catalog.py) |
| スキルの名前と説明 | ハーネスの枠 | 要求 1 の `messages[0].content` | `- review: コードを読み、観点ごとに問題を挙げる。引数は読むファイル` | [`catalog.skills_section`](../local_coding_agent/skills/catalog.py) |
| load_skill の道具（スキルがあるときだけ足す） | Ollama の欄 | 要求 1 の `tools` | 6 個 | [`__main__.main`](../local_coding_agent/__main__.py) |
| 読み込めるスキルの名前 | ハーネスの値 | 要求 1 の `tools[5].function.parameters.properties.name.enum` | `["review"]` | [`load_skill.definition`](../local_coding_agent/tools/load_skill.py) |
| スキルの本文（$ARGUMENTS に引数を入れたもの） | そのままの文 | 要求 2 の `messages[3].content` | `convert.py を読み、checklist.md の観点ごとに` | [`content.skill_text`](../local_coding_agent/skills/content.py) |
| スキルのディレクトリと、付いているファイルの一覧 | ハーネスの枠 | 要求 2 の `messages[3].content` | `付いているファイル（要るときに read_file で読む）:\n- .local-coding-agent/skills/review/checklist.md` | [`content.skill_text`](../local_coding_agent/skills/content.py) |
| スキルの中身は、load_skill の結果 | Ollama の欄 | 要求 2 の `messages[3].tool_name` | `load_skill` | [`ollama_messages._tool_message`](../local_coding_agent/model/ollama_messages.py) |

#### 要求 1

- `tools`: 6 個（read_file・list_directory・write_file・edit_file・run_command・load_skill）。場面 1 の 5 個の後に、1 個を足した
- `messages`: 2 個。messages[0]（system の発言）は、場面 1 の content に文を足したもの

`tools[5]` から:

```json
[
  {
    "type": "function",
    "function": {
      "name": "load_skill",
      "description": "スキル（作業ごとの手順書）を読み込み、中身を返す。使えるスキルは、指示の「# スキル」の節にある。依頼がスキルの説明に合えば、作業を始める前に呼ぶ。",
      "parameters": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "enum": [
              "review"
            ],
            "description": "スキルの名前"
          },
          "arguments": {
            "type": "string",
            "description": "スキルに渡す引数（本文の $ARGUMENTS に入る）。スキルの説明に引数の案内があれば渡す"
          }
        },
        "required": [
          "name"
        ]
      }
    }
  }
]
```

`messages[0].content` は、場面 1 の content の後に、改行 2 つを挟んで、次を足したもの:

```text
# スキル

スキルは、作業ごとの手順書である。下に、作業ディレクトリに置かれたスキルの名前と説明を並べる。依頼がスキルの説明に合えば、作業を始める前に load_skill の道具でそのスキルを読み込み、本文の手順に従う。合うスキルが無ければ、読み込まない。

- review: コードを読み、観点ごとに問題を挙げる。引数は読むファイル
```

`messages[1]` から:

```json
[
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[1].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:30 (+09:00)
</metadata>
convert.py をレビューして
```

#### 要求 2

- `tools`: 要求 1 と同じ 6 個（read_file・list_directory・write_file・edit_file・run_command・load_skill）
- `messages`: 4 個。要求 1 の 2 個の後に、2 個を足した

`messages[2]` から:

```json
[
  {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "id": "call_m6v1c8hs",
        "function": {
          "index": 0,
          "name": "load_skill",
          "arguments": {
            "name": "review",
            "arguments": "convert.py"
          }
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_name": "load_skill",
    "tool_call_id": "call_m6v1c8hs",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[3].content`）:

```text
convert.py を読み、checklist.md の観点ごとに、当てはまる所を挙げよ。

スキルのディレクトリ: .local-coding-agent/skills/review/（本文の中の相対パスは、ここからのもの）
付いているファイル（要るときに read_file で読む）:
- .local-coding-agent/skills/review/checklist.md
```

### 6. スキル（利用者が /<名前> で呼ぶ）

スキルを /review で呼ぶ。ハーネスが、load_skill の結果と同じ中身を、依頼の発言として送る。呼んだ行は `<metadata>` の枠に入る。

打つ行（上から順に）:

1. `/review convert.py`

作業ディレクトリに置くファイル `.local-coding-agent/skills/review/SKILL.md`:

```text
---
description: コードを読み、観点ごとに問題を挙げる。引数は読むファイル
---

$ARGUMENTS を読み、checklist.md の観点ごとに、当てはまる所を挙げよ。
```

作業ディレクトリに置くファイル `.local-coding-agent/skills/review/checklist.md`:

```text
- 誤り
- 名前
```

見どころ:

| 情報 | 伝わり方 | 場所 | 照らした文 | 作る所 |
|---|---|---|---|---|
| 呼んだスキルの行 | ハーネスの枠 | 要求 1 の `messages[1].content` | `スキル: /review convert.py` | [`messages.metadata_text`](../local_coding_agent/model/messages.py) |
| スキルの中身（モデルが読み込むときと同じ文） | そのままの文 | 要求 1 の `messages[1].content` | `convert.py を読み、checklist.md の観点ごとに` | [`repl._send_skill`](../local_coding_agent/cli/repl.py)・[`content.skill_text`](../local_coding_agent/skills/content.py) |
| 「スキル: 」の行の、モデルへの説明（読み込み直さない） | そのままの文 | 要求 1 の `messages[0].content` | `そのスキルを load_skill で読み込み直さない` | [`system_prompt.read_instructions`](../local_coding_agent/context/system_prompt.py) |

#### 要求 1

- `tools`: 6 個（read_file・list_directory・write_file・edit_file・run_command・load_skill）。場面 1 の 5 個の後に、1 個を足した
- `messages`: 2 個。messages[0]（system の発言）は、場面 1 の content に文を足したもの

`tools[5]` から:

```json
[
  {
    "type": "function",
    "function": {
      "name": "load_skill",
      "description": "スキル（作業ごとの手順書）を読み込み、中身を返す。使えるスキルは、指示の「# スキル」の節にある。依頼がスキルの説明に合えば、作業を始める前に呼ぶ。",
      "parameters": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "enum": [
              "review"
            ],
            "description": "スキルの名前"
          },
          "arguments": {
            "type": "string",
            "description": "スキルに渡す引数（本文の $ARGUMENTS に入る）。スキルの説明に引数の案内があれば渡す"
          }
        },
        "required": [
          "name"
        ]
      }
    }
  }
]
```

`messages[0].content` は、場面 1 の content の後に、改行 2 つを挟んで、次を足したもの:

```text
# スキル

スキルは、作業ごとの手順書である。下に、作業ディレクトリに置かれたスキルの名前と説明を並べる。依頼がスキルの説明に合えば、作業を始める前に load_skill の道具でそのスキルを読み込み、本文の手順に従う。合うスキルが無ければ、読み込まない。

- review: コードを読み、観点ごとに問題を挙げる。引数は読むファイル
```

`messages[1]` から:

```json
[
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[1].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:30 (+09:00)
スキル: /review convert.py
</metadata>
convert.py を読み、checklist.md の観点ごとに、当てはまる所を挙げよ。

スキルのディレクトリ: .local-coding-agent/skills/review/（本文の中の相対パスは、ここからのもの）
付いているファイル（要るときに read_file で読む）:
- .local-coding-agent/skills/review/checklist.md
```

### 7. 組み込みのコマンド

依頼の間に、/help・/mode ask・/context を打ち、続けて依頼を打つ。その後 /clear を打ち、新しい依頼を打つ。組み込みのコマンドはハーネスの中で処理し、モデルを呼ばない。/mode で替えた許可のモードも送らない。

打つ行（上から順に）:

1. `こんにちは`
2. `/help`
3. `/mode ask`
4. `/context`
5. `続けて`
6. `/clear`
7. `新しい話`

見どころ:

| 情報 | 伝わり方 | 場所 | 照らした文 | 作る所 |
|---|---|---|---|---|
| /help・/mode・/context の行と出力（履歴にも入らない） | 送らない | 要求 2 の `messages` | 4 個 | [`repl.handle_line`](../local_coding_agent/cli/repl.py)・[`builtin.run_builtin`](../local_coding_agent/commands/builtin.py) |
| /clear の前の発言（履歴を空にする） | 送らない | 要求 3 の `messages` | 2 個 | [`builtin._clear`](../local_coding_agent/commands/builtin.py) |

#### 要求 1

- `tools`: 場面 1 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 2 個。messages[0]（system の発言）は場面 1 と同じ

`messages[1]` から:

```json
[
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[1].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:30 (+09:00)
</metadata>
こんにちは
```

#### 要求 2

- `tools`: 要求 1 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 4 個。要求 1 の 2 個の後に、2 個を足した

`messages[2]` から:

```json
[
  {
    "role": "assistant",
    "content": "こんにちは。"
  },
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[3].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:31 (+09:00)
</metadata>
続けて
```

#### 要求 3

- `tools`: 要求 2 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 2 個（要求 2 の続きではない）。messages[0]（system の発言）は要求 2 と同じ

`messages[1]` から:

```json
[
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[1].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:32 (+09:00)
</metadata>
新しい話
```

### 8. 止まった回の後の依頼

1回目は、道具の結果の後に Ctrl-C で止める。2回目は、道具の結果の後にモデルとの通信が切れる。どちらも、済んだ歩み（呼び出しと結果）までを履歴に残し、結果の発言の末尾に止まったことの知らせを足す。止まった要求（要求 2・要求 4）には応答が無い。

打つ行（上から順に）:

1. `notes.txt を読んで`
2. `もう一度読んで`
3. `どうなった`

作業ディレクトリに置くファイル `notes.txt`:

```text
買うもの: 牛乳
```

見どころ:

| 情報 | 伝わり方 | 場所 | 照らした文 | 作る所 |
|---|---|---|---|---|
| 止まった要求の応答は、履歴に足さない | 送らない | 要求 3 の `messages` | 6 個 | [`turn._stopped`](../local_coding_agent/loop/turn.py) |
| 止めた回の知らせ | ハーネスの枠 | 要求 3 の `messages[4].content` | `（利用者がこの回を途中で止めた）` | [`turn._stopped`](../local_coding_agent/loop/turn.py) |
| 知らせは、tool の発言の後の、別の user の発言になる | Ollama の欄 | 要求 3 の `messages[4].role` | `user` | [`ollama_messages._user`](../local_coding_agent/model/ollama_messages.py) |
| 誤りで止まった回の知らせ | ハーネスの枠 | 要求 5 の `messages[8].content` | `（誤りで、この回が途中で止まった）` | [`turn._stopped`](../local_coding_agent/loop/turn.py)・[`ollama_messages._user`](../local_coding_agent/model/ollama_messages.py) |

#### 要求 1

- `tools`: 場面 1 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 2 個。messages[0]（system の発言）は場面 1 と同じ

`messages[1]` から:

```json
[
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[1].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:30 (+09:00)
</metadata>
notes.txt を読んで
```

#### 要求 2

- `tools`: 要求 1 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 4 個。要求 1 の 2 個の後に、2 個を足した

`messages[2]` から:

```json
[
  {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "id": "call_e7u2k9pd",
        "function": {
          "index": 0,
          "name": "read_file",
          "arguments": {
            "path": "notes.txt"
          }
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_name": "read_file",
    "tool_call_id": "call_e7u2k9pd",
    "content": "     1\t買うもの: 牛乳"
  }
]
```

#### 要求 3

- `tools`: 要求 2 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 6 個。要求 2 の 4 個の後に、2 個を足した

`messages[4]` から:

```json
[
  {
    "role": "user",
    "content": "（利用者がこの回を途中で止めた）"
  },
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[5].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:31 (+09:00)
</metadata>
もう一度読んで
```

#### 要求 4

- `tools`: 要求 3 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 8 個。要求 3 の 6 個の後に、2 個を足した

`messages[6]` から:

```json
[
  {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "id": "call_w3z8m5qt",
        "function": {
          "index": 0,
          "name": "read_file",
          "arguments": {
            "path": "notes.txt"
          }
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_name": "read_file",
    "tool_call_id": "call_w3z8m5qt",
    "content": "     1\t買うもの: 牛乳"
  }
]
```

#### 要求 5

- `tools`: 要求 4 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 10 個。要求 4 の 8 個の後に、2 個を足した

`messages[8]` から:

```json
[
  {
    "role": "user",
    "content": "（誤りで、この回が途中で止まった）"
  },
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[9].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:32 (+09:00)
</metadata>
どうなった
```

### 9. 2回目の依頼

依頼を2回打つ。モデルの API は会話を覚えないので、2回目の要求には、1回目の依頼と答え（推論を含む）も入る。

打つ行（上から順に）:

1. `1 + 1 は`
2. `それに 2 を足すと`

見どころ:

| 情報 | 伝わり方 | 場所 | 照らした文 | 作る所 |
|---|---|---|---|---|
| それまでの全ての発言 | Ollama の欄 | 要求 2 の `messages` | 4 個 | [`repl._send`](../local_coding_agent/cli/repl.py)・[`turn.run_turn`](../local_coding_agent/loop/turn.py) |
| 前の回の推論 | Ollama の欄 | 要求 2 の `messages[2].thinking` | `1 + 1 = 2。` | [`ollama_messages._assistant`](../local_coding_agent/model/ollama_messages.py) |
| 前の回の答え | そのままの文 | 要求 2 の `messages[2].content` | `2 です。` | [`ollama_messages._assistant`](../local_coding_agent/model/ollama_messages.py) |
| 発言ごとの送った時刻 | ハーネスの枠 | 要求 2 の `messages[3].content` | `送った時刻: 2026-10-24 15:31 (+09:00)` | [`messages.metadata_text`](../local_coding_agent/model/messages.py) |

#### 要求 1

- `tools`: 場面 1 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 2 個。messages[0]（system の発言）は場面 1 と同じ

`messages[1]` から:

```json
[
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[1].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:30 (+09:00)
</metadata>
1 + 1 は
```

#### 要求 2

- `tools`: 要求 1 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 4 個。要求 1 の 2 個の後に、2 個を足した

`messages[2]` から:

```json
[
  {
    "role": "assistant",
    "content": "2 です。",
    "thinking": "1 + 1 = 2。"
  },
  {
    "role": "user",
    "content": "⟨文 1⟩"
  }
]
```

⟨文 1⟩（`messages[3].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:31 (+09:00)
</metadata>
それに 2 を足すと
```

### 10. 指示の差し替え（--system-prompt-file）

指示の部分を、ファイルの中身に差し替えて起動する。環境の節は残り、既定の指示（ハーネスが入れる情報の説明を含む）は送らない。

打つ行（上から順に）:

1. `こんにちは`

起動の引数（`--model` と `--directory` のほか）: `--system-prompt-file <作業ディレクトリ>/short.md`

作業ディレクトリに置くファイル `short.md`:

```text
あなたは、短く答える。
```

見どころ:

| 情報 | 伝わり方 | 場所 | 照らした文 | 作る所 |
|---|---|---|---|---|
| 指示（ファイルの中身） | そのままの文 | 要求 1 の `messages[0].content` | `あなたは、短く答える。` | [`system_prompt.read_instructions`](../local_coding_agent/context/system_prompt.py) |
| 環境の節は残る | ハーネスの枠 | 要求 1 の `messages[0].content` | `# 環境` | [`system_prompt.build_system_prompt`](../local_coding_agent/context/system_prompt.py)・[`environment.environment_section`](../local_coding_agent/context/environment.py) |
| 既定の指示 | 送らない | 要求 1 の `messages[0].content` | `# ハーネスが入れる情報` を含まない | [`system_prompt.read_instructions`](../local_coding_agent/context/system_prompt.py) |

#### 要求 1

- `tools`: 場面 1 と同じ 5 個（read_file・list_directory・write_file・edit_file・run_command）
- `messages`: 2 個

`messages`:

```json
[
  {
    "role": "system",
    "content": "⟨文 1⟩"
  },
  {
    "role": "user",
    "content": "⟨文 2⟩"
  }
]
```

⟨文 1⟩（`messages[0].content`）:

```text
あなたは、短く答える。

# 環境

- 作業ディレクトリ: /work/project
- 作業ディレクトリは git のリポジトリの中か: はい
- OS: macOS 15.6（Darwin 24.6.0）
```

⟨文 2⟩（`messages[1].content`）:

```text
<metadata>
送った時刻: 2026-10-24 15:30 (+09:00)
</metadata>
こんにちは
```

## 作る所

見どころの「作る所」の、生成したときのコードの行である。

- [`ollama_messages.chat_request_body`](../local_coding_agent/model/ollama_messages.py#L32)
- [`ollama_messages.to_ollama_messages`](../local_coding_agent/model/ollama_messages.py#L62)
- [`system_prompt.read_instructions`](../local_coding_agent/context/system_prompt.py#L59)
- [`environment.environment_section`](../local_coding_agent/context/environment.py#L46)
- [`system_prompt.build_system_prompt`](../local_coding_agent/context/system_prompt.py#L70)
- [`ollama_messages.to_ollama_tools`](../local_coding_agent/model/ollama_messages.py#L47)
- [`turn.run_turn`](../local_coding_agent/loop/turn.py#L40)
- [`messages.metadata_text`](../local_coding_agent/model/messages.py#L125)
- [`ollama_messages._assistant`](../local_coding_agent/model/ollama_messages.py#L94)
- [`ollama_messages._tool_call`](../local_coding_agent/model/ollama_messages.py#L109)
- [`ollama_messages._user`](../local_coding_agent/model/ollama_messages.py#L114)
- [`ollama_messages._tool_message`](../local_coding_agent/model/ollama_messages.py#L127)
- [`ollama_messages._tool_names`](../local_coding_agent/model/ollama_messages.py#L77)
- [`read_file.run`](../local_coding_agent/tools/read_file.py#L46)
- [`tool_call.execute`](../local_coding_agent/loop/tool_call.py#L84)
- [`input_check.input_problem`](../local_coding_agent/tools/input_check.py#L26)
- [`policy.denial`](../local_coding_agent/permissions/policy.py#L97)
- [`confirm.refusal`](../local_coding_agent/permissions/confirm.py#L47)
- [`run_command.run`](../local_coding_agent/tools/run_command.py#L49)
- [`custom.expand`](../local_coding_agent/commands/custom.py#L95)
- [`custom.split_front_matter`](../local_coding_agent/commands/custom.py#L77)
- [`catalog.skills_section`](../local_coding_agent/skills/catalog.py#L112)
- [`__main__.main`](../local_coding_agent/__main__.py#L83)
- [`load_skill.definition`](../local_coding_agent/tools/load_skill.py#L19)
- [`content.skill_text`](../local_coding_agent/skills/content.py#L18)
- [`repl._send_skill`](../local_coding_agent/cli/repl.py#L107)
- [`repl.handle_line`](../local_coding_agent/cli/repl.py#L51)
- [`builtin.run_builtin`](../local_coding_agent/commands/builtin.py#L37)
- [`builtin._clear`](../local_coding_agent/commands/builtin.py#L54)
- [`turn._stopped`](../local_coding_agent/loop/turn.py#L91)
- [`repl._send`](../local_coding_agent/cli/repl.py#L132)
