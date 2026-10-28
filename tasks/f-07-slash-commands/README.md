# F-07 を試す材料

slash commands（F-07）を試すための、小さなプロジェクトである。通らないテストと、自作のコマンドのファイルを持つ。自作のコマンドは、作業ディレクトリの `.local-coding-agent/commands/<名前>.md` にあり、`/<名前>` で呼ぶたびに読まれる。プロジェクトを写し、写しを作業ディレクトリにしてエージェントを起動する。エージェントが写しを書き換えるので、試すたびに写し直す。

| ファイル | 中身 |
|---|---|
| `project/temperature.py` | 摂氏と華氏の変換。`celsius_to_fahrenheit` に誤りがある |
| `project/test_temperature.py` | テスト。写したばかりの状態では、4つのうち3つが失敗する |
| `project/.local-coding-agent/commands/fix.md` | `/fix`: テストを走らせて直す。前付けに `description` があり、本文で `$ARGUMENTS` を使う |
| `project/.local-coding-agent/commands/explain.md` | `/explain`: ファイルの役目を説明する。`description` を `"…"` で囲んである |
| `project/.local-coding-agent/commands/review.md` | `/review`: 誤りがありそうな所を挙げる。前付けも `$ARGUMENTS` も無い（引数を付けると、末尾に `ARGUMENTS: <引数>` が足される） |

## 写して起動する

リポジトリの根で:

```sh
cp -R tasks/f-07-slash-commands/project .tmp/f-07-project
cd .tmp/f-07-project
PYTHONPATH=../.. ../../.venv/bin/python -m local_coding_agent --model qwen3.5:9b
```

- 写し直すときは、前の写しを消してから写す。`cp -R` は、写し先のディレクトリがあると、その中に写す
- 走行の記録は、写しの中の `traces/` に書かれる。コマンドの行ごとに1件（`type` が `command`）が入る。自作のコマンドでモデルに送った発言は、次の `request` の件の `body.messages` の最後にある
- 既定の許可のモードは `allow-all` である。`/mode ask` で、会話の途中から、書く前とコマンドの前に問わせられる

## 課題

| 課題 | 打つもの | 見ること |
|---|---|---|
| 一覧 | `/help` | 組み込みの5つと、自作の3つ（`/explain`・`/fix`・`/review`）が出る。数値の行が出ない（モデルを呼ばない） |
| 自作のコマンドで直させる | `/fix test_temperature.py` | `[コマンド]` の行が出る。送った発言が、置き換えた本文と、`<metadata>` の `コマンド: /fix test_temperature.py` を持つ。テストが通ったか（下の判定） |
| 引数を末尾に足す | `/review temperature.py` | 送った本文の末尾に `ARGUMENTS: temperature.py` がある。モデルが `temperature.py` を読むか |
| 会話を消す | 何かを話す → `/context` → `/clear` → `/context` → 前の話を尋ねる | `/context` の発言の数が 0 になり、入力のトークン数が `まだ無い` になる。モデルが前の話を知らない |
| モードを変える | `/mode ask` → `/fix` | 書く前とコマンドの前に問う。`/mode` で今のモードが出る |
| 知らない名前 | `/tmp を見て` → ` /tmp を見て`（頭に空白） | 1つ目は誤りで送らず、2つ目は依頼として送る |

`/help`・`/clear`・`/context`・`/mode`・知らない名前は、答えに決まった値がある（画面と走行の記録で見る）。`/explain`・`/review` の答えは、人が読んで判定する。

## 判定

リポジトリの根で、写しに対してテストを走らせる。終了コードが 0 なら通った。写したばかりの状態では通らない。

```sh
.venv/bin/python tasks/f-05-run-command/judge.py .tmp/f-07-project
```
