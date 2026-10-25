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
- 推論（thinking）: 推論を学習したモデルは、答えの前に推論の文を生成する。Ollama は推論の文を本文と別の欄で返し、`think` で切り替える。gpt-oss は `think` に `low`・`medium`・`high` を渡して、推論の強さを選べる

## Apple Silicon の Mac での動き

- macOS 14 以上で動く。Apple M 系の機械では CPU と GPU を使い、Intel の機械では CPU だけを使う
- v0.40.0 以降、対応する構造のモデル（Qwen3.5・Gemma 4 など）は、Apple の機械学習の枠組み MLX を使う実行系で動く
- **既定の文脈の長さに注意する**。GPU のメモリが 24 GiB 未満の機械では、既定の文脈の長さは 4k トークンで、エージェントには足りない。`OLLAMA_CONTEXT_LENGTH` で広げる
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

## このリポジトリで使うモデル

| モデル | Ollama のライブラリでの名前 | 役 | 特徴 |
|---|---|---|---|
| Qwen3.5-9B | `qwen3.5:9b`（MLX 用の `qwen3.5:9b-mlx` もある） | 基準 | 9B（90 億パラメータ）。道具の呼び出し・推論の切り替え・画像の入力を持つ。Apache-2.0 |
| gpt-oss-20b | `gpt-oss:20b` | 推論の強さを試す用 | MoE（全体 21B のうち、1トークンごとに 3.6B だけを使う）。推論の強さを3段から選べる。Ollama での大きさは 14 GB で、メモリ 16 GB の機械ではぎりぎり載る。Apache-2.0 |

## 出典

確かめた日は、断りが無ければ 2026-10-22。

- FAQ（待ち受けのアドレス・手元で動くこと・インターネットを使うもの・クラウドの機能を切る設定・並列の数は 2026-10-23。macOS のアプリでの環境変数の設定は 2026-10-25）: https://docs.ollama.com/faq
- Troubleshooting（ログの出力先・`OLLAMA_DEBUG=1`。2026-10-25）: https://docs.ollama.com/troubleshooting
- `OLLAMA_DEBUG` の値と段（main のソース。2026-10-25）: https://github.com/ollama/ollama/blob/main/envconfig/config.go
- trace の段で出す、解析器の入力と出力（main のソースの `ChatHandler`。2026-10-25）: https://github.com/ollama/ollama/blob/main/server/routes.go
- API の基点（手元と ollama.com・手元のサーバでしかできない操作。2026-10-23）: https://docs.ollama.com/api/introduction
- Cloud（ollama.com の API と API キー。2026-10-23）: https://docs.ollama.com/cloud
- macOS（必要な版・Apple M 系と Intel）: https://docs.ollama.com/macos
- Context length（既定の文脈の長さ）: https://docs.ollama.com/context-length
- Chat（発言の欄と、`role` の値。2026-10-24）: https://docs.ollama.com/api/chat
- Modelfile（`TEMPLATE`・`SYSTEM`。2026-10-24）: https://docs.ollama.com/modelfile
- Tool calling: https://docs.ollama.com/capabilities/tool-calling
- Thinking（`think` の値と段階）: https://docs.ollama.com/capabilities/thinking
- OpenAI compatibility: https://docs.ollama.com/api/openai-compatibility
- Anthropic compatibility（対応・未対応の一覧）: https://docs.ollama.com/api/anthropic-compatibility ・ https://ollama.com/blog/claude
- v0.40.0 のリリースノート（Apple Silicon で MLX が既定に）: https://github.com/ollama/ollama/releases/tag/v0.40.0
- Qwen3.5-9B: https://huggingface.co/Qwen/Qwen3.5-9B ・ Ollama のライブラリ（2026-10-23） https://ollama.com/library/qwen3.5
- gpt-oss-20b: https://huggingface.co/openai/gpt-oss-20b ・ モデルカード https://arxiv.org/html/2508.10925v1 ・ Ollama のライブラリ（2026-10-23） https://ollama.com/library/gpt-oss
