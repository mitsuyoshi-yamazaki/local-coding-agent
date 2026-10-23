# Poetry

Python の版と依存を管理する道具である。このリポジトリでは、Python の版の固定と、依存の記録に使う。

## このリポジトリの設定

- `pyproject.toml`
  - `requires-python = ">=3.14,<3.15"` で Python の版を固定する。Poetry は、この範囲の Python を自動では入れない。手元に要る
  - `dependencies = []`。第三者のパッケージに依存していない
  - `package-mode = false`。配布するパッケージとしては扱わず、依存の管理にだけ使う。この形では `name` と `version` を省ける
- `poetry.lock`: 依存を解いた結果。アプリケーションでは commit するものとされており、このリポジトリも commit する

## 動き方

- Poetry 自身は Python 3.10 以上で動き、プロジェクトとは別の環境に入れる。プロジェクトの環境に入れてはいけない
- プロジェクトの仮想環境は、既定では Poetry のキャッシュのディレクトリ（`{cache-dir}/virtualenvs`）に作られ、リポジトリの中には作られない
- 仮想環境の Python は、既定では Poetry 自身が動く Python である。それが `requires-python` に合わなければ、合うものを探す。`poetry env use <Python のパス>` で指定できる

## 主なコマンド

| コマンド | 何をするか |
|---|---|
| `poetry install` | `poetry.lock` の通りに依存を入れる |
| `poetry run python <ファイル>` | 仮想環境の Python で走らせる |
| `poetry add <パッケージ>` | 依存を足し、`pyproject.toml` と `poetry.lock` を書き換える |

## 出典

確かめた日は 2026-10-23。版は 2.5.1。

- Introduction（Poetry 自身に要る Python の版・別の環境に入れること）: https://python-poetry.org/docs/
- Basic usage（package mode・`requires-python`・`poetry.lock`・各コマンド・仮想環境の場所）: https://python-poetry.org/docs/basic-usage/
- Managing environments（仮想環境の Python の選び方・`poetry env use`）: https://python-poetry.org/docs/managing-environments/
