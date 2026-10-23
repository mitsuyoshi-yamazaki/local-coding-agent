# Ollama

このリポジトリで、LLM を手元の機械で動かすために使う実行環境である。まだ入れていない（入れるのはリポジトリの持ち主）。

## 何をするものか

Ollama は、重み（学習で決まったモデルの数値）が公開された LLM を、手元の機械で動かすプログラムである。モデルの取り込み・読み込み・推論を行い、ほかのプログラムから呼べる API を出す。

起動すると、**自分の機械の中に HTTP のサーバを立てる**。既定では `127.0.0.1` の 11434 番で待ち受ける。

## 「API で呼ぶ」の意味

API で呼ぶといっても、インターネット上のサービスを呼ぶわけではない。web の API と同じ HTTP と JSON で、自分の機械の中のサーバに要求を送る。

```sh
curl http://localhost:11434/api/chat -d '{
  "model": "<モデルの名前>",
  "messages": [{"role": "user", "content": "こんにちは"}]
}'
```

- 要求は機械の外へ出ない。公式の FAQ は "Ollama runs locally. We don't see your prompts or data when you run locally." と書く
- 待ち受けのアドレスは `OLLAMA_HOST` で変えられる。変えると、同じ LAN の他の機械からも呼べるようになる。このリポジトリでは変えない

## インターネットを使うもの

- **モデルの取り込み**（`ollama pull`）。一度取り込めば、推論にインターネットは要らない
- **アプリの自動の更新**（macOS・Windows）
- **クラウドのモデルと web 検索**。Ollama は、手元ではなく Ollama のサーバで動くモデルも提供している。これを使うと、要求は Ollama のサーバへ送られる。`OLLAMA_NO_CLOUD=1`（または `~/.ollama/server.json` に `"disable_ollama_cloud": true`）で、これらを切った手元だけの状態にできる。このリポジトリの目的はローカル LLM なので、クラウドのモデルは使わない

## API の口

Ollama は3種類の口を持つ。同じモデルを、どの形でも呼べる。

| 口 | 形 | 備考 |
|---|---|---|
| 独自の API | `/api/chat` など | 道具の呼び出し（`tools`）・推論の切り替え（`think`）・JSON Schema による出力の指定（`format`）を持つ |
| OpenAI 互換 | `/v1/chat/completions` など | OpenAI の API と同じ形 |
| Anthropic 互換 | `/v1/messages` | Claude の API と同じ形（v0.14.0 から）。Claude Code をこの口につなぐこともできる。`tool_choice` などは使えない |

## 道具の呼び出しと推論

- 道具の呼び出し（[仕組み](../how-coding-agents-work.md#道具の呼び出し)）: `/api/chat` の `tools` に道具の定義を渡すと、モデルが呼び出しを返す。道具の呼び出しを学習したモデルでないと使えない
- 推論（thinking）: 推論を学習したモデルは、答えの前に推論の文を生成する。Ollama は推論の文を本文と別の欄で返し、`think` で切り替える。gpt-oss は `think` に `low`・`medium`・`high` を渡して、推論の強さを選べる

## Apple Silicon の Mac での動き

- macOS 14 以上で動く。Apple M 系の機械では CPU と GPU を使い、Intel の機械では CPU だけを使う
- v0.40.0（2026-09-25）から、対応する構造のモデル（Qwen3.5・Gemma 4 など）は、Apple の機械学習の枠組み MLX を使う実行系で動く
- **既定の文脈の長さに注意する**。GPU のメモリが 24 GiB 未満の機械では、既定の文脈の長さは 4k トークンで、エージェントには足りない。`OLLAMA_CONTEXT_LENGTH` で広げる
- 既定では、一度に1つの要求だけを処理する（`OLLAMA_NUM_PARALLEL`）

## このリポジトリで使うモデル

| モデル | 役 | 特徴 |
|---|---|---|
| Qwen3.5-9B | 基準 | 9B（90 億パラメータ）。道具の呼び出し・推論の切り替え・画像の入力を持つ。Apache-2.0 |
| gpt-oss-20b | 推論の強さを試す用 | MoE（全体 21B のうち、1トークンごとに 3.6B だけを使う）。推論の強さを3段から選べる。重みは約 12 GB で、メモリ 16 GB の機械ではぎりぎり載る。Apache-2.0 |

Ollama での正確なモデルの名前（タグ）は、取り込むときに確かめる。

## 出典

確かめた日は 2026-10-22（FAQ は 2026-10-23）。

- FAQ（待ち受けのアドレス・手元で動くこと・インターネットを使うもの・クラウドの機能を切る設定・並列の数）: https://docs.ollama.com/faq
- macOS（必要な版・Apple M 系と Intel）: https://docs.ollama.com/macos
- Context length（既定の文脈の長さ）: https://docs.ollama.com/context-length
- Tool calling: https://docs.ollama.com/capabilities/tool-calling
- Thinking（`think` の値と段階）: https://docs.ollama.com/capabilities/thinking
- OpenAI compatibility: https://docs.ollama.com/api/openai-compatibility
- Anthropic compatibility（対応・未対応の一覧）: https://docs.ollama.com/api/anthropic-compatibility ・ https://ollama.com/blog/claude
- v0.40.0 のリリースノート（Apple Silicon で MLX が既定に）: https://github.com/ollama/ollama/releases/tag/v0.40.0
- Qwen3.5-9B: https://huggingface.co/Qwen/Qwen3.5-9B
- gpt-oss-20b: https://huggingface.co/openai/gpt-oss-20b ・ モデルカード https://arxiv.org/html/2508.10925v1
