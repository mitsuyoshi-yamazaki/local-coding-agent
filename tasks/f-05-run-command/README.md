# F-05 を試す材料

コマンドの実行と、結果を読んで直すループ（F-05）を試すための、小さなプロジェクトが2つある。どちらも、通らないテストを持つ。プロジェクトを写し、写しを作業ディレクトリにしてエージェントを起動する。エージェントが写しを書き換えるので、試すたびに写し直す。

| プロジェクト | 中身 | テストを走らせると |
|---|---|---|
| `duration/` | 時間の長さの文字列（`1h30m`）と秒数を変換する `parse_duration`・`format_duration`。どちらにも誤りがある | 失敗する（期待した値と、実際の値が出る） |
| `words/` | 文を語に分ける `split_words`。スペースのある文で、ループが終わらない | 終わらない（エージェントの `run_command` では時間切れになる） |

どちらのプロジェクトにも、テストの走らせ方（`python3 -m unittest`）を書いた `README.md` がある。

## 写して起動する

リポジトリの根で（`duration` の例。`words` も同じ）:

```sh
cp -R tasks/f-05-run-command/duration .tmp/f-05-duration
cd .tmp/f-05-duration
PYTHONPATH=../.. ../../.venv/bin/python -m local_coding_agent --model qwen3.5:9b
```

- パッケージは `.venv` に入れていない（`pyproject.toml` の `package-mode = false`）ので、`PYTHONPATH` でリポジトリの根を渡す
- 写し直すときは、前の写しを消してから写す。`cp -R` は、写し先のディレクトリがあると、その中に写す
- 走行の記録は、写しの中の `traces/` に書かれる
- 既定の許可のモードは `allow-all` で、コマンドを走らせる前に問わない。問わせるときは、起動の引数に `--permission-mode ask` を足す
- エージェントが走らせるコマンドは、起動した端末の `PATH` で探される。`python3` が無い機械では、モデルは別のコマンドを試すことになる

## 判定

リポジトリの根で、写しに対してテストを走らせる。終了コードが 0 なら通った。写したばかりの状態では、どちらも通らない。

| 課題 | コマンド |
|---|---|
| `duration` を直す | `.venv/bin/python tasks/f-05-run-command/judge.py .tmp/f-05-duration` |
| `words` を直す | `.venv/bin/python tasks/f-05-run-command/judge.py .tmp/f-05-words` |

`judge.py` は、テストを 30 秒で打ち切る。`words` の終わらないテストが直っていなくても、判定は止まらない。
