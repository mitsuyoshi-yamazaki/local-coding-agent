# local-coding-agent

ローカル LLM（自分の機械で動かす大規模言語モデル）で動くコーディングエージェントである。Claude Code のようなコーディングエージェントの主要な機能を1つずつ自分で実装し、仕組みを理解するために作っている。

仕組みの説明と、作る機能の一覧は [docs/](docs/README.md) にある。

## できること

| 機能 | できること |
|---|---|
| [F-01 チャットと走行の記録](docs/features/f-01-chat-and-trace/implementation.md) | 端末で依頼を打つと、手元のモデルの応答を流しながら表示する。毎回、会話の全体を送る。要求と応答・トークン数・時間を記録する |
| [F-02 system prompt と環境の知らせ](docs/features/f-02-system-prompt/implementation.md) | 毎回の要求の先頭に、モデルへの指示（system prompt）と、作業ディレクトリ・git のリポジトリの中か・OS の知らせを入れる。利用者の発言には、送った時刻を付ける。指示はファイルで差し替えられる |

まだ、ファイルを読む・書く・コマンドを走らせるといった道具は使えない（[作る機能](docs/features.md) の F-03 から）。

## 要るもの

- macOS（このリポジトリは Apple Silicon の Mac で作っている）
- Python 3.14
- [Poetry](https://python-poetry.org/docs/)（2.x。Python の版と依存を管理する）
- [Ollama](https://ollama.com/) の公式アプリ（手元でモデルを動かす）

## セットアップ

### 1. Python の環境を作る

```sh
git clone https://github.com/mitsuyoshi-yamazaki/local-coding-agent.git
cd local-coding-agent
poetry install
```

仮想環境はリポジトリの中の `.venv/` に作られる（`poetry.toml` の設定）。Poetry が Python 3.14 を見つけられないときは、`poetry env use <Python 3.14 のパス>` で指定してから `poetry install` する。

実行するコードは標準ライブラリだけを使う。`poetry install` で入るのは、開発に使う lint（Ruff）と型の検査（mypy）だけである。

### 2. Ollama を設定する

Ollama のアプリを入れ、次の2つを設定してから、アプリを開き直す。

- **クラウドの機能を切る**: `~/.ollama/server.json` に `"disable_ollama_cloud": true` を書く（または、環境変数 `OLLAMA_NO_CLOUD=1`）。このエージェントは手元のモデルだけを使う
- **文脈の長さを広げる**: GPU のメモリが 24 GiB 未満の機械では、既定の文脈の長さは 4k トークンで、エージェントには足りない。アプリの設定のスライダーで広げる（または、環境変数 `OLLAMA_CONTEXT_LENGTH`）。どこまで広げられるかは、機械のメモリとモデルによる

macOS のアプリに環境変数を渡すときは、`launchctl setenv <名前> <値>` を走らせてから、アプリを開き直す。

### 3. モデルを取り込む

```sh
ollama pull qwen3.5:9b
ollama pull gpt-oss:20b
```

`qwen3.5:9b` が基準のモデルである（MLX 用の `qwen3.5:9b-mlx` もある）。`gpt-oss:20b` は推論の強さを3段から選べるモデルで、推論の段階の機能（F-10）で使う。使えるモデルとその特徴は [docs/technologies/ollama.md](docs/technologies/ollama.md) にある。

## 起動

リポジトリの根で走らせる。

```sh
.venv/bin/python -m local_coding_agent --model qwen3.5:9b
```

| 引数 | 意味 |
|---|---|
| `--model` | Ollama のモデルの名前。必須 |
| `--host` | Ollama の URL。既定は `http://localhost:11434` |
| `--system-prompt-file` | 指示の部分を、このファイルの中身（UTF-8）に差し替える。作業ディレクトリなどの環境の節は残る。無ければ既定の指示を使う |
| `--debug` | Ollama の応答を全て表示する。値を付けないと、推論の文（thinking）を薄い色で本文の前に出し、本文と推論の文のほかの欄を JSON で出す（終わりの行は全ての欄）。`--debug raw` では、Ollama から届いた行（1行に1つの JSON）をそのまま出す |
| `--no-bell` | 応答が終わったときに、端末のベルを鳴らさない |

## 使い方

画面は次のようになる（応答と数値は例）。

```text
走行の記録: traces/20261024-153012.jsonl
指示: 既定

> 私は山田です

はい、山田さん。
[入力 12 トークン・出力 5 トークン・最初の文字まで 0.81 秒・全体 1.20 秒]

> 私の名前は？

山田さんです。
[入力 30 トークン・出力 4 トークン・最初の文字まで 0.42 秒・全体 0.70 秒]

>
```

- `> ` に依頼を1行打ち、Enter で送る。応答は届いたそばから表示され、終わると数値の1行が出る
- 入力と応答の間と、数値の行と次の入力の間には、空行が入る。端末では、数値の行を薄い色で出す（誤りの行は薄くしない）
- **応答が終わると、端末のベルを鳴らす**（誤りで終わった回も鳴らし、Ctrl-C で止めた回は鳴らさない）。音が鳴るか・どの音かは端末の設定による。`--no-bell` で止められる。出力が端末でないとき（ファイルへ流すなど）は鳴らさない
- **応答の途中で Ctrl-C**: その回の応答を止める。止めた回の依頼と応答は、次の回に送る会話に入らない
- **Ctrl-D**: 終える
- **走行の記録**: 起動ごとに1つ、`traces/<起動の時刻>.jsonl` に書かれる。1行に1件で、送った JSON の全体と、受けた応答・トークン数・時間が入る。中身の欄は [F-01 の文書](docs/features/f-01-chat-and-trace/implementation.md#走行の記録) にある。送った JSON には、system prompt と、送った時刻を入れた発言が、モデルに渡した形のまま入る
- **指示の差し替え**: 指示の長さで答えがどう変わるかを試すための指示のファイルが、`tasks/f-02-system-prompt/` にある（`short.md`・`long.md`）。指示を送らないときは `--system-prompt-file /dev/null` を渡す。中身は [F-02 の文書](docs/features/f-02-system-prompt/implementation.md#試すための指示のファイル) にある

## 開発

```sh
.venv/bin/python -m unittest          # テスト（偽物のモデルを使い、Ollama には繋がない）
.venv/bin/ruff check .                 # lint
.venv/bin/ruff format --check .        # 整形の検査
.venv/bin/mypy                         # 型の検査
```

| 場所 | 中身 |
|---|---|
| `local_coding_agent/` | エージェントのコード |
| `tests/` | テスト（標準ライブラリの `unittest`） |
| `tasks/` | 実物のモデルで試すための材料 |
| `docs/` | 仕組みの説明・作る機能・要件 |
| `traces/` | 走行の記録（git に入れない） |
| `experiments/` | 実験で使う手元のファイル。自分で書いた指示のファイルなど（git に入れない） |
