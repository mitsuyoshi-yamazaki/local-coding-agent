# local-coding-agent

ローカル LLM（自分の機械で動かす大規模言語モデル）で動くコーディングエージェントである。Claude Code のようなコーディングエージェントの主要な機能を1つずつ自分で実装し、仕組みを理解するために作っている。

仕組みの説明と、作る機能の一覧は [docs/](docs/README.md) にある。

## できること

| 機能 | できること |
|---|---|
| [F-01 チャットと走行の記録](docs/features/f-01-chat-and-trace/implementation.md) | 端末で依頼を打つと、手元のモデルの応答を流しながら表示する。毎回、会話の全体を送る。要求と応答・トークン数・時間を記録する |
| [F-02 system prompt と環境の知らせ](docs/features/f-02-system-prompt/implementation.md) | 毎回の要求の先頭に、モデルへの指示（system prompt）と、作業ディレクトリ・git のリポジトリの中か・OS の知らせを入れる。利用者の発言には、送った時刻を付ける。指示はファイルで差し替えられる |
| [F-03 道具の呼び出しとループ](docs/features/f-03-tool-loop/implementation.md) | モデルに、ファイルを読む道具（`read_file`）と、ディレクトリの中身を見る道具（`list_directory`）を渡す。モデルが道具を呼ぶ間、道具を実行して結果を返し、もう一度モデルを呼ぶ。変更を伴う道具は、実行の前に人に確かめる |

ファイルを書く・コマンドを走らせる道具は、まだ無い（[作る機能](docs/features.md) の F-04・F-05）。

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

## 使い方

画面は次のようになる（応答と数値は例）。

```text
走行の記録: traces/20261024-153012.jsonl
指示: 既定
> 私は山田です
はい、山田さん。
[入力 12 トークン・出力 5 トークン・最初の文字まで 0.81 秒・全体 1.20 秒]
> README.md の1行目は？

[入力 1021 トークン・出力 30 トークン・最初の文字まで 2.10 秒・全体 2.52 秒]
[道具] read_file {"path": "README.md", "limit": 1}
→ 3 行
「# local-coding-agent」です。
[入力 1105 トークン・出力 12 トークン・最初の文字まで 0.62 秒・全体 0.80 秒]
>
```

- `> ` に依頼を1行打ち、Enter で送る。応答は届いたそばから表示され、モデルを1回呼ぶたびに数値の1行が出る
- **道具**: モデルが道具を呼ぶと、呼び出しを `[道具] <名前> <入力>` の1行で、結果を `→ <行数> 行`（誤りなら `→ 誤り: …`）の1行で表示し、結果を渡してもう一度モデルを呼ぶ。モデルが道具を呼ばずに答えたら、その回を終える。使える道具は `read_file`（ファイルを行番号付きで読む）と `list_directory`（ディレクトリの中身を見る）で、どちらも読むだけである。作業ディレクトリの外も読める
- **実行の前の問い**: 変更を伴う道具は、実行の前に `実行してよいか [y/N]: ` と問う（`y` か `yes` で実行する）。今の道具は読むだけなので、問いは出ない
- **Ctrl-C**: 応答の途中・道具の実行の途中で押すと、その回を止める。止めた回の依頼・道具の呼び出しと結果・応答は、次の回に送る会話に入らない
- **Ctrl-D**: 終える
- **走行の記録**: 起動ごとに1つ、`traces/<起動の時刻>.jsonl` に書かれる。1行に1件で、送った JSON の全体と、受けた応答・道具の呼び出しと結果・トークン数・時間が入る。中身の欄は [F-01 の文書](docs/features/f-01-chat-and-trace/implementation.md#走行の記録) と [F-03 の文書](docs/features/f-03-tool-loop/implementation.md#走行の記録) にある。送った JSON には、system prompt・道具の定義・送った時刻を入れた発言が、モデルに渡した形のまま入る
- **指示の差し替え**: 指示の長さで答えがどう変わるかを試すための指示のファイルが、`tasks/f-02-system-prompt/` にある（`short.md`・`long.md`）。指示を送らないときは `--system-prompt-file /dev/null` を渡す。中身は [F-02 の文書](docs/features/f-02-system-prompt/implementation.md#試すための指示のファイル) にある
- **道具を試す材料**: ファイルを辿らないと答えられない問いと、長いファイルを分けて読む問いのための小さなプロジェクトが、`tasks/f-03-tool-loop/project/` にある。問いと答えは [F-03 の文書](docs/features/f-03-tool-loop/implementation.md#試すための材料) にある

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
