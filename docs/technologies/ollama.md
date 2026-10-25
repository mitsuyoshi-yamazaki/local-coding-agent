# Ollama

公開されたモデル（Qwen・gpt-oss など）を手元の機械で動かす実行環境である。このリポジトリでは、LLM の実行に使う。

## 動き方

- Ollama はローカルのサーバとして動き、HTTP の API を出す。既定では `127.0.0.1` の 11434 番で待ち受け、API の基点は `http://localhost:11434/api` である
- 手元のモデルを使う限り、要求は機械の外へ出ない。公式の FAQ は "Ollama runs locally. We don't see your prompts or data when you run locally." と書く
- インターネット経由の Ollama のサービス（ollama.com）も、同じ API を `https://ollama.com/api` で出している。API キーが要る。モデルの作成・削除は手元のサーバでしかできない
- 待ち受けのアドレスは `OLLAMA_HOST` で変えられる。変えると、同じ LAN の他の機械からも呼べるようになる。このリポジトリでは変えない

## インターネットを使うもの

- **モデルの取り込み**（`ollama pull`）。一度取り込めば、推論にインターネットは要らない
- **アプリの自動の更新**（macOS・Windows）
- **クラウドのモデルと web 検索**。手元ではなく Ollama のサーバで動くモデルで、使うと要求は Ollama のサーバへ送られる。`OLLAMA_NO_CLOUD=1`（または `~/.ollama/server.json` に `"disable_ollama_cloud": true`）で、これらを切った手元だけの状態にできる。このリポジトリの目的はローカル LLM なので、クラウドのモデルは使わない

## API の口

Ollama は3種類の口を持つ。同じモデルを、どの形でも呼べる。

| 口 | 形 | 備考 |
|---|---|---|
| 独自の API | `/api/chat` など | 道具の呼び出し（`tools`）・推論の切り替え（`think`）・JSON Schema による出力の指定（`format`）を持つ |
| OpenAI 互換 | `/v1/chat/completions` など | OpenAI の API と同じ形 |
| Anthropic 互換 | `/v1/messages` | Claude の API と同じ形（v0.14.0 から）。Claude Code をこの口につなぐこともできる。`tool_choice` などは使えない |

## 指示（system prompt）の渡し方

- `/api/chat` には system prompt の欄が無い。`messages` の中に、`role` が `system` の発言として入れる（[仕組み](../how-coding-agents-work.md#指示system-prompt)）
- 発言が持つ欄は `role`・`content`・`images`・`tool_calls` で、送った時刻などのメタデータの欄は無い
- Ollama は、`messages` を、モデルごとの雛形（Modelfile の `TEMPLATE`）で1つの文に組み立ててから、モデルに渡す。Modelfile の `SYSTEM` は、その雛形に入れる system の発言を決める

## 道具の呼び出しと推論

- 道具の呼び出し（[仕組み](../how-coding-agents-work.md#道具の呼び出し)）: `/api/chat` の `tools` に道具の定義を渡すと、モデルが呼び出しを返す。道具の呼び出しを学習したモデルでないと使えない
  - 道具の定義は、`type` が `function` で、`function` に `name`・`description`・`parameters`（入力の形の JSON Schema）を持つ
  - 呼び出しは、モデルの発言の `tool_calls` に入る。1つは、`id` と、`function` の `index`・`name`・`arguments` を持つ。`arguments` は文字列ではなく、JSON の object である
  - 結果は、`role` が `tool` の発言で返す。道具の名前（`tool_name`）と呼び出しの id（`tool_call_id`）と、結果の文（`content`）を持つ。Claude の Messages API の `is_error` にあたる欄は無い
  - ストリーミングでは、`tool_calls` は流れてくる断片のどれかに載る。全ての断片から集める
- 推論（thinking）: 推論を学習したモデルは、答えの前に推論の文を生成する。Ollama は推論の文を本文と別の欄（`message.thinking`）で返し、`think` で切り替える。`think` を送らなければ、モデルの既定に従う。gpt-oss は `think` に `low`・`medium`・`high` を渡して、推論の強さを選べる
  - 道具を呼んだモデルの発言は、推論の文も `thinking` に入れて履歴に戻せる。文書の道具の呼び出しのストリーミングの例は、そうしている

## Apple Silicon の Mac での動き

- macOS 14 以上で動く。Apple M 系の機械では CPU と GPU を使い、Intel の機械では CPU だけを使う
- v0.40.0 以降、対応する構造のモデル（Qwen3.5・Gemma 4 など）は、Apple の機械学習の枠組み MLX を使う実行系で動く。どちらの実行系で動いているかは、`ollama ps` の `RUNNER` の列に出る（`qwen3.5:9b` は `mlx`。実測）
- **既定の文脈の長さに注意する**。GPU のメモリが 24 GiB 未満の機械では、既定の文脈の長さは 4k トークンである。MLX でない実行系では、超えた分を切り詰める（次の項）ので、エージェントには足りない。`OLLAMA_CONTEXT_LENGTH` で広げる
- **文脈の長さを超えた会話の切り詰め**: Ollama は、`messages` を組み立てた文が文脈の長さを超えると、古い発言から落として収める。system の発言と最後の発言は残す。応答には、落としたことは出ない。要求の `truncate` に `false` を渡すと切り詰めない。ただし、形式が safetensors のモデル（MLX の実行系で動くもの）では、`truncate` によらず切り詰めない。`qwen3.5:9b` は、`ollama ps` の `CONTEXT` が 4096 のまま、28811 トークンの入力を処理し、会話の先頭の依頼に答えた（実測。[F-03 の計測の結果](../features/f-03-tool-loop/measurements.md)）。MLX の実行系の中で文脈の長さがどう使われるかは、確かめていない
- 既定では、一度に1つの要求だけを処理する（`OLLAMA_NUM_PARALLEL`）

## 使い方

### ログの出力先

| 動かし方 | 出力先 |
|---|---|
| macOS のアプリ | `~/.ollama/logs/server.log` |
| 端末で `ollama serve` を走らせたとき | その端末 |

ほかの OS（Linux・Windows）とコンテナでの出力先は、公式の Troubleshooting にある。

エージェントが送った要求と受けた応答の中身は、エージェントの側の走行の記録にある（[F-01 の走行の記録](../features/f-01-chat-and-trace/implementation.md#走行の記録)）。Ollama のログは、Ollama のサーバの側で書かれる。

### ログの段（レベル）の変え方

環境変数 `OLLAMA_DEBUG` で変える。

| 値 | 段 |
|---|---|
| 無し・`0` | info（既定） |
| `1` | debug |
| `2` | trace（debug より詳しい）。モデルに組み込みの解析器（parser）があるとき、モデルが出した生の文と、それを本文・推論の文・道具の呼び出しに分けた後の形が出る |

macOS のアプリでは、環境変数を `launchctl` で設定し、アプリを起動し直す。

```sh
launchctl setenv OLLAMA_DEBUG 2
# Ollama のアプリを終了して、起動し直す
```

戻すときは、`launchctl unsetenv OLLAMA_DEBUG` を実行し、アプリを起動し直す。端末で走らせるときは、`OLLAMA_DEBUG=2 ollama serve` のように、起動するコマンドに付ける。

### 前の要求の計算の使い回し（KV キャッシュ）

- モデルは、入力のトークンを処理するときに、トークンごとに注意（attention）の計算の中間の結果を作る。これを KV キャッシュと呼ぶ。Ollama のサーバは、KV キャッシュを、モデルを載せたメモリに持つ
- Ollama のサーバは、応答の後も KV キャッシュを残す。会話の続き（前の要求に、応答と次の発言を足した要求）を送ると、前の要求の部分を処理し直さない（実測。`qwen3.5:9b`）。公式の文書には書かれていない
- 先頭の一部だけが前の要求と同じ要求（同じ system prompt で始めた別の会話など）では、その部分も処理し直すことがある（実測。`qwen3.5:9b`）。どこまで使い回すかの決まりは、公式の文書に無い
- 使い回したかは、応答の欄には出ない。応答の `prompt_eval_count`（入力のトークン数）は使い回した分を含めた全体の数で、使い回すと `prompt_eval_duration`（入力の処理の時間）だけが短くなる（実測）
- このエージェントは、system prompt を会話の間は変えず、前の回までの発言を送ったときのまま送るので、要求の先頭が毎回同じ文になる（[F-02](../features/f-02-system-prompt/implementation.md#モデルに届く文)）

公式の文書には、KV キャッシュの期限や大きさを直接決める設定は無い。次の設定が、間接に決める。

| 決まるもの | 設定 | 既定 |
|---|---|---|
| 期限 | `OLLAMA_KEEP_ALIVE`: モデルをメモリに置いておく時間。モデルがメモリから外れると、KV キャッシュも消える。負の値で置いたまま、`0` で応答の後すぐ外す。要求の `keep_alive` の欄が、この設定より優先する | 5 分 |
| 大きさの上限 | 文脈の長さ（`OLLAMA_CONTEXT_LENGTH`、またはアプリの設定）。今の値は、`ollama ps` の `CONTEXT` の列で見る。MLX の実行系では、文脈の長さを超えた入力も処理した（上の「Apple Silicon の Mac での動き」） | GPU のメモリによる（上の「Apple Silicon の Mac での動き」） |
| 使うメモリの量 | `OLLAMA_KV_CACHE_TYPE`: KV キャッシュの数値を何ビットで持つか（量子化）。`f16`・`q8_0`（`f16` の約 1/2。精度がわずかに落ちる）・`q4_0`（約 1/4。精度が少し落ちる）。Flash Attention（文脈が長いときのメモリを減らす計算の方法）が効いているときだけ使え、全てのモデルに効く | `f16` |
| 同時に持てる会話の数 | `OLLAMA_NUM_PARALLEL`: 1つのモデルが同時に処理する要求の数。要るメモリは、この数 × 文脈の長さで増える | 1 |

macOS のアプリでの設定のしかたは、上の `OLLAMA_DEBUG` と同じ（`launchctl setenv` して、アプリを起動し直す）。

## このリポジトリで使うモデル

| モデル | Ollama のライブラリでの名前 | 役 | 特徴 |
|---|---|---|---|
| Qwen3.5-9B | `qwen3.5:9b`（MLX 用の `qwen3.5:9b-mlx` もある） | 基準 | 9B（90 億パラメータ）。道具の呼び出し・推論の切り替え・画像の入力を持つ。32 層のうち 24 層が線形注意（linear attention）の層で、トークンごとの K/V の代わりに固定の大きさの状態を持つ。残りの 8 層が通常の注意の層。Apache-2.0 |
| gpt-oss-20b | `gpt-oss:20b` | 推論の強さを試す用 | MoE（全体 21B のうち、1トークンごとに 3.6B だけを使う）。推論の強さを3段から選べる。Ollama での大きさは 14 GB で、メモリ 16 GB の機械ではぎりぎり載る。Apache-2.0 |

## 出典

確かめた日は、断りが無ければ 2026-10-22。

- FAQ（待ち受けのアドレス・手元で動くこと・インターネットを使うもの・クラウドの機能を切る設定・並列の数は 2026-10-23。macOS のアプリでの環境変数の設定・モデルをメモリに置いておく時間・並列とメモリ・Flash Attention・KV キャッシュの量子化は 2026-10-25）: https://docs.ollama.com/faq
- Troubleshooting（ログの出力先・`OLLAMA_DEBUG=1`。2026-10-25）: https://docs.ollama.com/troubleshooting
- `OLLAMA_DEBUG` の値と段（main のソース。2026-10-25）: https://github.com/ollama/ollama/blob/main/envconfig/config.go
- trace の段で出す、解析器の入力と出力（main のソースの `ChatHandler`。2026-10-25）: https://github.com/ollama/ollama/blob/main/server/routes.go
- 文脈の長さを超えた会話の切り詰め（`ChatHandler` の `truncate`・MLX のモデルでは切り詰めない。2026-10-25）: https://github.com/ollama/ollama/blob/main/server/routes.go ・ 古い発言から落とし、system の発言と最後の発言を残す（`chatPrompt`。2026-10-25）: https://github.com/ollama/ollama/blob/main/server/prompt.go ・ MLX のモデルの見分け方（`Model.IsMLX`。2026-10-25）: https://github.com/ollama/ollama/blob/main/server/images.go
- API の基点（手元と ollama.com・手元のサーバでしかできない操作。2026-10-23）: https://docs.ollama.com/api/introduction
- Cloud（ollama.com の API と API キー。2026-10-23）: https://docs.ollama.com/cloud
- macOS（必要な版・Apple M 系と Intel）: https://docs.ollama.com/macos
- Context length（既定の文脈の長さ。変え方と `ollama ps` での見方は 2026-10-25）: https://docs.ollama.com/context-length
- Chat（発言の欄と、`role` の値。2026-10-24）: https://docs.ollama.com/api/chat
- Modelfile（`TEMPLATE`・`SYSTEM`。2026-10-24）: https://docs.ollama.com/modelfile
- Tool calling（道具の定義と呼び出しと結果の形・ストリーミングでの集め方。2026-10-24。ストリーミングの例が推論の文を履歴に戻すことは 2026-10-25）: https://docs.ollama.com/capabilities/tool-calling
- API の型（発言の `tool_calls`・`tool_name`・`tool_call_id`、呼び出しの `id`・`index`・`arguments`。2026-10-24）: https://github.com/ollama/ollama/blob/main/api/types.go
- Thinking（`think` の値と段階。`message.thinking` と、`think` を送らないときはモデルの既定に従うことは 2026-10-25）: https://docs.ollama.com/capabilities/thinking
- OpenAI compatibility: https://docs.ollama.com/api/openai-compatibility
- Anthropic compatibility（対応・未対応の一覧）: https://docs.ollama.com/api/anthropic-compatibility ・ https://ollama.com/blog/claude
- v0.40.0 のリリースノート（Apple Silicon で MLX が既定に）: https://github.com/ollama/ollama/releases/tag/v0.40.0
- Qwen3.5-9B: https://huggingface.co/Qwen/Qwen3.5-9B ・ 層の構成（`config.json` の `layer_types`。2026-10-25） https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/config.json ・ Ollama のライブラリ（2026-10-23） https://ollama.com/library/qwen3.5
- gpt-oss-20b: https://huggingface.co/openai/gpt-oss-20b ・ モデルカード https://arxiv.org/html/2508.10925v1 ・ Ollama のライブラリ（2026-10-23） https://ollama.com/library/gpt-oss
