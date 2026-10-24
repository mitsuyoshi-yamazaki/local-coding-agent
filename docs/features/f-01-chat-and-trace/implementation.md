# F-01 チャットと走行の記録: 実装した仕様と仕組み

[実装前の仕様](spec.md) に対して、実際に実装した仕様と、その仕組みである。

## 使い方

```sh
.venv/bin/python -m local_coding_agent --model qwen3.5:9b
```

起動すると、走行の記録のファイルの場所を表示し、`> ` で依頼を待つ。依頼を1行打つと、応答が流れて表示され、最後に数値の1行が出る。Ctrl-D で終える。

```text
走行の記録: traces/20261024-153012.jsonl
> 私は山田です
はい、山田さん。
[入力 12 トークン・出力 5 トークン・最初の文字まで 0.81 秒・全体 1.20 秒]
>
```

## 仕組み

1回の依頼は、次の順で流れる。

1. `cli/repl.py` が1行を読み、それまでの履歴の末尾に、利用者の発言として足す
2. `model/ollama.py` が、会話の全体を `/api/chat` の形に変え、送る JSON を作る
3. `cli/repl.py` が、送る JSON の全体を走行の記録に書く
4. `model/ollama.py` が JSON を送り、流れてくる NDJSON を1行ずつ読んで、本文の断片と終わりの知らせに変える
5. `cli/repl.py` が、本文の断片を届いたそばから表示する。最初の断片が届いた時刻と、終わった時刻を測る
6. `cli/repl.py` が、応答を走行の記録に書き、数値の1行を表示する
7. 応答が終わりまで届いたら、利用者の発言とモデルの発言を履歴に足す。止めた回と誤りの回は足さない

モデルの API は会話の状態を持たない。2回目の依頼では、1回目の依頼と応答を含めた会話の全体を送る。履歴を持っているのは `cli/repl.py` の `run` の中の変数 `history` だけである。

### 会話の形

`model/messages.py` は、会話を Claude の Messages API と同じ形で持つ。1つの発言（`Message`）は、役割（`user` か `assistant`）と、塊（content block）の並びである。F-01 の塊は本文（`TextBlock`）だけである。

Ollama の `/api/chat` は、発言を役割と本文の文字列で受ける。`model/ollama.py` の `to_ollama_messages` が、送る直前に本文の塊をつないで1つの文字列にする。

### REPL とモデルの間

`cli/repl.py` は Ollama の形を知らない。`model/chat.py` の `ChatModel` の2つの操作だけを使う。

| 操作 | 何をするか |
|---|---|
| `build_request(messages)` | 会話の全体から、送り先と送る JSON の全体（`ChatRequest`）を作る |
| `stream(request)` | 送って、応答を本文の断片（`TextDelta`）と終わりの知らせ（`Done`）の並びとして返す。繋がらない・誤りが返ったときは `ModelError` を投げる |

`model/ollama.py` の `OllamaChat` が、Ollama に向けてこの2つを実装する。テストでは、決めた台本どおりに返す偽物（`tests/fakes.py` の `ScriptedModel`）に差し替える。

### 走行の記録

起動ごとに1つ、`traces/<起動の時刻>.jsonl` を作る。1行に1件で、どの件にも書いた時刻（`time`）が付く。

| 件 | 欄 |
|---|---|
| 要求（`"type": "request"`） | `turn`（何回目か）・`url`・`body`（送った JSON の全体） |
| 応答（`"type": "response"`） | `turn`・`status`（`done`・`cancelled`・`error`）・`text`（本文。止めた・誤りの回は途中まで）・`done_reason`・`model_stats`（Ollama が最後の行で返したトークン数と時間。時間はナノ秒）・`measured`（手元で測った `first_token_seconds` と `total_seconds`）・`error` |

`model_stats` に入る欄は `prompt_eval_count`（入力のトークン数）・`eval_count`（出力のトークン数）・`total_duration`・`load_duration`・`prompt_eval_duration`・`eval_duration` のうち、Ollama が返したものである。

## 実装前の仕様との違い

| 点 | 実装前の仕様 | 実装 |
|---|---|---|
| ファイル | `model/` は `messages.py` と `ollama.py` | `model/chat.py` を足した。REPL とモデルの間の形（`ChatModel`・`ChatRequest`・`TextDelta`・`Done`・`ModelError`）を、Ollama に依らない場所に置くためである |
| 起動の表示 | 書いていない | 起動のときに、走行の記録のファイルの場所を表示する |
| 入力を待つ間の Ctrl-C | 書いていない | 何もせず、次の入力を待つ |
| 終わりの行が来ない応答 | 書いていない | `done` が `true` の行の前に応答が終わったら、誤りとして扱う（履歴に足さない） |
| JSON として読めない行 | 書いていない | 誤りとして扱う（履歴に足さない） |
| 記録のモデルの数値の欄の名前 | 「Ollama が返したトークン数と時間」 | `model_stats`。後で Ollama 以外の口を足しても同じ名前で使うため |

## ファイル

| ファイル | 行数の目安 | 中身 |
|---|---|---|
| `local_coding_agent/__main__.py` | 50 | 引数を読み、REPL を起動する |
| `local_coding_agent/cli/repl.py` | 150 | 入力・表示・履歴・走行の記録の中身 |
| `local_coding_agent/model/messages.py` | 40 | 会話の形 |
| `local_coding_agent/model/chat.py` | 50 | REPL とモデルの間の形 |
| `local_coding_agent/model/ollama.py` | 130 | `/api/chat` の形への変換・要求・NDJSON の読み取り・誤りの文 |
| `local_coding_agent/trace/writer.py` | 40 | 走行の記録の書き出し |
| `tests/` | 340 | 偽物（`fakes.py`）と、変換・読み取り・REPL・記録のテスト |
