# Claude Code の設定

このリポジトリで開発に使う Claude Code の設定を、[要件](requirements.md) からどう書き起こしたかを示す対応表である。書き起こしの手順は `.claude/skills/derive-settings/SKILL.md` にある。

- Claude Code の版: 2.1.308
- 公式の文書を確かめた日: 2026-10-24

## 設定の置き場

| ファイル | 中身 |
|---|---|
| `CLAUDE.md` | 要件の読み込み（`@docs/requirements.md`）と、設定では止められない部分の指示 |
| `.claude/settings.json` | permissions・sandbox・hook の登録 |
| `.claude/hooks/guard_paths.py` | リポジトリの外のファイルを編集する道具の呼び出しを拒む hook |
| `.claude/rules/docs.md` | docs/ の書き方（docs/ の文書を読み書きすると読み込まれる） |
| `.claude/skills/derive-settings/SKILL.md` | 要件から設定を書き起こす手順 |
| `.claude/skills/feature-record/` | 機能の記録を書く手順と雛形 |
| `pyproject.toml`・`poetry.toml` | Python の版・lint と型の検査の設定・仮想環境をリポジトリの中に作る設定 |
| `.gitignore` | 仮想環境（`.venv/`）と一時ファイルの置き場（`.tmp/`）を git に入れない |

## 強制の手段

| 手段 | 何を縛るか | 限界 |
|---|---|---|
| permissions（deny・ask・allow） | 道具の呼び出しを、規則と照合して拒む・人に確かめる・確かめずに通す。照合は deny → ask → allow の順で、どの設定ファイルの deny も allow に勝つ。ask は auto mode でも人に確かめる | Bash の規則はコマンドの文字列で照合する。同じ操作を別の書き方（`/bin/rm`・`sh -c '…'`・Python から呼ぶ、など）にすると一致しない |
| sandbox | Bash のコマンドとその子のプロセスを、OS（macOS では Seatbelt）で縛る。書き込みは作業ディレクトリと一時ディレクトリだけ。ネットワークは許したドメインだけ | Read・Edit・WebFetch などの道具には効かない。sandbox の外で走らせるコマンド（`excludedCommands`）には効かない。削除は縛らない |
| `blockReadsOutsideWorkingDirectories` | Read・Grep・Glob が作業ディレクトリの外を読むのを拒む。sandbox と併せると、sandbox の中のコマンドもホームディレクトリなどを読めない | 利用者の設定で足した作業ディレクトリと、Claude Code が要る `~/.claude` の一部は読める |
| hook（PreToolUse） | 道具の呼び出しの前にスクリプトを走らせ、入力を見て拒む | 登録した道具にしか効かない |
| CLAUDE.md・rule | Claude への指示 | 強制力は無い |
| lint・静的検査 | コードの書き方と型 | コードにしか効かない |

## 対応表

### ファイル削除系の操作の禁止

| 手段 | 設定 |
|---|---|
| deny | `rm`・`rmdir`・`unlink`・`mv`・`find … -delete`・`git rm`・`git mv`・`git clean`・`git restore`・`git reset --hard`・`git checkout -- …`・`git checkout .`・`git stash drop`・`git stash clear`・`git branch -d`/`-D`・`git tag -d`・`git worktree remove`・`poetry env remove` |
| ask | `git checkout`・`git switch`（ファイルを指すと未コミットの変更を捨てるため） |
| CLAUDE.md | 削除が要るときは、消すものとコマンドを示して人に頼む |

止められない部分: 別の書き方の削除（`/bin/rm`・Python の `os.remove` など）。

### リポジトリの外のファイルの編集と読み取りの禁止

| 手段 | 設定 |
|---|---|
| hook | `guard_paths.py` が、Edit・Write・NotebookEdit の対象がリポジトリの外なら拒む（シンボリックリンクは辿った先で判じる） |
| sandbox | Bash のコマンドの書き込みを、作業ディレクトリと一時ディレクトリに限る |
| `blockReadsOutsideWorkingDirectories` | Read・Grep・Glob と、sandbox の中のコマンドの読み取りを、作業ディレクトリに限る |
| deny | 秘匿の場所の読み取り（下の「環境変数と秘匿情報」） |

止められない部分:

- sandbox の外で走る `git` と `poetry` の読み書き（`git` は `~/.gitconfig` と ssh の鍵を読む。`poetry` はリポジトリの外のキャッシュに書く）
- sandbox が許す一時ディレクトリへの書き込み
- 利用者の設定で足した作業ディレクトリの読み取り

### 道具の導入とモデルの取り込み

| 手段 | 設定 |
|---|---|
| `poetry.toml` | `virtualenvs.in-project = true`。仮想環境をリポジトリの中（`.venv/`）に作る |
| ask | `poetry` の全てのコマンド（依存の導入は人と相談するため） |
| deny | リポジトリの外に入れる操作: `uv tool`・`pipx`・`brew`・`pip install`・`ollama pull`/`rm`/`create`/`cp`/`push` |
| sandbox の除外 | `poetry` は自分の置き場（`~/.local`）を読むので、sandbox の外で走らせる |
| CLAUDE.md | 一時ファイルは `.tmp/` に置く |

止められない部分: `poetry` のダウンロードのキャッシュは、リポジトリの外（Poetry のキャッシュのディレクトリ）に書かれる。

### git の remote の操作

| 手段 | 設定 |
|---|---|
| ask | `git push`・`git remote add`/`set-url`/`remove`/`rm`/`rename`/`set-head`/`prune` |
| allow | `git fetch`・`git pull`・`git ls-remote`・`git remote -v` |
| sandbox の除外 | `git` は sandbox の外で走らせる（macOS の sandbox の中からは ssh の remote に届かないため） |
| deny | `git -C …`・`git -c …`（`git -C . push` のような書き方で ask を避けられるため） |
| CLAUDE.md | push しない。remote の操作は基本行わない |

### デプロイと、外部へ影響を及ぼす操作の禁止

| 手段 | 設定 |
|---|---|
| sandbox | `network.deniedDomains` を `["*"]` にし、sandbox の中のコマンドは外へ出られない。拒むドメインは許すドメインに勝つ。許すドメインを空にするだけでは外へ出られた（下の「止まるかを確かめた操作」） |
| deny | `curl`・`wget`・`ssh`・`scp`・`rsync`・`gh`・MCP の全ての道具（`mcp__*`）・`Artifact`・`ArtifactComments`・`ArtifactData`・`RemoteTrigger` |
| allow | WebFetch・WebSearch（読むだけの道具） |

止められない部分: WebFetch の URL に載せて送ること。sandbox の外で走る `git` と `poetry` の通信（`git push` は ask）。

手元の Ollama を呼ぶこと: sandbox は全てのドメインを拒むので、今は sandbox の中のコマンドから Ollama に届かない。作ったエージェントを実物のモデルで走らせるときの扱いは、上流で設計の途中である。

### 実物のモデルで走らせるのは、許可の機能（F-06）ができるまで人だけ

| 手段 | 設定 |
|---|---|
| sandbox | 上の `deniedDomains: ["*"]` で、sandbox の中のコマンド（作ったエージェント・`ollama` のコマンドを含む）は手元の Ollama にも届かない |

止められない部分: 無いと見ている。ただし、手元の Ollama が入っていないので、届かないことは試していない。

### 環境変数と秘匿情報の読み取りの禁止

| 手段 | 設定 |
|---|---|
| deny | `env`・`printenv`・`export`（引数なし）・`set`（引数なし）・`security`（キーチェーン）・`$` を含むコマンド（変数の展開とコマンドの置き換え）・Read の `**/.env`・`**/.env.*`・`~/.ssh/**`・`~/.aws/**`・`~/.gnupg/**`・`~/.netrc`・`~/.config/gh/**`・`~/Library/Keychains/**` |

止められない部分: Python などのプログラムの中から環境変数を読んで出すこと。

### 強制のための書き方

| 手段 | 設定 |
|---|---|
| deny | `sh -c`・`bash -c`・`zsh -c`・`eval`・`git -C`・`git -c`・`$` を含むコマンド |
| ask | `cd`（作業ディレクトリはリポジトリの根なので、要らない） |
| CLAUDE.md | ファイルを読む・探すのは Read・Grep・Glob で行い、shell で行わない。web を読むのは WebFetch で行う。言い換えて規則を避けない |

止められない部分: 規則に一致しない全ての言い換え。

### 人と相談して進める作業

| 手段 | 設定 |
|---|---|
| ask | `CLAUDE.md`・`.claude/` の下・`pyproject.toml`・`poetry.toml`・`poetry.lock`・`.gitignore` の編集。`poetry` の全てのコマンド |
| deny | `docs/inbox/` の下の編集（inbox に書くのは上流だけ） |
| CLAUDE.md | 仕様の決定・依存と道具の導入は、人と相談してから行う |

止められない部分: 仕様の決定（CLAUDE.md の指示だけ）。

### 文書・記録・lint

| 要件 | 手段 |
|---|---|
| docs/ の書き方（規則は skill か rule にする） | rule（`.claude/rules/docs.md`） |
| 機能ごとの文書の置き場（`docs/features/f-NN-<機能名>/`・実装前の仕様と計測は直さない） | rule（`.claude/rules/docs.md`）と skill `feature-record` |
| コードは常に Claude Code が書き、人が読む | 要件（CLAUDE.md が読み込む） |
| 機能ごとの記録の項目と書き方 | skill `feature-record`（手順と雛形） |
| 1機能の進め方・inbox と outbox の書式 | 要件（CLAUDE.md が読み込む） |
| 持ち主が直接出した要件は、写しに先に書き、上流へ報告する | 要件（CLAUDE.md が読み込む）と CLAUDE.md（報告は main 側） |
| commit するもの | CLAUDE.md |
| README.md にセットアップ・起動・使い方を書き、機能を足すたびに直す | CLAUDE.md |
| 作業の進行を `docs/progress.md` に記録し、常に更新する | CLAUDE.md と `.gitignore`（git に入れない）。docs/ の rule は当てない |
| main 側で確認し、git worktree（`.worktrees/next`）で次の機能を実装する | CLAUDE.md（分担）と `.gitignore`（`.worktrees/`）。worktree 側のセッションは、作業ディレクトリが worktree なので、`blockReadsOutsideWorkingDirectories` と sandbox で main 側のファイルを読めず、hook で worktree の外を編集できない |
| git worktree（`.worktrees/polish`・branch `polish`）で、作るエージェントのソフトウェア面を改善する。polish は main へマージせず、main を polish へ一方的にマージする | CLAUDE.md（分担）・`.gitignore`（`.worktrees/`）・deny の `Bash(git merge *polish*)`（main と worktree 側で polish を取り込まない） |
| 実装したセッションから、問いに答えるセッションへの引き継ぎ（`handoff.md`） | rule（`.claude/rules/docs.md`）と CLAUDE.md |
| 走行の記録を git に入れない | `.gitignore` の `traces/` |
| テスト・lint・型の検査 | `pyproject.toml` の設定と、CLAUDE.md の「commit の前に走らせる」 |
| 1ファイル 200 行程度・関数 50 行まで（polish 側には当てない） | 要件（CLAUDE.md が読み込む）。lint では検査していない |
| 要件を守っているかを確かめる lint | 無い |

止められない部分: polish を取り込む操作のうち、`git merge …polish…` の形でないもの（`git pull . polish`・`git rebase polish`・`git cherry-pick`・polish の commit の名前を指す `git merge`）。CLAUDE.md の指示だけで守る。

## 止まるかを確かめた操作

2026-10-24 に、設定を置いたセッションで試した。止まらなくても害の無い形で試している。

| 操作 | 結果 |
|---|---|
| `rm .tmp/no-such-file` | deny で止まった |
| `git clean -n` | deny で止まった |
| `echo $HOME` | deny（`$` を含むコマンド）で止まった |
| `env` | deny で止まった |
| `git -C . status --short` | deny で止まった |
| `curl -sI https://example.com` | deny で止まった |
| Artifact の道具 | deny で止まった |
| MCP の道具 | deny で、セッションから外れた |
| `docs/inbox/` の下のファイルの Edit | deny で止まった |
| Read で `/etc/hosts` | `blockReadsOutsideWorkingDirectories` で止まった |
| `ls`（ホームディレクトリ） | sandbox で止まった（Operation not permitted） |
| `touch /claude-sandbox-test` | sandbox で止まった（Operation not permitted） |
| Write で `/claude-guard-test.txt` | hook で止まった |
| Python から `https://example.com` へ接続 | 許すドメインを空にしただけでは**止まらなかった**。`deniedDomains: ["*"]` を足して止まった（host is on the deny list） |
| `git push --dry-run` | ask で人に確かめられた |

試していないもの: `mv`・`git restore` などの、上で試したものと同じ形の deny。`cd` と `poetry` の ask。

許すドメインを空にしただけで外へ出られた原因は、確かめていない。許すドメインは、`allowedDomains` と、どの設定ファイルの `WebFetch(domain:…)` の allow とも合わさる。このリポジトリの allow にある `WebFetch` はドメインを指定しない形で、公式の文書では、この形は sandbox の中のコマンドが届く先を変えない。確かめるには `deniedDomains` を外して試す必要があり、そのあいだ sandbox の中のコマンドが外へ出られるので、行っていない。
