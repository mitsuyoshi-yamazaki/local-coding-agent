# polish の進行

polish 側（branch `polish`）で行ったことと、main との差異の記録である。書き方は `.claude/rules/polish.md` にある。

## 現在の状況

- 作業中の issue: H-01〜H-04。実装し、テスト・lint・型の検査が通った（下の経過の 2026-10-25）
- 人を待っていること: H-01〜H-04 を、実物のモデルと端末で試して、解決したかを確かめる。特に、ベルが鳴るか（端末の設定による）・貼り付けで `^[[200~` が見えないか・矢印キーを打った依頼が取り消されるか
- `.venv/` は Python 3.14.4 でできている。polish のセッションの中では `poetry` のコマンドが「Current Python version (3.6.5) is not allowed」で止まるので、`poetry` は持ち主が端末で走らせる（下の経過）

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
- README.md の「起動」に `--debug`・`--no-bell` があり、「使い方」に、改行の入れ方・行の編集・ベル・区切りの説明と、空行を入れた画面の例がある。Ctrl-D の説明に、依頼の途中では取り消しになることがある

### コード

- `model/chat.py`・`model/ollama.py`: 応答の知らせに、`RawLine`（届いた行そのもの）・`ThinkingDelta`（推論の文）・`OtherFields`（本文と推論の文のほかの欄）がある。main は本文の断片と終わりの知らせだけ
- `cli/screen.py`（main に無い）: 画面への書き出し。文の種類（本文・推論の文・添え書き）ごとに薄い色を付け、行の頭にいるかを覚える。ベルも鳴らす
- `cli/user_input.py`（main に無い）: 行末の `\` と bracketed paste で、改行を含む依頼を読む。依頼の途中の Ctrl-D と、矢印キーなどを打った依頼は取り消す。REPL の間、端末の ECHOCTL を切る
- `cli/repl.py`: `Display`（色・デバッグの段・ベル）を持つ。入力の後と数値の行の後に空行を入れ、数値の行を薄くする。デバッグの段に合わせて知らせを表示する
- `__main__.py`: `--debug [raw]`・`--no-bell` がある。色とベルは、出力が端末のときだけ使う。起動の知らせの後に空行を入れる
- main と衝突しそうな所: main が F-03（道具の呼び出し）や F-09（thinking）で、`read_stream`・`StreamEvent`・`repl.receive` を変えると衝突する。polish の変更を活かして解く

## main 側に頼むこと

- 無い

## 経過

### 2026-10-24

- polish 側の進行を管理するファイル（issues-human.md・issues-claude.md・polish-progress.md・specs/）と `.claude/rules/polish.md` を足した。CLAUDE.md の polish 側の項で、handoff.md を指していた所を直した
- `.venv/` を作った。`poetry install` は、セッションの中でも持ち主の端末でも、そのままでは止まった
  - セッションの中: `poetry install`・`poetry env use …python3.14` が「Current Python version (3.6.5) is not allowed」で止まった。Poetry 2.5.1 は、`VIRTUAL_ENV`（または base でない conda の `CONDA_PREFIX`）があると「すでに仮想環境の中にいる」と見なし、in-project の `.venv` よりもその環境を優先する。polish のセッションのプロセスに、Python 3.6.5 の環境を指す変数があると見ている（環境変数は読めないので確かめていない。持ち主の端末では空だった）
  - 持ち主の端末: `.venv` が無いので、Poetry が Python を探すために `python`（pyenv の shim）を走らせ、終了コード 127 で止まった
  - 直し方: セッションで `/usr/local/opt/python@3.14/bin/python3.14 -m venv .venv` で `.venv` を先に作り（next の `.venv` と同じ Python）、持ち主が端末で `poetry install` を走らせた。`.venv` があると、Poetry は Python を探さずにそれを使う
  - テスト45件・Ruff・Ruff の整形・mypy が通ることを確かめた

### 2026-10-25

- 持ち主の指示で、issues-human.md は人が `--` より下に箇条書きで書き、番号と題は Claude Code が取り出す前に振る形にした（`.claude/rules/polish.md`）
- main を取り込んだ（`fa8b701`・`5323358`）。衝突は無かった。main 側に頼んでいた CLAUDE.md と progress.md の直しは、main の `52cd6f0` で済んでいた
- issues-human.md の4件に H-01〜H-04 を振り、人と仕様を決めた（specs/ は書いていない）
  - H-01: `--debug` は、推論の文を薄い色で本文の前に出し、本文と推論の文のほかの欄を JSON で出す（途中の行では、毎回同じ形で来る model・created_at・done を除く）。`--debug raw` は、届いた行をそのまま出す
  - H-02: 端末のベル（`\a`）。応答が終わった回と誤りの回に鳴らし、Ctrl-C で止めた回は鳴らさない。既定で鳴らし、`--no-bell` で止める
  - H-03: 入力の後と数値の行の後に空行を入れ、数値の行を薄い色にする。誤りの行は薄くしない
  - H-04: 行末の `\` で続ける。bracketed paste で、貼り付けた複数行を1つの依頼にする
- H-01〜H-04 を実装した（`287b60e`・`9b97898`・`0d649b9`・`7943d12`）。色とベルは、出力が端末のときだけ使う
- code-reviewer の指摘と、自分で気づいた点で H-04 を直した（`4f6a60e`）: 依頼の途中の Ctrl-D は REPL を終えずに依頼を取り消す・末尾の改行を除く・矢印キーなどを打った依頼は送らない（ECHOCTL を切ったので、画面のカーソルだけが動き、依頼の中身と食い違うため）。canonical mode から来る制限（1行の長さの上限・貼り付けた制御文字）は C-06 に書いた。行の編集は C-05 に書いた
