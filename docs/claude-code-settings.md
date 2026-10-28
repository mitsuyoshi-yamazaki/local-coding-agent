# Claude Code の設定

このリポジトリで開発に使う Claude Code の設定を、[要件](requirements.md) からどう書き起こしたかを示す対応表である。書き起こしの手順は `.claude/skills/derive-settings/SKILL.md` にある。

- Claude Code の版: 2.1.308。sandbox の除外と `.git` への書き込みの拒否は 2.1.310 で、作るエージェントを実物のモデルで走らせる扱いは 2.1.312 で確かめた
- 公式の文書を確かめた日: 2026-10-24。sandbox の除外と `.git` への書き込みの拒否は 2026-10-25（[sandboxing](https://code.claude.com/docs/en/sandboxing) の Protected paths・[settings-reference](https://code.claude.com/docs/en/settings-reference) の `sandbox.excludedCommands` と `sandbox.filesystem.denyWrite`・[permission-modes](https://code.claude.com/docs/en/permission-modes) の Protected paths）
- 2026-10-28 に確かめた: [sandboxing](https://code.claude.com/docs/en/sandboxing)（localhost へのつなぎは `NO_PROXY` で proxy を通らず、macOS では `network.allowLocalBinding` で決まる・その警告）・[settings-reference](https://code.claude.com/docs/en/settings-reference) の `sandbox.network.*` のキー・[permission-modes](https://code.claude.com/docs/en/permission-modes)（auto mode でも deny と ask が効く・分類器が止めるものに、人の承認も sandbox も無いエージェントのループの起動がある）・[hooks](https://code.claude.com/docs/en/hooks) の PreToolUse の入出力。[permissions](https://code.claude.com/docs/en/permissions) は、結果が大きくリポジトリの外に保存されたので読んでいない（規則の順と Bash の規則の照合は、F-06 の仕様で 2026-10-27 に確かめたものを使う）。skills と memory の文書は、この回は変える所が無いので確かめていない

## 設定の置き場

| ファイル | 中身 |
|---|---|
| `CLAUDE.md` | 要件の読み込み（`@docs/requirements.md`）と、設定では止められない部分の指示 |
| `.claude/settings.json` | permissions・sandbox・hook の登録 |
| `.claude/hooks/guard_paths.py` | リポジトリの外のファイルを編集する道具の呼び出しを拒む hook |
| `.claude/agent-settings.json` | Claude Code が作るエージェントを実物のモデルで走らせるときに、写しの `.local-coding-agent/settings.json` に置く、作るエージェントの許可の設定 |
| `.claude/rules/docs.md` | docs/ の書き方（docs/ の文書を読み書きすると読み込まれる） |
| `.claude/skills/derive-settings/SKILL.md` | 要件から設定を書き起こす手順 |
| `.claude/skills/feature-record/` | 機能の記録を書く手順と雛形 |
| `.claude/skills/merge-feature/SKILL.md` | 機能の branch を main に取り込み、人が確かめるための案内（動作の確かめ方・読む順・既存の実装からの変わり）を示す手順。人が `/merge-feature <branch>` で呼ぶ（Claude が自分からは使わない） |
| `pyproject.toml`・`poetry.toml` | Python の版・lint と型の検査の設定・仮想環境をリポジトリの中に作る設定 |
| `.gitignore` | 仮想環境（`.venv/`）と一時ファイルの置き場（`.tmp/`）を git に入れない |

## 強制の手段

| 手段 | 何を縛るか | 限界 |
|---|---|---|
| permissions（deny・ask・allow） | 道具の呼び出しを、規則と照合して拒む・人に確かめる・確かめずに通す。照合は deny → ask → allow の順で、どの設定ファイルの deny も allow に勝つ。ask は auto mode でも人に確かめる | Bash の規則はコマンドの文字列で照合する。同じ操作を別の書き方（`/bin/rm`・`sh -c '…'`・Python から呼ぶ、など）にすると一致しない |
| sandbox | Bash のコマンドとその子のプロセスを、OS（macOS では Seatbelt）で縛る。書き込みは作業ディレクトリと一時ディレクトリだけ。ネットワークは許したドメインだけ（proxy を通るつなぎ）。localhost へは proxy を通らずに直に繋ぎ、macOS では `network.allowLocalBinding` で通すかが決まる | Read・Edit・WebFetch などの道具には効かない。sandbox の外で走らせるコマンド（`excludedCommands`）には効かない。除外は、呼び出しの中の全てのコマンドが除外の型に一致したときだけ効き、`cd`・リダイレクト・コマンドの置き換えを含む呼び出しは sandbox の中に残る。作業ディレクトリの中の `.git` は、`hooks` と `config` だけを既定で守り（公式の文書の Protected paths）、worktree の `.git`（gitdir を指すファイル）は守らない（実測）。削除は縛らない |
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
| CLAUDE.md | 削除が要るときは、消すものとコマンドを示して人に頼む。branch と stash は、取り込み済みでも消さず、人にも消すよう頼まない |

止められない部分: 別の書き方の削除（`/bin/rm`・Python の `os.remove` など）。

### リポジトリの外のファイルの編集と読み取りの禁止

| 手段 | 設定 |
|---|---|
| hook | `guard_paths.py` が、Edit・Write・NotebookEdit の対象がリポジトリの外なら拒む（シンボリックリンクは辿った先で判じる） |
| sandbox | Bash のコマンドの書き込みを、作業ディレクトリと一時ディレクトリに限る |
| `blockReadsOutsideWorkingDirectories` | Read・Grep・Glob と、sandbox の中のコマンドの読み取りを、作業ディレクトリに限る |
| deny | 秘匿の場所の読み取り（下の「環境変数と秘匿情報」） |

止められない部分:

- sandbox の外で走る `git` と、除外した `poetry` のコマンド（下の「道具の導入とモデルの取り込み」）の読み書き（`git` は `~/.gitconfig` と ssh の鍵を読む。`poetry` はリポジトリの外のキャッシュに書く）
- sandbox が許す一時ディレクトリへの書き込み
- 利用者の設定で足した作業ディレクトリの読み取り

### 道具の導入とモデルの取り込み

| 手段 | 設定 |
|---|---|
| `poetry.toml` | `virtualenvs.in-project = true`。仮想環境をリポジトリの中（`.venv/`）に作る |
| ask | `poetry` の全てのコマンド（依存の導入は人と相談するため） |
| deny | リポジトリの外に入れる操作: `uv tool`・`pipx`・`brew`・`pip install`・`ollama pull`/`rm`/`create`/`cp`/`push` |
| sandbox の除外 | `poetry install`（引数なし）と `poetry add --group dev …` だけを、sandbox の外で走らせる。`poetry` は自分の置き場（`~/.local`）を読むので、sandbox の中では見つからない。ほかの形（`poetry run …`・引数を付けた `poetry install`・ほかのサブコマンド）は除外の型に一致せず、sandbox の中に残って失敗する |
| CLAUDE.md | 一時ファイルは `.tmp/` に置く。コードは `.venv/bin/python` で走らせる（`poetry run` は使わない） |

止められない部分:

- `poetry` のダウンロードのキャッシュは、リポジトリの外（Poetry のキャッシュのディレクトリ）に書かれる
- 除外した `poetry` のコマンドは、リポジトリの中のファイル（`pyproject.toml`・`poetry.toml`・`poetry.lock`・`.venv/`）を読み、それに従って動く。sandbox の中のコマンドはこれらを書き換えられるので、書き換えてから除外したコマンドを走らせると、sandbox の外でコードが走り得る（公式の文書 sandboxing の、作業ディレクトリのファイルに従って動く道具を除外したときの警告。試していない）。`poetry` は ask なので人がコマンドを見るが、確認の画面からは前に書き換えたファイルは分からない
- `poetry add --group dev …` の型には、パス・git・URL の依存を指す形と、`--directory` で別のプロジェクトを指す形も一致する。前者は指した先のコードを sandbox の外で組み立て得る。後者はリポジトリの外のプロジェクトを書き換える。ask で人がコマンドを見て断る

### git の remote の操作

| 手段 | 設定 |
|---|---|
| ask | `git push`・`git remote add`/`set-url`/`remove`/`rm`/`rename`/`set-head`/`prune` |
| allow | `git fetch`・`git pull`・`git ls-remote`・`git remote -v` |
| sandbox の除外 | `git` は sandbox の外で走らせる（macOS の sandbox の中からは ssh の remote に届かないため） |
| deny | `git -C …`・`git -c …`（`git -C . push` のような書き方で ask を避けられるため） |
| deny・sandbox の `filesystem.denyWrite` | main の `.git` と、worktree の `.git`（`.worktrees/*/.git`。gitdir を指すファイル）に、Edit・Write の道具（deny の `Edit(/.git)`・`Edit(/.git/**)`・`Edit(/.worktrees/*/.git)`）からも、sandbox の中のコマンド（`denyWrite` の `./.git`・`./.worktrees/*/.git`）からも書かせない。`git` は sandbox の外で走り、`.git` の `config` と `hooks`、worktree の `.git` と `.git/worktrees/*/commondir` が指す先の `config` と `hooks` に書かれたプログラムを走らせるため。`git` 自体は sandbox の外で走るので、この拒否は `git` の動作に効かない |
| CLAUDE.md | push しない。remote の操作は基本行わない |

止められない部分:

- 入れ子のリポジトリ（サブディレクトリの `.git/`）。ただし、そこで `git` を走らせるには `cd`（ask）か `git -C`（deny）が要る
- `git --git-dir=…`・`git --exec-path=…` のように、sandbox の中から書ける場所（`.tmp/` など）の gitdir や実行ファイルを指す形も `git *` に一致し、sandbox の外で走る（試していない）。CLAUDE.md の「言い換えて規則を避けない」だけで守る

### デプロイと、外部へ影響を及ぼす操作の禁止

| 手段 | 設定 |
|---|---|
| sandbox | `network.deniedDomains` を `["*"]` にし、sandbox の中のコマンドは外へ出られない。拒むドメインは許すドメインに勝つ。許すドメインを空にするだけでは外へ出られた（下の「止まるかを確かめた操作」） |
| deny | `curl`・`wget`・`ssh`・`scp`・`rsync`・`gh`・MCP の全ての道具（`mcp__*`）・`Artifact`・`ArtifactComments`・`ArtifactData`・`RemoteTrigger` |
| allow | WebFetch・WebSearch（読むだけの道具） |

止められない部分: WebFetch の URL に載せて送ること。sandbox の外で走る `git` と、除外した `poetry` のコマンドの通信（`git push` は ask）。

手元の Ollama を呼ぶこと: `allowLocalBinding` で、sandbox の中のコマンドから localhost に届く（下の「作るエージェントを実物のモデルで走らせる」）。proxy を通る外へのつなぎは、`deniedDomains: ["*"]` のまま止まる。

### 作るエージェントを実物のモデルで走らせる

許可の機能（F-06）ができたので、Claude Code も実物のモデルで走らせてよい。作るエージェントに、Claude Code が守る運用の要件にあたる許可の規則を設定し、手元の Ollama だけに届くようにする。

| 手段 | 設定 |
|---|---|
| sandbox | `network.allowLocalBinding: true`。sandbox は localhost へのつなぎを proxy に通さず（`NO_PROXY`）、macOS では、この設定が無いと直のつなぎを止める（公式の文書。下の「止まるかを確かめた操作」）。作るエージェントは `.venv/bin/python` で起動し、その子のプロセス（`run_command` のコマンド）まで sandbox の中で走る。リポジトリの外の読み書き・proxy を通る外への通信・`.git` への書き込みは、Claude Code のコマンドと同じく OS で止まる。`poetry run` で起動する形は除外の型に一致しないので、sandbox の外に出ない |
| 作るエージェントの許可（`.claude/agent-settings.json`） | モード `accept-edits`（作業ディレクトリの中の編集は通し、ほかは問う）。`allow` は `run_command(python3 -m unittest*)`。`deny` は、削除（`rm`・`rmdir`・`unlink`・`mv`・`find … -delete`）・`git`・環境変数（`env`・`printenv`・`export`・`set`・`security`・`$` を含むもの）・外への通信（`curl`・`wget`・`ssh`・`scp`・`rsync`・`gh`）・`ollama`・道具の導入（`pip`・`pip3`・`brew`・`poetry`）・作業ディレクトリの設定ファイル（`.local-coding-agent/`）の書き換え・秘匿のファイルの `read_file`（`.env`・`.env.*`・`~/.ssh` など、Claude Code の Read の deny と同じ場所） |
| 作るエージェントの起動 | 標準入力に依頼のファイルを渡し、問いには答えない。入力の終わりで、問われた呼び出しは全て拒まれる（F-06 の判定）。`--directory <写し>` で、`cd` を使わずに写しを作業ディレクトリにする |
| CLAUDE.md | 走らせるのは人に頼まれたとき（試す段は人が行う）。走らせ方（写し・設定・標準入力）。課題の設定と合わせるときもモードを `allow-all` にしない。Ollama の API は推論と読むだけの口だけを使う。localhost の Ollama のほかには繋がない。worktree 側と polish 側は走らせない |

止められない部分:

- **localhost の全てのポート**: `allowLocalBinding` はポートを限れない。sandbox の中の全てのコマンド（Claude Code のコマンドと、作るエージェントが走らせるコマンド）が、localhost で待つ全てのサービスに繋げ、ポートを開いて待つこともできる（公式の文書の警告）。CLAUDE.md の指示だけで守る
- **Ollama の API の、モデルを取り込む・消す口**: Ollama のサーバは sandbox の外で動くので、`/api/pull` を呼べば、リポジトリの外（`~/.ollama`）に書かれ、外から取り込まれる。Claude Code の deny（`ollama pull` など）と、作るエージェントの deny（`curl`・`ollama`）は、Python から API を呼ぶ形には効かない。CLAUDE.md の指示だけで守る
- **通したテストのコード**: `python3 -m unittest` を通す規則は、テストのコード（モデルが書き換えられる）が行う全てを通す。sandbox はリポジトリの外を止めるが、リポジトリの中の削除と書き換え（写しの外を含む）は止めない。テストのコードが環境変数を出せば、走行の記録に残り、Claude Code がそれを読みうる
- **作るエージェントの規則の照合の限界**（F-06 の `implementation.md` の「照合の限界」）: 別の書き方（`/bin/rm`・`python3 -c`）は `deny` に合わない。ただし `accept-edits` で問いに答えないので、`allow` に合わないコマンドは拒まれる
- **人が見ていないところで走らせるとき**: Claude Code が走らせると、作るエージェントは Claude Code の sandbox の中で走る。課題の繰り返しなどで、それで足りるか（OS のサンドボックスを重ねるか）は、要件のとおり上流が持ち主に問う

### 環境変数と秘匿情報の読み取りの禁止

| 手段 | 設定 |
|---|---|
| deny | `env`・`printenv`・`export`（引数なし）・`set`（引数なし）・`security`（キーチェーン）・`$` を含むコマンド（変数の展開とコマンドの置き換え）・Read の `**/.env`・`**/.env.*`・`~/.ssh/**`・`~/.aws/**`・`~/.gnupg/**`・`~/.netrc`・`~/.config/gh/**`・`~/Library/Keychains/**` |

止められない部分: Python などのプログラムの中から環境変数を読んで出すこと。

### 強制のための書き方

| 手段 | 設定 |
|---|---|
| deny | `sh -c`・`bash -c`・`zsh -c`・`eval`・`git -C`・`git -c`・`$` を含むコマンド |
| ask | `cd`（作業ディレクトリはリポジトリの根なので、要らない。作るエージェントは `--directory` で写しを指す） |
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
| 持ち主が直接出した要件は、写しに先に書き、上流へ報告する。続けて守る指示は、写しに書いて上流へ上げるかを持ち主に問う | 要件（CLAUDE.md が読み込む）と CLAUDE.md（報告は main 側） |
| commit するもの | CLAUDE.md |
| README.md にセットアップ・起動・使い方を書き、機能を足すたびに直す | CLAUDE.md |
| 作業の進行を `docs/progress.md` に記録し、常に更新する（扱うのは main 側だけ） | CLAUDE.md と `.gitignore`（git に入れない）。docs/ の rule は当てない。worktree 側と polish 側のセッションは main 側のファイルを読めないので（下の行）、main 側が書き直すたびに各 worktree へ写しを置き、worktree 側は読むだけにする（CLAUDE.md の指示だけ）。写しも、worktree の `.gitignore` で git に入らない |
| main 側で確認し、git worktree（`.worktrees/next`）で次の機能を実装する | CLAUDE.md（分担）と `.gitignore`（`.worktrees/`）。main への取り込みと、その後の確認の案内は skill `merge-feature`。worktree 側のセッションは、作業ディレクトリが worktree なので、`blockReadsOutsideWorkingDirectories` と sandbox で main 側のファイルを読めず、hook で worktree の外を編集できない |
| git worktree（`.worktrees/polish`・branch `polish`）で、作るエージェントのソフトウェア面を改善する。polish は main へマージせず、main を polish へ一方的にマージする | CLAUDE.md（分担）・`.gitignore`（`.worktrees/`）・deny の `Bash(git merge *polish*)`（main と worktree 側で polish を取り込まない） |
| 実装したセッションから、問いに答えるセッションへの引き継ぎ（`handoff.md`） | rule（`.claude/rules/docs.md`）と CLAUDE.md |
| 走行の記録を git に入れない | `.gitignore` の `traces/` |
| テスト・lint・型の検査 | `pyproject.toml` の設定と、CLAUDE.md の「commit の前に走らせる」 |
| 1ファイル 200 行程度・関数 50 行まで（polish 側には当てない） | 要件（CLAUDE.md が読み込む）。lint では検査していない |
| 要件を守っているかを確かめる lint | 無い |

止められない部分: polish を取り込む操作のうち、`git merge …polish…` の形でないもの（`git pull . polish`・`git rebase polish`・`git cherry-pick`・polish の commit の名前を指す `git merge`）。CLAUDE.md の指示だけで守る。

## 止まるかを確かめた操作

2026-10-24 に、設定を置いたセッションで試した。`poetry` と `.git` の行は、2026-10-25 に、設定を今の形にした同じセッションで試した。止まらなくても害の無い形で試している（`.git` の行は、既にあるファイルに0バイトを足す `: >> <パス>` と、ファイルに無い文字列を置き換える Edit。通っても中身は変わらない）。

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
| `git merge polish`（main 側。polish が main と同じ commit のときに試した） | deny で止まった |
| `which poetry` | sandbox の中では見つからなかった（poetry not found） |
| `poetry run python -c "print('ok')"` | sandbox の中に残り、走らなかった（operation not permitted: poetry・終了コード 127） |
| `poetry install --dry-run` | 引数が付くと除外の型に一致せず、上と同じく走らなかった |
| `poetry install && poetry run python -c "print('ok')"` | 呼び出しの全体が sandbox の中に残り、`poetry install` から走らなかった |
| `poetry install` | sandbox の外で走った（入れるものは無かった） |
| `poetry add --group dev --dry-run ruff` | sandbox の外で走った（ruff は入っているので何も足さなかった。`pyproject.toml` と `poetry.lock` は変わらなかった） |
| `: >> .git/config`・`: >> .git/hooks/pre-commit.sample` | 拒否を足す前から、sandbox の保護のパスで止まった（operation not permitted） |
| `: >> .worktrees/next/.git`・`: >> .worktrees/polish/.git` | 拒否を足す前は**止まらなかった**（書き込みで開けた）。`denyWrite` を足して止まった |
| `: >> .git/worktrees/next/commondir` | `denyWrite` で止まった |
| Edit で `.worktrees/next/.git`・`.git/description` | deny で止まった |
| `git status --short` | 上の拒否を足したあとも、sandbox の外で動いた |
| Python から `http://localhost:11434/api/version`（`allowLocalBinding` を足す前。2026-10-28） | sandbox で止まった（Operation not permitted） |
| 同じ（`allowLocalBinding` を足した後） | 届いた（Ollama 0.40.10）。設定の変更は、同じセッションのまま効いた |
| Python から `https://example.com`（`allowLocalBinding` を足した後） | deny list で止まった（host is on the deny list） |
| `.claude/agent-settings.json` を写しに置き、作るエージェントの判定（`decide`）に掛けた（モデルは使っていない） | `python3 -m unittest`（`-v 2>&1` 付きも）と作業ディレクトリの中の `read_file`・`write_file` は通した。`python3 -m unittest; rm -rf build`・`find … -delete`・`env`・`echo $HOME`・`git status`・`curl …/api/pull`・`.env` と `~/.ssh` の `read_file`・`.local-coding-agent/settings.json` の `write_file` は拒んだ。`cat README.md` と作業ディレクトリの外の `read_file`・`write_file` は問うた |
| 作るエージェントを、`--directory` で写しを指し、標準入力に依頼のファイルを渡して、`qwen3.5:9b` で1回走らせた（F-03 の読む材料） | 作業ディレクトリの中の `read_file` は問わずに通り、`run_command` の `ls` は問われて、入力の終わりで拒まれた。auto mode の分類器には止められなかった |

試していないもの: `mv`・`git restore` などの、上で試したものと同じ形の deny。`cd` と `poetry` の ask（上の `poetry` の行は走ったが、確認が出たかは記録していない）。除外した `poetry` のコマンドに、書き換えたリポジトリの中のファイルを読ませて sandbox の外でコードを走らせる形（上の「道具の導入とモデルの取り込み」の止められない部分）。`git --git-dir=…`・`git --exec-path=…` で、書ける場所を指す形（上の「git の remote の操作」の止められない部分）。localhost の Ollama のほかのポートに届くこと（`allowLocalBinding` の警告のとおりと見ている）と、Ollama の API のモデルを取り込む・消す口（試すと、リポジトリの外が変わる）。

許すドメインを空にしただけで外へ出られた原因は、確かめていない。許すドメインは、`allowedDomains` と、どの設定ファイルの `WebFetch(domain:…)` の allow とも合わさる。このリポジトリの allow にある `WebFetch` はドメインを指定しない形で、公式の文書では、この形は sandbox の中のコマンドが届く先を変えない。確かめるには `deniedDomains` を外して試す必要があり、そのあいだ sandbox の中のコマンドが外へ出られるので、行っていない。
