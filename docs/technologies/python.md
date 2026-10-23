# Python

このリポジトリのエージェントを書く言語である。端末から実行する。

## このリポジトリでの使い方

- 版は 3.14 に固定している（`pyproject.toml` の `requires-python = ">=3.14,<3.15"`）。3.14 は修正の版が出る段階にあり、支持の終わりは 2030-10 の予定である
- 版と依存は [Poetry](poetry.md) で管理する
- 第三者のパッケージは使わず、標準ライブラリで書くのを基本にする。依存は全て `pyproject.toml` の `dependencies` に書くので、何に依存しているかはそこで分かる

## 出典

確かめた日は 2026-10-23。

- Status of Python versions（3.14 の段階と支持の終わり）: https://devguide.python.org/versions/
