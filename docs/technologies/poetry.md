# Poetry

Python の版と依存を管理する道具である。このリポジトリでは、Python の版の固定と、依存の記録に使う。

## このリポジトリの設定

- `pyproject.toml`
  - `requires-python = ">=3.14,<3.15"` で Python の版を固定する。Poetry は、この範囲の Python を自動では入れない。手元に要る
  - `dependencies = []`。第三者のパッケージに依存していない
  - `package-mode = false`。配布するパッケージとしては扱わず、依存の管理にだけ使う。この形では `name` と `version` を省ける
  - `[dependency-groups]` の `dev`: 開発にだけ使う依存（lint の Ruff と、型の検査の mypy）。実行するコードは、これに依存しない
- `poetry.lock`: 依存を解いた結果。アプリケーションでは commit するものとされており、このリポジトリも commit する
- `poetry.toml`: このプロジェクトだけの Poetry の設定。`virtualenvs.in-project = true` で、仮想環境をリポジトリの中の `.venv/` に作る

## 動き方

- Poetry 自身は Python 3.10 以上で動き、プロジェクトとは別の環境に入れる。プロジェクトの環境に入れてはいけない
- プロジェクトの仮想環境は、既定では Poetry のキャッシュのディレクトリ（`{cache-dir}/virtualenvs`）に作られる。`virtualenvs.in-project` を `true` にしても、キャッシュに既に仮想環境があると、Poetry はそちらを使う。キャッシュの仮想環境を消すと、設定が効く
- 仮想環境の Python は、既定では Poetry 自身が動く Python である。それが `requires-python` に合わなければ、合うものを探す。`poetry env use <Python のパス>` で指定できる

## 主なコマンド

| コマンド | 何をするか |
|---|---|
| `poetry install` | `poetry.lock` の通りに依存を入れる |
| `poetry run python <ファイル>` | 仮想環境の Python で走らせる |
| `poetry add <パッケージ>` | 依存を足し、`pyproject.toml` と `poetry.lock` を書き換える。`--group dev` で開発用の依存に足す |

## 出典

確かめた日は、断りが無ければ 2026-10-23。版は 2.5.1。

- Introduction（Poetry 自身に要る Python の版・別の環境に入れること）: https://python-poetry.org/docs/
- Basic usage（package mode・`requires-python`・`poetry.lock`・各コマンド・仮想環境の場所）: https://python-poetry.org/docs/basic-usage/
- Managing environments（仮想環境の Python の選び方・`poetry env use`）: https://python-poetry.org/docs/managing-environments/
- Configuration（`virtualenvs.in-project` と、キャッシュに仮想環境があるときの扱い・`poetry.toml`。2026-10-24）: https://python-poetry.org/docs/configuration/
