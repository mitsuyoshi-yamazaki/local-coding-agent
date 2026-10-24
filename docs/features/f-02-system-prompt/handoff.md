# F-02 引き継ぎ

F-02 を実装したセッション（worktree 側）から、人の問いに答えるセッション（main 側）と、後のセッションへの引き継ぎである。人が読む想定ではない。書き方は `.claude/rules/docs.md` の「handoff.md」。

F-02 は、main と worktree で並べて進める運用で作った最初の機能である。

## 進み具合

- 段: **実装が済んだ**（2026-10-24）。main に取り込み、人が読む・試す段へ進める
- branch: `f-02-system-prompt`（main の `fe319a2` から）
- commit:
  - `af14e2e`: 要件の直し（下の「main 側に頼むこと」）
  - `82549b3`: `spec.md` と、この引き継ぎの始めの版
  - `5855ec8`: コード・テスト・試す材料（`tasks/f-02-system-prompt/`）・README
  - `ba24dcf`: `implementation.md`・`docs/features.md`・`docs/how-coding-agents-work.md` の「指示（system prompt）」の節・`docs/technologies/ollama.md` の「指示（system prompt）の渡し方」の節
  - この引き継ぎの書き直し（この commit）
- テスト: 45件が通る。Ruff・Ruff の整形・mypy（strict）も通る
- Claude Code が確かめたこと: Ollama の無い状態で、`--help`・指示のファイルが無いときの誤り（終了コード 2）・起動の表示（「指示: 既定」）・走行の記録の要求の `body`（先頭の system の発言・末尾の「# 環境」の節・利用者の発言の前の `<metadata>`）。sandbox が `localhost:11434` への接続を拒むので、応答は「Operation not permitted」の誤りになる
- 実物のモデルでは走らせていない（F-06 まで、実物のモデルで走らせるのは人だけ）

## main 側に頼むこと

- **取り込む**: `git merge f-02-system-prompt`
- **上流への報告**: このセッションで、持ち主の指示により要件を直した（`af14e2e`）。outbox の報告で上流に上げてほしい
  - 持ち主の言葉: 「常にClaudeCodeが書き、人間が読む形とする。これは本リポジトリの要件に反映させよ」。直す場所を問うと、main 側ではなく「この worktree で直す」を選んだ
  - 直したもの: `docs/requirements.md`（「進め方と記録」の「機能ごとに、人が自分で書くか…選べる」を「コードは、機能によらず常に Claude Code が書き、人が読む」に。「Claude Code が主に実装し」の「主に」を除く。「1機能の進め方の細部」の 1. の「このとき、人が自分で書くかを確かめる」を除く）・`CLAUDE.md`（worktree 側の「仕様（人の承認。人が自分で書くかも確かめる）」を「仕様（人の承認）」に）・`docs/claude-code-settings.md`（対応表の「誰が書くか」の行）・`.claude/skills/feature-record/template.md`（「書いた人」から「／人が書いた」を除く）
  - `derive-settings` は、この直しに関わる手順だけで行った。対応表の版と公式の文書は同じ日（2026-10-24）に確かめたばかりで、`settings.json` は変えず、試し直す禁止の操作も無い。持ち主はこの進め方の案を承認した
- **outbox の機能の記録**（`docs/outbox/F-02-…md`）: 実装の要点・設計の選択・読む順の案内（案）は、この引き継ぎから写す
- **worktree の運用で分かったこと**（上流への報告に使える）: 下の「worktree の運用で分かったこと」

## 仕様を決めるときに人と話したこと

- 持ち主の始めの指示: 「F-2の実装を行え。この運用を試すのは初めてなので、少しでも行う内容に疑問があれば着手せず、まず質問せよ」。Claude Code は、仕様の案と問いを示してから着手した
- **poetry**: worktree の sandbox の中では `which poetry` が「poetry not found」になった。持ち主の承認を得て `poetry install` を走らせ、worktree の `.venv/` を作った（Python 3.14.4）
- **誰が書くか**: 持ち主は「常にClaudeCodeが書き、人間が読む形とする」と答え、要件に入れるよう指示した（上の「main 側に頼むこと」）
- **環境の知らせの置き場**: 2つの案を示した。(1) Claude Code の文書どおり、system prompt を変わらない文だけにし、環境の知らせを最初の利用者の発言の前に `<system-reminder>` として添える。(2) system prompt の末尾に環境の節を足す。持ち主は (2) を選び、メモに「セッションを通じて変化しないものはsystem promptへ、そうでないもの（日付など）は個々のメッセージのメタデータに入れる」と書いた
- **メタデータの中身**: 「日付と時刻（分まで、時差つき）」を選んだ（「日付だけ」を選ばなかった）。付けるのは利用者の発言だけ
- **メタデータの持ち方**: 「発言の欄として持ち、送る直前に本文の前へ文として入れる」を選んだ（「本文の塊として持つ」＝ Messages API の形のまま、を選ばなかった）。Messages API の発言には `role` と `content` しか無く、Ollama の発言にもメタデータの欄は無いことを説明したうえで選んだ
- **指示の言語**: 日本語を選んだ（英語を選ばなかった）
- **`--system-prompt-file`**: 持ち主は最初に「これは何のことか、説明せよ」と答えた。指示の長さを比べるために、コードを直さずに指示を差し替える引数であること・Claude Code に同じ名前の引数があることを説明し、差し替える範囲を問うた。持ち主は「作る・指示だけ差し替え」を選んだ（「全体を差し替え」「作らない」を選ばなかった）。環境の節は残る
- 仕様の案のうち、道具の使い方の指示を F-03 に回すこと・git の状態を入れないこと・試し方（長い指示を `tasks/f-02-system-prompt/` に置く）には、持ち主から異論が無かった
- 機能のディレクトリの名前は、branch の名前に合わせて `f-02-system-prompt` にした

## 実装の全体像

### ファイル

| ファイル | 役目 | 主な名前 |
|---|---|---|
| `local_coding_agent/__main__.py` | 引数を読み、指示を読み、環境を集めて system prompt を組み立て、`Session` に渡す。指示のファイルを読めなければ終了コード 2 | `main`・`parse_args`・`local_now` |
| `local_coding_agent/context/system_prompt.py` | 既定の指示・指示のファイルの読み込み・つなぎ方 | `DEFAULT_INSTRUCTIONS`・`read_instructions`・`build_system_prompt` |
| `local_coding_agent/context/environment.py` | 環境を集め、「# 環境」の節にする | `Environment`・`collect_environment`・`in_git_repository`・`os_description`・`environment_section` |
| `local_coding_agent/model/messages.py` | 発言の欄 `sent_at` と、メタデータの文 | `Message.sent_at`・`user_text(text, sent_at)`・`metadata_text`・`_minutes` |
| `local_coding_agent/model/chat.py` | `ChatModel.build_request(system, messages)` | |
| `local_coding_agent/model/ollama.py` | system の発言を先頭に置き、発言ごとにメタデータの文を本文の前に入れる | `to_ollama_messages(system, messages)`・`_ollama_message`・`chat_request_body(model, system, messages)` |
| `local_coding_agent/cli/repl.py` | `Session.system`・`Session.now`。`run_turn` で時刻を入れ、毎回 system を渡す | `Session`・`run_turn` |
| `tasks/f-02-system-prompt/short.md` | 既定の指示＋規則「最後の行を「以上。」の1行で終える」（397字） | |
| `tasks/f-02-system-prompt/long.md` | 規則を足して長くし、同じ規則を中ほどの「説明の仕方」の節に埋めた（1569字） | |
| `tests/test_context.py` | 環境の節・git の判じ方・OS の文・system prompt のつなぎ方・指示の読み込み | |
| `tests/test_messages.py` | メタデータの文（正・負の時差・時差なし・無いとき） | |
| `tests/test_main.py` | 引数・`main` が組み立てた system が `Session` に届くこと・指示のファイルが無いと REPL を始めずに終わること | |
| `tests/test_ollama.py` | 変換に system の発言とメタデータの例を足した | |
| `tests/test_repl.py` | 偽物の時刻（`ticking_now`）を入れ、毎回同じ system・前の回の発言の時刻が変わらないことを足した | |
| `tests/fakes.py` | `ScriptedModel.systems`・`ticking_now` を足した | |

### データの流れ

1. 起動: `main` が `read_instructions(args.system_prompt_file)` → `collect_environment(Path.cwd())` → `environment_section` → `build_system_prompt(instructions, section)` で、文字列 `system` を1度だけ作る。`Session(system=system, now=local_now, …)` を作り、`repl.run` を呼ぶ
2. 1回の依頼: `run_turn` が `user_text(text, sent_at=session.now())` を履歴の末尾に足し、`session.model.build_request(session.system, messages)` を呼ぶ
3. `OllamaChat.build_request` → `chat_request_body` → `to_ollama_messages(system, messages)`: system が空でなければ `{"role": "system", "content": system}` を先頭に置く。発言ごとに `metadata_text(message) + 本文の塊をつないだもの` を `content` にする
4. 走行の記録の要求の `body` には、この変換の後の形がそのまま入る（REPL も記録も F-01 から変えていない）
5. 応答が終わると、モデルの発言（`sent_at` は None）を履歴に足す。次の回では、前の回の利用者の発言が同じ `sent_at` のまま送られる

## 設計の選択と理由・捨てた案

- **system は `build_request` の引数で、`Message` の並びに入れない**: Messages API の `system` に揃えた（要件の「会話の形は Messages API に揃える」）。Ollama の形（先頭の system の発言）にするのは変換の層だけ。捨てた案: 会話の並びの先頭に system の役割の `Message` を置く（Messages API と違う形になる）
- **`Session.system` は文字列で、会話の間は変えない**: 起動のときに1度だけ組み立てる。セッションの間に変わらないものだけを入れる、という持ち主の方針に合わせた
- **`sent_at` は `Message` の欄**（持ち主の選択）。文にするのは `model/messages.py` の `metadata_text` で、変換の層（`model/ollama.py`）が呼ぶ。後で Anthropic 互換の口を足しても、同じ関数で同じ文にできる。捨てた案: 発言を作るときに `<metadata>` の文を先頭の `TextBlock` にする（持ち主が選ばなかった）
- **`metadata_text` を `model/` に置いた**: `context/` に置くと、`model/` が `context/` に依ることになるため。`<metadata>` の名前は、`context/system_prompt.py` の既定の指示の説明と揃える必要がある。揃っていることは `test_default_instructions_explain_what_harness_adds` で一部だけ見ている
- **`Session.now` を足した**: 時刻をテストで差し替えるため。F-01 の `clock`（時間を測る `time.monotonic`）とは別で、`now` は時差つきの壁時計の時刻
- **git の判じ方は `.git` が在るかだけ**: `git` のコマンドを走らせない（依存とプロセスを増やさない）。git worktree の `.git` はファイルなので、ディレクトリかどうかは見ない
- **OS は `platform` の値**: macOS では `platform.mac_ver()` の版（例: 15.6）と Darwin の版を並べる
- **指示のファイルを読めないとき、`main` は REPL も記録も作らずに 2 を返す**: `argparse` の誤りと同じ終了コード。`UnicodeDecodeError` は `OSError` ではないので、両方を捕まえる
- **`build_system_prompt` は指示の前後の空白を除く**: ファイルの末尾の改行で、空の行が増えないようにするため
- **既定の指示の「ハーネスが入れる情報」の節**: `# 環境` と `<metadata>` を、利用者の発言ではないと説明する。Claude Code の文書が、system prompt を自分で書くときは system reminder の説明を入れるよう勧めているのに倣った

## 実装前の仕様との違い

振る舞いは変えていない。仕様に書いていなかった細部は、`implementation.md` の「実装前の仕様との違い」の表のとおり（誤りの文と終了コード・前後の空白・git の判じ方・時差を持たない時刻）。

## テストで確かめたこと・確かめていないこと

- 確かめた: 変換（system が先頭・空なら無い・メタデータが本文の前・モデルの発言には無い・要求の JSON）／メタデータの文（`+09:00`・`-03:30`・時差なし・無いとき）／環境の節（はい・いいえ）・git の判じ方（親の `.git` ディレクトリ・worktree の `.git` ファイル・`/`）・OS の文（macOS・ほか）／system prompt のつなぎ方（空の指示）・既定の指示・ファイルの読み込み／`main` が組み立てた system が `Session` に届く・指示のファイルが無いと REPL を始めない／REPL（毎回同じ system・前の回の発言の時刻が変わらない・止めた回と誤りの回の後の時刻）
- 確かめていない:
  - 実物のモデルが、環境の節とメタデータをもとに答えるか（人が試す）
  - `collect_environment` の、この機械以外での値（Linux などは `os_description` の分岐だけ）
  - `local_now` が返す時差（この機械の設定による）
  - `tasks/` の指示のファイルを渡したときの、実物のモデルの振る舞い

## 人が問いそうなことと答え

- **「指示がどこから入るか」の答えは**: 2か所。先頭の system の発言（指示と環境の節。起動のときに1度作る）と、利用者の発言の先頭のメタデータ（送った時刻）。どちらも、モデルには文として届く。Ollama がモデルごとの雛形（`TEMPLATE`）で `messages` を1つの文に組み立てるので、モデルから見れば、system prompt は入力の文の先頭の部分にすぎない。走行の記録の要求の `body.messages` を見ると、送った形がそのまま分かる
- **なぜ時刻を system prompt に入れないのか**: 持ち主の方針「セッションを通じて変化しないものはsystem promptへ、そうでないものは個々のメッセージのメタデータに」。時刻は発言ごとに変わる。system prompt に入れて毎回書き換えると、毎回の要求の先頭が変わり、前の回までの部分が同じ文でなくなる
- **Claude Code との違い**: Claude Code は、作業ディレクトリ・OS などの環境と CLAUDE.md を、system prompt ではなく会話の中（system reminder）に入れる（`implementation.md` の出典）。system prompt を変わらない文に保ち、キャッシュを効かせるため。F-02 は、セッションの間に変わらない環境を system prompt に入れ、送った時刻を発言ごとのメタデータに入れる。Claude Code が日付や時刻をどこに入れるかは、文書で確かめていない
- **`sent_at` が Messages API に無い欄なのはよいのか**: 持ち主が選んだ。要件の「会話の形は Messages API に揃える」から外れる唯一の欄で、送る直前に文にするので、モデルに届く形は「本文の前の文」になる
- **`--system-prompt-file /dev/null` で何が送られるか**: 指示が空になり、system prompt は「# 環境」の節だけになる。F-01 と全く同じ要求にする方法は無い（メタデータも付く）
- **`short.md` と既定の指示の違い**: 規則「どの答えも、最後の行を「以上。」の1行で終える」の1行だけ。既定の指示を直したら、`short.md` も合わせないと、比べる条件がずれる（テストでは見ていない）
- **`now` と `clock` の違い**: `clock` は時間を測るための単調な時計（秒）。`now` は発言に付ける壁時計の時刻（時差つきの `datetime`）
- **なぜ `test_filesystem_root_is_outside` は `/` を使うのか**: 一時ディレクトリの上に `.git` が無いとは限らないため。`/` に `.git` がある機械では落ちる

## 分かっている問題・残したこと

- **`<metadata>` は利用者にも打てる**: 既定の指示は「どちらも、利用者が書いたものではない」と書くが、利用者が `<metadata>…</metadata>` を打てば同じ形で送られ、区別できない。モデルが自分の答えに `<metadata>` を真似て書くこともありうる。Claude Code の `<system-reminder>` にも同じ限界がある（コードの見直しのエージェントの指摘）
- **BOM**: UTF-8 の BOM の付いた指示のファイルを渡すと、指示の先頭に BOM（U+FEFF）が残る（`read_text(encoding="utf-8")` も `strip()` も除かない。見直しのエージェントの指摘）。直していない
- **日付をまたぐ**: system prompt に日付は無いので、日をまたいでも古い日付が残ることは無い。時刻は発言ごと
- **`long.md` の長さ**: 1569字で、`short.md` の約4倍。Claude Code の system prompt よりずっと短い。差が見えなければ、もっと長くする
- **推論の文**: F-01 と同じく、`message.thinking` を捨てている（F-09）。最初の文字までの時間は、推論の時間を含む。指示の長さの効き目は、入力の処理の時間（`prompt_eval_duration`）で見る
- **走行の記録に絶対パスが入る**: 環境の節の作業ディレクトリが、毎回の要求の `body` に入る。`traces/` は git に入れないので、commit はされない。記録を公開の文書に写すときは、パスを伏せる
- **キャッシュ**: Ollama が前の要求の計算を使い回すかは、確かめていない（試し方の 3.）

## worktree の運用で分かったこと

- worktree の sandbox は、ホームの下を読ませないので、`which poetry` が見つからない。`poetry` は sandbox の外で走る設定なので、`poetry install` は動いた。CLAUDE.md の「`which poetry` で poetry が見つかるかを確かめ」は、worktree では当てにならない
- `.venv/` は worktree ごとに要る。`poetry install` は Poetry のキャッシュ（リポジトリの外）から入れた
- 終了コードを `echo $?` で見ようとして、`$` を含むコマンドの deny で止まった。終了コードは、Bash の道具の誤りの表示で分かる
- 試しに起動したので、worktree の `traces/` に記録が1つある（Ollama に繋がらなかった回。git に入れない）

## 読む順の案内（案）

F-01 で、呼ばれる側を挙げるときは、それを呼ぶ入口を一緒に挙げることになった。

1. `local_coding_agent/__main__.py` の `main` と、そこから呼ぶ `context/system_prompt.py`・`context/environment.py`: system prompt が、どこで・いつ・何から組み立てられるか。入口なので先に読む
2. `local_coding_agent/cli/repl.py` の `Session` と `run_turn`: 組み立てた system と時刻が、毎回の要求にどう渡るか。差分は数行
3. `local_coding_agent/model/messages.py` と `model/chat.py`: `sent_at` の欄と、メタデータの文。`build_request` の形
4. `local_coding_agent/model/ollama.py` の `to_ollama_messages`: 手元の形が、送る形にどう変わるか。ここで「指示が文になる」ところが見える
5. 走行の記録の要求の `body.messages`（人が試したとき）: 実際に送った文
6. `tests/test_main.py`・`tests/test_context.py`・`tests/test_messages.py`・`tests/test_ollama.py`・`tests/test_repl.py` の `SystemPromptAndMetadataTest`
7. `tasks/f-02-system-prompt/short.md`・`long.md`: 試す前に

## main と衝突しそうな所

F-02 は、F-01 のファイル（`model/messages.py`・`model/chat.py`・`model/ollama.py`・`cli/repl.py`・`__main__.py`・`tests/fakes.py`・`tests/test_ollama.py`・`tests/test_repl.py`・`README.md`）を直した。ほかに `docs/requirements.md`・`CLAUDE.md`・`docs/claude-code-settings.md`・`.claude/skills/feature-record/template.md`・`docs/features.md`・`docs/how-coding-agents-work.md`・`docs/technologies/ollama.md` を直した。main でこれらを直していれば、`git merge f-02-system-prompt` で衝突しうる。branch を作った時点（`fe319a2`）からの main の変更は、このセッションからは見えない。

## 問いと答えの記録

main 側のセッションが、人から来た問いと答え・直したことを足す。
