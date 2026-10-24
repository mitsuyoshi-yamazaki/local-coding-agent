# F-03 道具の呼び出しとループ: 実装した仕様と仕組み

[実装前の仕様](spec.md) に対して、実際に実装した仕様と、その仕組みである。

## 使い方

起動は F-02 と同じである。依頼を打つと、モデルが道具を呼ぶ間、モデルの呼び出しと道具の実行が交互に表示される（数値は例）。

```text
> tasks/f-03-tool-loop/project のサーバは、何番のポートで待ち受けるか

[入力 1021 トークン・出力 38 トークン・最初の文字まで 2.10 秒・全体 2.64 秒]
[道具] read_file {"path": "tasks/f-03-tool-loop/project/README.md"}
→ 6 行

[入力 1160 トークン・出力 41 トークン・最初の文字まで 0.95 秒・全体 1.52 秒]
[道具] read_file {"path": "tasks/f-03-tool-loop/project/config/server.toml"}
→ 8 行
8642 番で待ち受ける（config/server.toml の [server] の port）。
[入力 1290 トークン・出力 25 トークン・最初の文字まで 0.88 秒・全体 1.10 秒]
>
```

- モデルを1回呼ぶたびに、本文を流して表示し、数値の1行を出す。道具を呼ぶだけの応答は本文が空なので、数値の1行の前に空の行が出る
- 道具を実行するたびに、呼び出しを1行（`[道具] <名前> <入力の JSON>`）、結果を1行で出す。結果の1行は、モデルに渡した結果の文の行数（`→ 6 行`）か、誤りの文（`→ 誤り: ファイルが無い: x`）である。行数には、読み残しの知らせの行も入る
- 変更を伴う道具は、呼び出しの1行の後に `実行してよいか [y/N]: ` と問う。既定の道具（`read_file`・`list_directory`）は読むだけなので、問いは出ない
- **Ctrl-C**: 応答の途中・道具の実行の途中・問いの途中のどこで押しても、その回の全体（依頼・道具の呼び出しと結果・応答）を履歴に足さない

## 仕組み

### ループ

`loop/turn.py` の `run_turn` が、1回の依頼を処理する。

1. 利用者の依頼を、履歴の末尾に足す
2. `loop/model_call.py` の `call_model`: system prompt・道具の定義・会話の全体を送り、応答を流して表示する。応答の中の道具の呼び出しを集める
3. 応答を、モデルの発言（本文の塊と呼び出しの塊）として履歴に足す。呼び出しが無ければ、ここで終える
4. `loop/tool_call.py` の `run_tool_calls`: 呼び出しを順に1つずつ処理し、結果をまとめて1つの利用者の発言として履歴に足す。2. へ戻る

ループの回数に上限は無い。モデルが道具を呼び続ける限り回り、止めるのは人の Ctrl-C である。

`cli/repl.py` は、1行を受けて `run_turn` に渡し、返ってきた新しい履歴を持つ。履歴を持つのは、F-01 と同じく `cli/repl.py` の `run` の変数 `history` だけである。`run_turn` の中の `messages` は、その回の歩みを足していく下書きで、回が終わったときに新しい履歴として返る。止めた回と誤りの回は、下書きを捨てて元の履歴を返す。

`loop/session.py` の `Session` は、ループと REPL が使うもの（モデル・system prompt・道具の組・作業ディレクトリ・入力・出力・走行の記録・時計）をまとめる。`__main__.py` が起動のときに1度作る。

### 道具の呼び出しの処理

`loop/tool_call.py` の `execute` が、呼び出し1つを次の順で処理する。どこで止まっても、誤りの結果（`is_error` が真の `tool_result`）としてモデルに返し、ループは続ける。

| 順 | 見ること | 止まったときにモデルに返す結果 |
|---|---|---|
| 1 | その名前の道具があるか | `知らない道具: <名前>（使える道具: read_file, list_directory）` |
| 2 | 入力が、定義の入力の形（JSON Schema）に合うか（`tools/input_check.py`） | `入力が定義に合わない: <どこが合わないか>` |
| 3 | 変更を伴う道具なら、人が許すか（`permissions/confirm.py`） | `利用者が実行を拒んだ` |
| 4 | 道具を実行する。道具が `ToolError` を投げたら | 道具が書いた誤りの文 |

- **入力の照らし方**: 必須の欄（`required`）・欄の型（`type`）・数の下限（`minimum`）だけを見る。定義に無い欄は見ない。真偽値は数とみなさない（Python では `True` は `int` の一種だが、JSON では別の型である）。整数の欄は、小数点を持つ数（`10.0` など）を受けない
- **確かめる問い**: `y` か `yes`（大文字も可。前後の空白は除く）なら許す。それ以外の答えと、入力の終わり（Ctrl-D）は拒んだとする。問うのは、道具の印 `changes` が真の道具だけである。既定の道具は印を持たないので、問いの仕組みは、印のある偽物の道具を使うテストで確かめている
- **拒んだとき**: その回を止めず、拒まれたことを結果としてモデルに返す。モデルは、それを読んでやり方を変えうる。拒む理由を打つ欄は無い

Claude Code は、Manual のモードでは、ファイルの変更とコマンドの実行の前に問う。読むだけの道具（ファイルを読む・Grep）は、作業ディレクトリの中なら問わない（出典）。

### 道具

道具は `tools/` に1つを1ファイルで置く。道具（`tools/tool.py` の `Tool`）は、モデルに渡す定義（`model/chat.py` の `ToolDefinition`: 名前・説明・入力の形）と、変更を伴うかの印（`changes`）と、実行する関数（`run`）からなる。実行する関数は、入力と作業ディレクトリを受けて結果の文を返し、誤りは `ToolError` で知らせる。既定の組は `tools/default.py` の `DEFAULT_TOOLS` で、`__main__.py` が `Session` に渡す。

パスは、作業ディレクトリ（起動したディレクトリ。`Session.cwd`）からの相対パスか、絶対パスで受ける。作業ディレクトリの外も読める。作るエージェントは、素の状態では全てを許すからである。

**`read_file`**（`tools/read_file.py`）

| 入力 | 型 | 意味 |
|---|---|---|
| `path` | 文字列。必須 | 読むファイル |
| `offset` | 1 以上の整数 | 何行目から読むか。既定は 1 |
| `limit` | 1 以上の整数 | 何行読むか。既定は 2000 |

- 結果は `cat -n` と同じ形で返す。行番号を6桁で右に寄せ、タブを挟んで行を置く（例: `     1\t# 在庫の帳簿`）
- 2000 字を超える行は、2000 字で切り、`…（この行は <字数> 字。2000 字で切った）` を添える
- 読み残した行があれば、空の行を挟んで `（全体は <行数> 行。続きは、offset に <次の行> を渡して読む）` を末尾に足す
- 空のファイルは `（空のファイル）` を返す
- 誤り: ファイルが無い・ディレクトリである・UTF-8 として読めない・`offset` が行数を超えている・パスとして使えない（NUL の字を含むなど）・そのほか読めない（権限など）
- 改行は、Python の `read_text` が `\n` に揃える（`\r\n` も `\n` になる）。行は `\n` で分ける
- 結果の大きさを抑えるのは、行数（`limit`）と1行の長さ（2000 字）だけである。結果の総量の上限は無く、1回で最大 2000 行 × 2000 字を返しうる。ファイルは、読む範囲によらず全体を読み込む

**`list_directory`**（`tools/list_directory.py`）

| 入力 | 型 | 意味 |
|---|---|---|
| `path` | 文字列 | 見るディレクトリ。既定は作業ディレクトリ |

- 結果は、中の名前を1行に1つ、名前の順（Python の文字列の順）に並べる。ディレクトリには、名前の末尾に `/` を付ける。点で始まる名前も出す
- 空のディレクトリは `（空のディレクトリ）` を返す
- 誤り: ディレクトリが無い・ディレクトリではなくファイルである・パスとして使えない・そのほか見られない

Claude Code の Read の道具も、行番号を付けて返し、`offset` と `limit` で大きなファイルを分けて読む（出典）。

### 会話の形

`model/messages.py` に、Claude の Messages API と同じ塊を2つ足した。

| 塊 | 欄 | 入る発言 |
|---|---|---|
| `ToolUseBlock`（`tool_use`） | `id`・`name`・`input` | モデルの発言。本文の塊の後に置く。本文が空なら、呼び出しの塊だけになる |
| `ToolResultBlock`（`tool_result`） | `tool_use_id`・`content`（文）・`is_error` | 利用者の発言。1回の応答の呼び出しの結果を、まとめて1つの発言にする（`tool_results`） |

結果の塊は、`tool_use_id` で、どの呼び出しの結果かを示す。呼び出しの `id` は、モデルの API が付けたものを使い、付いていなければ `loop/model_call.py` が `call_<回>_<歩み>_<順>` を付ける（例: 1回目の依頼で、2回目に呼んだモデルの、最初の呼び出しなら `call_1_2_0`）。

1回の依頼の後の履歴は、たとえば次の並びになる。

| 発言 | 塊 |
|---|---|
| 利用者 | 本文（依頼） |
| モデル | 呼び出し（`read_file`、id は `call_1_1_0`） |
| 利用者 | 結果（`call_1_1_0` の結果） |
| モデル | 呼び出し（`read_file`、id は `call_1_2_0`） |
| 利用者 | 結果（`call_1_2_0` の結果） |
| モデル | 本文（答え） |

### Ollama の形への変換

`model/ollama_messages.py` が、送る直前に `/api/chat` の形へ変える。

| このリポジトリの形 | `/api/chat` の形 |
|---|---|
| 道具の定義 | 要求の `tools` の1つ。`type` が `function` で、`function` に `name`・`description`・`parameters`（`input_schema` そのまま）。道具が無ければ `tools` を送らない |
| モデルの発言の `tool_use` | その発言の `tool_calls` の1つ。`id` と、`function` に `index`（その発言の中の順）・`name`・`arguments`（`input` そのまま） |
| 利用者の発言の `tool_result` | 結果ごとに、`role` が `tool` の発言1つ。`tool_name`・`tool_call_id`・`content` |
| `is_error` | 欄が無い。誤りの結果は、`content` の先頭に `誤り: ` を足す |

- `tool` の発言は道具の名前（`tool_name`）を持つが、Messages API の結果の塊は持たない。変換の層が、会話の中の呼び出しの塊から、id で名前を引く
- 利用者の発言が、結果の塊の後に本文の塊も持つときは、`tool` の発言の後に `user` の発言を置く。ループが作る結果の発言は、結果の塊だけを持つ

2回目にモデルを呼ぶときの `messages` は、次の形になる（中身は略した）。

```json
[
  {"role": "system", "content": "あなたは、利用者の端末で動くコーディングエージェントである。…"},
  {"role": "user", "content": "<metadata>\n送った時刻: 2026-10-24 15:30 (+09:00)\n</metadata>\ntasks/f-03-tool-loop/project のサーバは、何番のポートで待ち受けるか"},
  {"role": "assistant", "content": "",
   "tool_calls": [{"id": "call_1_1_0",
                   "function": {"index": 0, "name": "read_file",
                                "arguments": {"path": "tasks/f-03-tool-loop/project/README.md"}}}]},
  {"role": "tool", "tool_name": "read_file", "tool_call_id": "call_1_1_0",
   "content": "     1\t# 在庫の帳簿\n     2\t\n…"}
]
```

応答の読み取り（`model/ollama.py` の `read_stream`）:

- 流れてくる行の `message.tool_calls` を、どの行に載っていても集め、1つずつ呼び出し（`model/chat.py` の `ToolCall`）にする。本文の断片と同じく、届いた順に返す
- 呼び出しの形が読めない（`function` や `name` が無い・`arguments` が object でない）ときは、モデルの誤り（`ModelError`）として扱う。その回は履歴に足さない
- 推論の文（`message.thinking`）は、F-01 と同じく捨てる。表示もせず、履歴にも戻さない

### system prompt

`context/system_prompt.py` の既定の指示を、次のように直した。

| 節 | 中身 |
|---|---|
| できること | ファイルを読む道具（`read_file`）と、ディレクトリの中身を見る道具（`list_directory`）を持つ。ファイルを書く・編集する道具と、コマンドを走らせる道具は持たない。読んでいないファイルの中身を、読んだように答えない |
| 道具の使い方（足した） | ファイルの中身やディレクトリの様子が要るときは、推測せずに道具で確かめる。パスは相対パスか絶対パスで渡す。ループの中にいるので、結果を読んでから続けて呼んでよく、一度に複数を呼んでもよい。答えに要ることが揃ったら、道具を呼ばずに答える。長いファイルは `offset` と `limit` で続きを読む |
| ハーネスが入れる情報 | 「# 環境」の節と `<metadata>` に、道具の結果を足した。誤りの結果は `誤り: ` で始まることを書く |

道具の定義（名前・説明・入力の形）は、system prompt ではなく、要求の `tools` で渡る。Ollama は、モデルごとの雛形で、道具の定義も1つの文に組み立ててからモデルに渡す（[F-02 の仕組み](../f-02-system-prompt/implementation.md#モデルに届く文)）。

Ollama の文書は、モデルに、ループの中にいて道具を何度も呼べることを伝えるとよい、と書く（出典）。

### 走行の記録

F-01 の記録（[欄](../f-01-chat-and-trace/implementation.md#走行の記録)）に、欄と件を足した。

| 件 | 欄 |
|---|---|
| 要求（`"type": "request"`） | F-01 の欄に、`step`（その回の中で何回目にモデルを呼んだか。1 から） |
| 応答（`"type": "response"`） | F-01 の欄に、`step` と `tool_calls`（呼び出しの並び。1つは `id`・`name`・`input`。止めた・誤りの回は空） |
| 道具（`"type": "tool"`） | `turn`・`step`（呼び出しを返した応答の `step`）・`id`・`name`・`input`・`confirmed`（問わなかったら `null`、許したら `true`、拒んだら `false`）・`result`（モデルに返した文）・`is_error`・`seconds`（道具の関数を実行した時間。実行しなかったら `null`） |

1回の依頼は、`request`（step 1）→ `response`（step 1）→ `tool` →…→ `request`（step 2）→ … と並び、`tool_calls` が空の `response` で終わる。モデルを何回呼んで答えたかは、最後の `response` の `step` で分かる。

- `measured` の `first_token_seconds` は、本文の断片か道具の呼び出しの、どちらかが最初に届くまでの時間である
- 道具の実行の途中・問いの途中で Ctrl-C を押した回は、その呼び出しの `tool` の件を書かない。記録は、呼び出しを返した `response` の件で途切れる

## 試すための材料

`tasks/f-03-tool-loop/project/` に、小さなプロジェクトを置く。リポジトリの根で起動し、次の問いを出す。答えは、モデルが材料と一緒に読まないよう、`tasks/` の下に置かない。

| ファイル | 中身 |
|---|---|
| `README.md` | 設定が `config/server.toml` にあり、点検の記録が `logs/inspection.log` にあること |
| `config/server.toml` | 待ち受けのアドレス・ポート（`8642`）・帳簿のファイルの場所 |
| `logs/inspection.log` | 2400 行。どの行も `pump-A: ok` の形で、A・B・C を順に繰り返す。2317 行目だけが `pump-A: pressure low (abnormal)` |

| 問い | 答え | 見ること |
|---|---|---|
| `tasks/f-03-tool-loop/project のサーバは、何番のポートで待ち受けるか` | 8642 | README から設定のファイルを辿るか。道具を何回呼び、何回目のモデルの呼び出しで答えたか |
| `tasks/f-03-tool-loop/project/logs/inspection.log で、ok ではない行は何行目にあり、何が書いてあるか` | 2317 行目・`pump-A: pressure low (abnormal)` | 1回目の `read_file` は 1〜2000 行と読み残しの知らせを返す。`offset` に 2001 を渡して続きを読むか |
| `tasks/f-03-tool-loop/project/docs/design.md を読んで要約せよ` | そのファイルは無い | 誤りの結果を読んで、どう答えるか |

2つ目の問いの1回目の `read_file` の結果は、2002 行・36038 字である（実測。続きの 2001〜2400 行は 400 行・7220 字）。文脈の長さが足りないと、結果が入りきらない。

## 実装前の仕様との違い

仕様の振る舞いは変えていない。仕様に書いていなかった細部は次のとおり。

| 点 | 実装 |
|---|---|
| ファイル | 変換の層を `model/ollama_messages.py` に分けた（`model/ollama.py` は接続と応答の読み取り）。`loop/` は `turn.py`（ループ）・`model_call.py`（モデルを1回呼ぶ）・`tool_call.py`（道具を実行する）・`session.py`（`Session`）に分けた。`Session` は `cli/repl.py` から `loop/session.py` へ移した。確かめる問いは `permissions/confirm.py` |
| 呼び出しの id | 付いていなければ `call_<回>_<歩み>_<順>` |
| `offset` が行数を超えるとき | 誤り `offset が行数を超えている（<パス> は <行数> 行）` |
| 空のディレクトリ | `（空のディレクトリ）` を返す |
| 結果の1行の行数 | モデルに渡した結果の文の行数（読み残しの知らせの行も数える） |
| 呼び出しの形が読めない応答 | モデルの誤りとして、その回を履歴に足さない |
| 入力の照らし方 | `required`・`type`・`minimum` だけを見る。定義に無い欄は見ない。真偽値を数とみなさない。整数の欄は `10.0` を受けない |
| パスとして使えない入力 | NUL の字を含むパスなどは、誤り `パスとして使えない: <パス>（<理由>）` |
| 誤りの結果の印 | 既定の指示の「ハーネスが入れる情報」に、誤りの結果が `誤り: ` で始まることを書いた |
| 既定の指示の「できること」 | 「ファイルの中身は、利用者が会話に貼ったものしか分からない」を除いた |
| 最初の文字までの時間 | 本文の断片か道具の呼び出しの、どちらかが最初に届くまで |
| 道具の実行の途中・問いの途中の Ctrl-C | `（止めた。この回は履歴に足さない）` を表示する。その呼び出しの `tool` の件は書かない |

## ファイル

| ファイル | 行数の目安 | 中身 |
|---|---|---|
| `local_coding_agent/loop/turn.py` | 50 | ループ（`run_turn`） |
| `local_coding_agent/loop/model_call.py` | 140 | モデルを1回呼び、応答を表示し、記録する。F-01 の `cli/repl.py` の `receive`・`summary` などを移した |
| `local_coding_agent/loop/tool_call.py` | 100 | 呼び出しを1つずつ処理し、表示し、記録する |
| `local_coding_agent/loop/session.py` | 30 | `Session` |
| `local_coding_agent/tools/tool.py` | 40 | 道具の形（`Tool`・`ToolError`）・名前で探す・パスを解く |
| `local_coding_agent/tools/input_check.py` | 70 | 入力を定義と照らす |
| `local_coding_agent/tools/read_file.py` | 100 | `read_file` |
| `local_coding_agent/tools/list_directory.py` | 60 | `list_directory` |
| `local_coding_agent/tools/default.py` | 10 | 既定の道具の組 |
| `local_coding_agent/permissions/confirm.py` | 30 | 実行の前に確かめる |
| `local_coding_agent/model/messages.py` | 100 | `tool_use`・`tool_result` の塊 |
| `local_coding_agent/model/chat.py` | 80 | 道具の定義・応答の中の呼び出し（`ToolCall`）・`build_request` が道具の定義を受ける |
| `local_coding_agent/model/ollama_messages.py` | 130 | `/api/chat` の形への変換 |
| `local_coding_agent/model/ollama.py` | 160 | 接続・応答の `tool_calls` の読み取り |
| `local_coding_agent/cli/repl.py` | 30 | 1行ずつ受けて、ループに渡す |
| `local_coding_agent/context/system_prompt.py` | 60 | 既定の指示 |
| `local_coding_agent/__main__.py` | 80 | 既定の道具の組と作業ディレクトリを `Session` に渡す |
| `tasks/f-03-tool-loop/project/` | | 試すための小さなプロジェクト |
| `tests/` | 1300 | 偽物と、変換・読み取り・道具・入力の照らし方・確かめる問い・ループ・起動・REPL のテスト |

## 出典

確かめた日は 2026-10-24。

- Ollama の Tool calling（`tools` の形・`role` が `tool` の発言と `tool_name`・`arguments` は object・ストリーミングでは全ての断片から `tool_calls` を集める・ループの中にいることをモデルに伝えるとよい）: https://docs.ollama.com/capabilities/tool-calling
- Ollama の API の型（発言の `tool_calls`・`tool_name`・`tool_call_id`、呼び出しの `id`、`function` の `index`・`name`・`arguments`）: https://github.com/ollama/ollama/blob/main/api/types.go
- Claude の Messages API の道具の呼び出し（`tool_use` の `id`・`name`・`input`、`tool_result` の `tool_use_id`・`content`・`is_error`、結果の塊は利用者の発言の先頭に置く、入力の誤りも結果として返す）: https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls
- Claude Code の Read の道具（行番号を付けて返す・`offset` と `limit`）: https://code.claude.com/docs/en/tools-reference
- Claude Code の許可（Manual のモードでは、ファイルの変更とコマンドは問い、読むだけの道具は作業ディレクトリの中なら問わない）: https://code.claude.com/docs/en/permissions
