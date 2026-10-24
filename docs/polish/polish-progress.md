# polish の進行

polish 側（branch `polish`）で行ったことと、main との差異の記録である。書き方は `.claude/rules/polish.md` にある。

## 現在の状況

- 作業中の issue: 無い
- 人を待っていること: main 側への変更の依頼（下の「main 側に頼むこと」）・`poetry install` で `.venv/` を作ること
- `poetry install` と `poetry env use …python3.14` は、「Current Python version (3.6.5) is not allowed」で止まった（2026-10-24）。Poetry 2.5.1 は、`VIRTUAL_ENV`（または base でない conda の `CONDA_PREFIX`）があると「すでに仮想環境の中にいる」と見なし、in-project の `.venv` が無いときはその環境の版を検査する。polish のセッションが、Python 3.6.5 の環境が有効なまま起動されたと見ている（環境変数は読めないので確かめていない）。`poetry.toml` は `in-project = true` だけで、`virtualenvs.create = false` ではない。next の worktree では同じ設定で動き、`.venv` は `/usr/local/opt/python@3.14/bin/python3.14` で作られている

## main との差異

### 目的

- polish は、本アプリケーションをソフトウェアとして使うときの使いやすさを上げる。学習と実装が済んだ後に、このソフトウェアを別のリポジトリで改善していくときの元にする。main は学習用の簡素な実装に保つ

### 運用

- 課題を issues-human.md・issues-claude.md（git に入れない）から1件ずつ取り出し、要れば specs/ で人と要件と仕様を決め、実装し、解決したら項目を消してこのファイルに書く（`.claude/rules/polish.md`）
- `docs/polish/handoff.md` は作らない。セッションの間の引き継ぎは、このファイルと specs/ に書く
- 人が全てのコードを読むこと・1機能を「仕様 → 実装 → 読む → 試す → 記録」で進めること・1ファイル 200 行程度と関数 50 行までの目安を、前提にしない（要件の「進め方と記録」の polish 側の項）

### 設定と文書

- `.claude/rules/polish.md` がある（main には無い）
- `.gitignore` に、`docs/polish/issues-human.md`・`docs/polish/issues-claude.md` がある
- CLAUDE.md の「polish 側」の項は、引き継ぎの置き場を `docs/polish/polish-progress.md` と `.claude/rules/polish.md` にしている（main は `docs/polish/handoff.md` を指している。main 側に同じ文面への直しを頼んでいる）

### コード

- 差異は無い

## main 側に頼むこと

- CLAUDE.md の main 側の項から、polish 側の進み具合を写す記述を消す。CLAUDE.md の polish 側の項を、polish の branch と同じ文面に直す。docs/progress.md の polish 側の進み具合の見方を直す（2026-10-24 に、依頼の文面を人に渡した）

## 経過

### 2026-10-24

- polish 側の進行を管理するファイル（issues-human.md・issues-claude.md・polish-progress.md・specs/）と `.claude/rules/polish.md` を足した。CLAUDE.md の polish 側の項で、handoff.md を指していた所を直した
