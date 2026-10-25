# F-04 を試す材料

ファイルの書き込みと編集（F-04）を試すための、小さなプロジェクトである。`project/` を写し、写しを作業ディレクトリにしてエージェントを起動する。エージェントが写しを書き換えるので、試すたびに写し直す。

| ファイル | 中身 |
|---|---|
| `project/inventory.py` | 在庫の表を読む `load` と、数の合計の `total_count`（誤りがある） |
| `project/stock.txt` | タブ区切りの在庫の表。行末に空白のある行がある |
| `project/test_inventory.py` | `total_count` のテスト（通らない） |
| `project/test_report.py` | まだ無い `report.py` の `low_stock` のテスト（通らない） |
| `project/test_stock.py` | `stock.txt` の中身のテスト（通らない） |

## 写して起動する

リポジトリの根で:

```sh
cp -R tasks/f-04-file-edit/project .tmp/f-04
cd .tmp/f-04
PYTHONPATH=../.. ../../.venv/bin/python -m local_coding_agent --model qwen3.5:9b
```

- パッケージは `.venv` に入れていない（`pyproject.toml` の `package-mode = false`）ので、`PYTHONPATH` でリポジトリの根を渡す
- 写し直すときは、前の写しを消してから写す。`cp -R` は、写し先のディレクトリがあると、その中に `project/` を写す
- 走行の記録は、写しの中の `traces/` に書かれる

## 判定

リポジトリの根で、写しに対してテストを走らせる。終了コードが 0 なら通った。写したばかりの状態では、どれも通らない。

| 課題 | コマンド |
|---|---|
| `inventory.py` の誤りを直す | `.venv/bin/python -m unittest discover -s .tmp/f-04 -p test_inventory.py` |
| `report.py` を作る | `.venv/bin/python -m unittest discover -s .tmp/f-04 -p test_report.py` |
| `stock.txt` を直す | `.venv/bin/python -m unittest discover -s .tmp/f-04 -p test_stock.py` |
