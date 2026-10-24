# F-01 引き継ぎ

F-01 を実装したセッションから、人の問いに答えるセッションへの引き継ぎである。人が読む想定ではない。書き方は `.claude/rules/docs.md` の「handoff.md」。

F-01 は、worktree の運用を始める前に、main のセッションが仕様から実装まで行った。

## 進み具合

- 段: 実装が済み、人がコードを読んでいる（2026-10-24）。試すのは、人が Ollama を入れてモデルを取り込んでから
- branch: `main`
- commit: `5aedc79`（コードとテスト）・`08278a9`（`implementation.md`）・`30625e3`（README）
- テスト: 19件が通る。Ruff・mypy（strict）も通る
- Claude Code が確かめたこと: Ollama の無い状態で、`--help`・起動・誤りの表示・Ctrl-D での終わり・走行の記録の中身。sandbox が `localhost:11434` への接続を拒むので、誤りは「Operation not permitted」になる（人の端末では「Connection refused」などになるはず）
- 実物のモデルでは走らせていない（F-06 まで、実物のモデルで走らせるのは人だけ）

## 仕様を決めるときに人と話したこと

- 仕様の案を示したところ、持ち主は「まず F-1 の仕様を docs/ 以下へ記載せよ」と指示し、機能ごとのディレクトリ（`docs/features/f-NN-<機能名>/`）の形を決めた。名前の番号は2桁（`f-1` だと `f-10` が `f-2` より前に並ぶため。上流も同じ読み）
- 応答の途中の Ctrl-C で、その回を履歴に足さない案（採った）と、足して次の回に送る案（Claude Code に近い）を示した。持ち主は「この仕様で良い」と答えた
- 誰が書くか: 持ち主は「Claude Code が書き、人が読む」を選んだ

## 実装の全体像

### ファイル

| ファイル | 役目 | 主な名前 |
|---|---|---|
| `local_coding_agent/__main__.py` | 引数（`--model`・`--host`）を読み、`Session` を組み立てて `repl.run` を呼ぶ。起動時に走行の記録のパスを表示する | `main`・`parse_args`・`DEFAULT_HOST`・`TRACE_DIRECTORY` |
| `local_coding_agent/cli/repl.py` | REPL。履歴を持ち、1回ごとに要求を作って記録し、応答を流して表示し、結果を記録し、履歴を返す | `Session`・`Outcome`・`run`・`run_turn`・`receive`・`response_record`・`summary` |
| `local_coding_agent/model/messages.py` | 会話の形（Messages API に揃えた） | `Message`・`TextBlock`・`ContentBlock`・`Role`・`user_text`・`assistant_text` |
| `local_coding_agent/model/chat.py` | REPL とモデルの間の形。Ollama に依らない | `ChatModel`（Protocol）・`ChatRequest`・`TextDelta`・`Done`・`StreamEvent`・`ModelError` |
| `local_coding_agent/model/ollama.py` | `/api/chat` との接続 | `OllamaChat`・`to_ollama_messages`・`chat_request_body`・`read_stream`・`_done`・`http_error_message`・`STAT_KEYS` |
| `local_coding_agent/trace/writer.py` | 走行の記録（JSONL） | `TraceSink`（Protocol）・`TraceWriter`・`trace_path` |
| `tests/fakes.py` | 偽物 | `ScriptedModel`・`RecordingTrace`・`scripted_lines`・`ticking_clock`・`Step` |
| `tests/test_repl.py` | REPL のテスト（履歴・止めた回・誤りの回・終わりの行が無い回・空の行・表示・記録） | |
| `tests/test_ollama.py` | 変換・NDJSON の読み取り・誤りの文・URL のテスト | |
| `tests/test_trace_writer.py` | 記録のファイル名と書き出しのテスト | |

### データの流れ（1回の依頼）

1. `run` が `session.read_line("> ")` で1行を読む。空の行は飛ばす。`EOFError`（Ctrl-D）で終わる。`KeyboardInterrupt`（入力を待つ間の Ctrl-C）は改行を出して続ける
2. `run_turn` が `messages = (*history, user_text(text))` を作る（新しい tuple。`history` は変えない）
3. `session.model.build_request(messages)` が `ChatRequest(url, body)` を返す。`OllamaChat` では `body = {"model", "messages"（to_ollama_messages）, "stream": True}`
4. `session.trace.write({"type": "request", "turn", "url", "body"})`。`TraceWriter.write` が `time` を先頭に足し、JSON 1行を追記する（`ensure_ascii=False`）
5. `receive` が `session.model.stream(request)` を回す
   - `TextDelta` なら、最初の1回だけ `first = clock() - started` を取り、本文を `text += …` でつなぎ、`output.write` と `flush` で表示する
   - `Done` なら覚えておく
   - `KeyboardInterrupt` → `Outcome("cancelled", 途中の本文, …)`
   - `ModelError` → `Outcome("error", …, str(error))`
   - 流れが `Done` 無しで終わったら → `Outcome("error", …, "応答が終わりの行の前に切れた")`
6. `run_turn` が `response_record` を記録し、`summary` を表示する
7. `status == "done"` なら `(*messages, assistant_text(outcome.text))` を返す。それ以外は元の `history` を返す（止めた回・誤りの回は履歴に入らない）

### `OllamaChat.stream` の中

- `urllib.request.Request(url, data=json, headers={"Content-Type": "application/json"}, method="POST")` を `urlopen` し、`with` の中で `read_stream(response)` を `yield from` する。`HTTPResponse` を回すと1行ずつのバイト列が得られる
- `read_stream`: 空の行を飛ばし、`json.loads`。object でなければ `ModelError`。`"error"` があれば `ModelError`。`message.content` が空でなければ `TextDelta`。`done is True` なら `_done(event)` を出して終わる
- `_done`: `done_reason`（文字列でなければ None）と、`STAT_KEYS` のうち int のものだけを `stats` に入れる
- 例外の扱い: `HTTPError` → `http_error_message`（本文の `{"error": …}` を読み、接続を閉じる）。`URLError` → 「Ollama に繋がらない（URL）: 理由」。その他の `OSError`（途中で切れた等）→ 「Ollama との通信が切れた」。順序が大事（`HTTPError` ⊂ `URLError` ⊂ `OSError`）

## 設計の選択と理由・捨てた案

- **`build_request` と `stream` を分けた**: 送る JSON の全体を記録に書くため、REPL が送る前に JSON を知る必要がある。捨てた案: `stream(messages)` 1つにまとめる（REPL が送った JSON を知れない）
- **`model/chat.py` を足した**（仕様の置き方に無い）: REPL と偽物を Ollama の形から切り離すため。後で Anthropic 互換の口を足すとき、`ChatModel` を実装するクラスを足すだけで済む
- **会話は変えない値**（`frozen` の dataclass・tuple）: 持ち主の全プロジェクトの規則「オブジェクトを変えない」に合わせた。止めた回・誤りの回で元の履歴をそのまま返せる利点もある
- **Ctrl-C は `receive` の中で捕まえる**: 途中までの本文を記録に残すため
- **時間は `time.monotonic`**（`Session.clock` で差し替えられる）。記録の `time` は `datetime.now().astimezone()` の ISO 8601（ミリ秒）
- **記録の欄の名前 `model_stats`**: Ollama 以外の口でも同じ名前で使うため（仕様は「Ollama が返したトークン数と時間」）
- **テストは通信を使わない**: NDJSON は `io.BytesIO` で渡す。sandbox の中では手元のポートも開けないので、`http.server` を立てるテストは書けない
- **`trace_path` は秒までの時刻**: 同じ秒に2つ起動すると同じファイルに追記される（下の「分かっている問題」）

## 実装前の仕様との違い

`implementation.md` の「実装前の仕様との違い」の表のとおり（`model/chat.py`・起動時の表示・入力を待つ間の Ctrl-C・終わりの行が来ない応答・`model_stats`）。

## テストで確かめたこと・確かめていないこと

- 確かめた: 変換（役割・順・本文の塊をつなぐ）／要求の JSON／NDJSON（断片の連なり・空の行・最後の行の数値・数値の無い最後の行・途中の `error`・object でない行）／誤りの文（`error` の欄・本文そのまま）／URL の末尾の `/`／REPL（毎回の全体送信・止めた回・誤りの回・終わりの行が無い回・空の行・表示の数値・記録の中身と測った時間）／記録のファイル名・追記・日本語
- 確かめていない:
  - `OllamaChat.stream` の HTTP の部分（`urlopen` と例外の変換）。実物の Ollama で人が試すまで分からない
  - 実物の Ollama の最後の行に、トークン数と時間が載るか（文書は非ストリームの形でしか欄を説明していない）。載らなければ数値の表示は `?` になる
  - `__main__.py`（Claude Code が手で走らせただけ）
  - Ctrl-C を実際に押したときの振る舞い（テストは `KeyboardInterrupt` を偽物が投げる形）

## 人が問いそうなことと答え

- **なぜ毎回、全部の履歴を送るのか**: `/api/chat` は会話の状態を持たないので、前の回を覚えていない。履歴を持つのは `repl.run` の `history` だけ。`test_sends_whole_history_every_turn` がそれを確かめる。走行の記録の2つ目の要求の `body.messages` を見ると、1回目が入っている
- **`Message` の `content` がなぜ塊の並び（tuple）なのか**: Claude の Messages API に揃えるため（要件の「モデルとの接続」）。F-03 で `tool_use`・`tool_result`、F-09 で thinking の塊が加わる。Ollama の `/api/chat` は文字列なので、送る直前に `to_ollama_messages` でつなぐ
- **`ChatModel` が Protocol なのはなぜか**: 偽物（`ScriptedModel`）と `OllamaChat` が継承なしで同じ形を持てるため。mypy が形を確かめる
- **`yield from read_stream(response)` が `with` の中にあるのはなぜか**: 応答を読み終わるまで接続を開けておくため。Ctrl-C や途中の誤りで生成器が閉じると、`with` が接続を閉じる
- **`http_error_message` の `with error:` は何か**: `HTTPError` は応答の本体を持つファイルのようなものでもあり、読んだら閉じる。閉じないとテストで ResourceWarning が出た
- **`_done` の `isinstance(value, int)` は**: Ollama が返した欄のうち、整数のものだけを数値として残す。欄が無いときは入らない
- **最初の文字までの時間に何が含まれるか**: 要求を送ってから、本文の最初の断片が届くまで。モデルの読み込み（`load_duration`）と入力の処理を含む。推論（thinking）をするモデルでは、推論の時間も含む（下の「分かっている問題」）
- **`text += event.text` は「変えない」の規則に反しないか**: 文字列は変えられない値で、`+=` は新しい文字列を作って名前を付け直している。関数の中の名前の付け直しは規則の対象外と読んだ
- **`turn` の数え方**: 空の行は数えない。止めた回・誤りの回も1回と数える（記録の `turn` は送った回の番号）

## 分かっている問題・残したこと

- **壊れた JSON の行**: `read_stream` の `json.loads` が `json.JSONDecodeError` を投げると、`ModelError` ではないので REPL が落ちる。Ollama が壊れた行を返すことは考えにくいが、`ModelError` に変えるのが正しい。人が読み終えてから直すか決める
- **thinking を捨てている**: Qwen3.5 などの推論をするモデルは、`think` を指定しないときも推論の文を `message.thinking` で返すことがある（Ollama の版とモデルによる）。F-01 は `message.content` しか見ないので、推論の間は何も表示されず、最初の文字までの時間が長く見える。F-09 で扱う
- **時間切れが無い**: `urlopen` に timeout を渡していない。モデルの読み込みが長いことがあるため。Ollama が応答しないまま止まると、Ctrl-C で止めるしかない
- **proxy の環境変数**: `urllib` は `HTTP_PROXY` などの環境変数を読む。人の環境で proxy が設定されていると、`localhost` への要求が proxy に向かうことがある（`NO_PROXY` で避ける）。試していない
- **同じ秒の起動**: 記録のファイル名は秒まで。同じ秒に2つ起動すると、同じファイルに2つの走行が混ざる
- **行の編集**: `input()` をそのまま使っているので、矢印キーでの編集や履歴の呼び出しは無い（`readline` を import すれば付くが、仕様で作らないとした）
- **文脈窓**: 履歴が Ollama の文脈の長さを超えたときの扱いは無い（F-12）。Ollama の振る舞いに任せている

## main と衝突しそうな所

（F-01 は main で実装したので無い。F-02 以降の worktree 側は、ここに書く）

## 問いと答えの記録

main 側のセッションが、人から来た問いと答え・直したことを足す。

（まだ無い）
