---
name: derive-settings
description: docs/requirements.md の要件から、CLAUDE.md・Claude Code の設定（permissions・sandbox・hook）・rule・lint の設定を書き起こし、docs/claude-code-settings.md の対応表を更新する。要件が変わったとき・Claude Code の版が上がったとき・リポジトリの状態が変わったとき（道具を足したなど）に使う
---

# 要件から設定を書き起こす

[docs/requirements.md](../../../docs/requirements.md) の要件を入力に、このリポジトリの Claude Code の設定を書き起こす。設定に書きたい具体的な内容があるのではなく、要件だけがある。書き起こしは、その時の Claude Code の設定方法と、その時のリポジトリの状態で行う。

## 書き起こすもの

| ファイル | 中身 |
|---|---|
| `CLAUDE.md` | 要件の読み込み（`@docs/requirements.md`）と、設定では止められない部分の指示。要件と同じことは書かない |
| `.claude/settings.json` | permissions（allow・ask・deny など）・sandbox・hook の登録 |
| `.claude/hooks/` | permissions で表せない判定をする hook のスクリプト |
| `.claude/rules/` | 特定のファイルを扱うときだけ要る規則（例: docs/ の書き方） |
| `pyproject.toml`・`poetry.toml` | lint と型の検査の設定・仮想環境の置き場 |
| `.gitignore` | git に入れない生成物と一時ファイルの置き場 |
| `docs/claude-code-settings.md` | 要件と設定の対応表（下の手順 4・5 の結果） |

`.claude/settings.local.json` は手元だけの設定で、git に入らない。書き起こしの対象にしない。

## 手順

### 1. 要件を読む

`docs/requirements.md` の全てを読む。前回からの差分は `git log -p docs/requirements.md` で分かる。

### 2. 今の Claude Code の設定方法を、公式の文書で確かめる

設定の方法は版で変わるので、前回の書き起こしを当てにしない。版は持ち主に、端末で `claude --version` を走らせて確かめてもらう（sandbox の中からは `~/.local` の `claude` を読めず、走らない）。分からなければ、分からないと対応表に書く。

確かめる文書（https://code.claude.com/docs/en/ の下。目次は https://code.claude.com/docs/llms.txt ）:

- `permissions`: 規則の書き方・照合の順・Bash の規則が一致しない書き方・Read と Edit の path の書き方・作業ディレクトリ
- `sandboxing`: sandbox が縛るもの・設定のキー・限界
- `settings-reference`: `permissions.*`・`sandbox.*` のキーの意味
- `hooks`: PreToolUse の入出力
- `permission-modes`: auto mode などの mode と、規則の関係
- `skills`・`memory`: skill・rule・CLAUDE.md の置き方と読み込まれ方

文書は WebFetch で読む。長い文書は、知りたい節を名指しして読む。確かめた日と版は、対応表の冒頭に書く。

### 3. リポジトリの状態を読む

- 言語と版: `pyproject.toml`
- 入っている道具: `pyproject.toml` の依存・`.venv/bin/`
- ディレクトリの構成と、git に入れていないもの: `.gitignore`
- 今の設定: `CLAUDE.md`・`.claude/` の下・`docs/claude-code-settings.md`

### 4. 対応表を作る

要件ごとに、何で強制するかを決める。手段は強いものから選ぶ。

1. sandbox（OS で縛る。Bash のコマンドとその子のプロセスにだけ効く）
2. permissions の deny・ask・allow と、`blockReadsOutsideWorkingDirectories` などの permissions のキー
3. hook（permissions で表せない判定）
4. lint と静的検査（コードにだけ効く）
5. rule と CLAUDE.md の指示（強制力は無い）

要件ごとに、設定では止められない部分（言い換えで避けられる、道具に効かない、など）を書く。`docs/claude-code-settings.md` を、この形で書き直す。

### 5. 持ち主の承認を得る

`CLAUDE.md`・rule・設定の変更と、道具の導入は、持ち主の承認を得てから行う。対応表の案（`docs/claude-code-settings.md`）を示し、前回との違い（強めた・緩めた・新しく止められなくなった）を挙げて問う。lint と静的検査の道具を足す・替えるときは、候補を挙げて問う。

### 6. 書き起こす

承認された範囲で、上の「書き起こすもの」を書く。`.claude/settings.json` は最後に書く。先に書くと、そのあとの操作が止まることがある。

道具は Poetry の開発用の依存として、リポジトリの中の仮想環境（`.venv/`）に入れる。リポジトリの外に入るもの（`~/.local` の道具・`~/.ollama` のモデル）は、人に頼む。

### 7. 禁止のはずの操作が止まるかを確かめる

対応表の deny・ask・hook・sandbox ごとに、1つずつ試す。試すのは、止まらなくても害の無い形にする。

- 対象が無いもの（`rm .tmp/no-such-file`）
- 書き込めない場所（`/` の直下は macOS では書き込めない）
- 何も変えない形（`git clean -n`・`git push --dry-run`）

ask は、人に確かめられることを見る（人が断る）。設定の変更が今のセッションに効かないもの（sandbox など）は、新しいセッションで試す。止まらなかったものは、対応表の「止められない部分」に書く。

### 8. 記録する

設定と対応表を commit する（push しない）。outbox の報告に、確かめた版と日・変えた設定・止まらなかった操作・人に頼むこと（リポジトリの外の削除や導入）を書く。
