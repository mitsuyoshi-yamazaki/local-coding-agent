# CLAUDE.md

このリポジトリで作業する Claude Code への指示である。

- 要件は [docs/requirements.md](docs/requirements.md) にあり、下で読み込む。正本は上流のリポジトリ（非公開）にあり、変更は `docs/inbox/` で届く
- この文書と Claude Code の設定（`.claude/`）は、要件から skill `derive-settings` で書き起こしたものである。要件と設定の対応と、設定では止められない部分は [docs/claude-code-settings.md](docs/claude-code-settings.md) にある
- 要件が変わったとき・Claude Code の版が上がったとき・道具を足したときは、`derive-settings` で書き起こし直す（変更は持ち主の承認を得てから）
- 返答の言語などの、持ち主の全プロジェクトに共通の規則は `~/.claude/rules/` にあり、ここにも効く

@docs/requirements.md

## 設定では止められないので、守ること

- **削除**: ファイルを消す・名前を変える・未コミットの変更を捨てる操作は行わない。要るときは、消すものとコマンドを示して人に頼む
- **リポジトリの外**: 読まない・書かない。一時ファイルは `.tmp/` に置く（Claude Code の scratchpad も使わない）
- **秘匿情報**: 環境変数と秘匿のファイルを読まない。Python などのプログラムを介しても読まない
- **書き方**: ファイルを読む・探すのは Read・Grep・Glob で行い、`cat`・`grep`・`find` を使わない。web を読むのは WebFetch で行う。shell のコマンドは間接的に呼ばない（`cd … &&`・`git -C`・`git -c`・`sh -c`・変数の展開 `$…`）。規則が止めない書き方に言い換えて、禁止の操作を行わない
- **push しない**。remote の操作は基本行わない

## 人と相談して進めること

- 仕様の決定・CLAUDE.md や rule や skill や設定の変更・依存や道具の導入（`poetry` のコマンドを含む）
- 自律的に行ってよいのは、機能の実装（テストと手元の commit を含む）・動作検証・docs/ の記載・outbox への記録である

## Python の環境

- 仮想環境はリポジトリの中の `.venv/` にある。コードは `.venv/bin/python` で走らせる（`poetry run` は使わない）
- commit の前に、テストと lint と型の検査を通す: `.venv/bin/python -m unittest`・`.venv/bin/ruff check .`・`.venv/bin/ruff format --check .`・`.venv/bin/mypy`（mypy が検査する場所は `pyproject.toml` にある。コードの置き場を作ったら足す）

## 記録

- 機能の記録は、skill `feature-record` の手順と雛形で書く

## 文書（docs/）

- 使う技術は、使い始めるときに `docs/technologies/` に書く。作る機能は、作るときに、その機能が何をし、どういう仕組みで動くかを書く
- 機能を足すたびに、`README.md` のセットアップ・起動・使い方と「できること」を、その機能に合わせて直す（機能の commit に含める）
- 書き方の規則は [.claude/rules/docs.md](.claude/rules/docs.md) にある（docs/ の文書を読み書きすると読み込まれる）
- outbox の記録で仕組みに触れるときは、docs/ を指す

## commit

- commit するもの: コード・テスト・試すための課題・docs/ の文書・開発の設定
- commit するファイルに、持ち主の個人の情報・上流の文書の中身（要件を除く）・手元の絶対パスを書かない
- 機械が出す 1 MB 以上のログは commit しない
