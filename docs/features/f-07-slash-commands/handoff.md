# F-07 引き継ぎ

F-07 を実装したセッション（worktree 側）から、人の問いに答えるセッション（main 側）と、後のセッションへの引き継ぎである。人が読む想定ではない。書き方は `.claude/rules/docs.md` の「handoff.md」。

## 進み具合

- 段: **実装が済んだ**（2026-10-28）。main に取り込み、人が読む・試す段へ進める
- branch: `f-07-slash-commands`（main の `eceac9c` から作った）
- commit:
  - `b2b2877`: `spec.md` と、この引き継ぎの始めの版
  - `cdf8487`: コード・テスト・試す材料（`tasks/f-07-slash-commands/`）・README
  - `2396792`: `implementation.md`・`docs/features.md`・`docs/how-coding-agents-work.md` の「コマンド（slash commands）」の節
  - この引き継ぎの書き直し（この commit）
- テスト: 341件が通る（main の `eceac9c` の274件に、F-07 で67件を足した。直したものを含む）。Ruff・Ruff の整形・mypy（strict）も通る
- コードの見直しのエージェント（Claude Code の subagent）に見せ、指摘の多くを直した（下の「見直しで直したこと」）
- 実物のモデルでは走らせていない（CLAUDE.md の worktree 側）。試すのは main 側で行う

## main 側に頼むこと

- **取り込む**: `git merge f-07-slash-commands`（`/merge-feature f-07-slash-commands`）。main は `eceac9c` の後に `01f8c74`（`--directory`）・`8b9aed9`（Claude Code が実物のモデルで走らせる設定）・`c1bcf86` を積んでいるので、早送りにはならない。`git merge-tree --write-tree f-07-slash-commands main` では、文字の衝突は出なかった（2026-10-28。下の「main と衝突しそうな所」）
- **progress.md**: worktree 側の branch は `f-07-slash-commands` である
- **人に消してもらうもの**（Claude Code は消さない）: 材料の判定を確かめたときに、worktree の `tasks/f-07-slash-commands/project/__pycache__/` ができた（git には入らない）。main には無い。`cp -R` で写すと一緒に写るが、害は無い: `rm -rf tasks/f-07-slash-commands/project/__pycache__`（worktree の中）
- **outbox の機能の記録**（`docs/outbox/F-07-…md`）: 実装の要点・設計の選択・読む順の案内（案）は、この引き継ぎから写す
- **Claude Code が実物のモデルで走らせるとき**（main の `8b9aed9` の CLAUDE.md）: 依頼のファイルを標準入力に渡す走らせ方では、`/` で始まる行がコマンドになる。`/help`・`/context`・`/clear` はモデルを呼ばずに処理され、`/exit` で終わる。自作のコマンドは、写しの `.local-coding-agent/commands/` に置けば、依頼のファイルの1行 `/fix test_temperature.py` で呼べる。`.claude/agent-settings.json` を写しの `.local-coding-agent/settings.json` に置く手順は、`commands/` と同じディレクトリなので、材料の `cp -R` の後に置けばよい
- **上流に上げてよいこと**: 下の「worktree の運用で分かったこと」（WebFetch の結果がリポジトリの外に保存された・Grep と Glob の道具が無い）

## 仕様を決めるときに人と話したこと

- 持ち主の始めの指示: 「F-07 を実装せよ」
- Claude Code は、仕様の案（コマンドとみなす行・組み込み `/help`・`/clear`・`/mode`・`/exit`・自作のファイルの置き場と前付け・`$ARGUMENTS`・名前が重なれば組み込みが勝つ・走行の記録の1件・作らないこと）を示し、4つを問うた
- **組み込みの組**: 「加えて `/context`」を選んだ（「`/help`・`/clear`・`/mode`・`/exit`（推奨）」「`/help`・`/clear`・`/mode` だけ」を選ばなかった）。選んだ案の説明は「今の履歴の発言の数と、最後の要求の入力トークン数を出す。F-12（文脈の要約）の前に、履歴の大きさを見られる」。推奨の4つに `/context` を足した5つとして読んだ（持ち主に確かめていない）
- **自作のコマンドの置き場**: 「作業ディレクトリだけ（推奨）」を選んだ（`.local-coding-agent/commands/<名前>.md`）。家のディレクトリ・`.claude/commands/` は読まない
- **引数**: 「`$ARGUMENTS` と、無ければ末尾（推奨）」を選んだ（Claude Code と同じ）。`$0`・`$1` は作らない
- **モデルに渡す形**: 「名前も `<metadata>` に入れる」を選んだ（「中身の文だけ（推奨）」を選ばなかった）。送った時刻と並べて `コマンド: /<名前> <引数>` を `<metadata>` に書く。モデルが、どのコマンドから来た依頼かを知れる
- `/mode` の名前・知らない名前を誤りにする・頭に空白で依頼として送る、などの案のほかの部分は、問わずに案のまま進めた
- 機能のディレクトリの名前と branch の名前は `f-07-slash-commands` にした（CLAUDE.md の `f-NN-<機能名>`）
- `spec.md` は、問いの答えを入れて Claude Code が書き、持ち主に改めて見せずに実装へ進んだ（F-04〜F-06 と同じ）。持ち主が `spec.md` を読んで異論があれば、main 側で受ける

## 実装の全体像

### ファイル

| ファイル | 役目 | 主な名前 |
|---|---|---|
| `local_coding_agent/commands/parse.py` | 行がコマンドか・名前と引数に分ける | `parse_command`・`CommandLine`・`NAME` |
| `local_coding_agent/commands/custom.py` | 自作のコマンドのファイルを探す・読む・前付け・引数の入れ方・一覧 | `find_custom`・`parse_custom`・`split_front_matter`・`expand`・`list_custom`・`CustomCommand`・`Listed`・`CommandError`・`COMMANDS_PATH`・`PLACEHOLDER` |
| `local_coding_agent/commands/builtin.py` | 組み込みのコマンドの処理と説明・`/help` の一覧・`/context` の1行 | `BUILTINS`・`Builtin`・`find_builtin`・`run_builtin`・`help_text`・`context_line`・`CLEARED` |
| `local_coding_agent/cli/conversation.py` | REPL が会話の間に持つもの | `Conversation`（`session`・`history`・`turn`・`input_tokens`・`finished`・`next_turn`） |
| `local_coding_agent/cli/repl.py` | 行を、組み込み・自作・依頼に振り分ける。走行の記録の `command` の1件 | `run`・`handle_line`・`_send_custom`・`_send`・`_show`・`CommandKind` |
| `local_coding_agent/loop/turn.py` | 入力トークン数を返す。依頼にコマンドの行を付けて受ける | `TurnResult`・`run_turn(…, command=None)`・`_input_tokens` |
| `local_coding_agent/model/messages.py` | 利用者の発言のメタデータに、コマンドの行を足した | `Message.command`・`user_text(…, command=None)`・`metadata_text`・`COMMAND_LABEL` |
| `local_coding_agent/model/ollama_messages.py` | 変換の表の docstring だけ（`sent_at・command`） | |
| `local_coding_agent/context/system_prompt.py` | 既定の指示の `<metadata>` の項 | `DEFAULT_INSTRUCTIONS` |
| `local_coding_agent/__main__.py` | 起動の行に `コマンド: /help で一覧` | `main` |
| `tasks/f-07-slash-commands/` | 試す材料（`project/` と README） | |
| `tests/test_commands_parse.py` | 行の見分け | |
| `tests/test_commands_custom.py` | 前付け・説明・引数の入れ方・ファイルの読み取り・一覧（本物の一時ディレクトリ。権限の誤りは `mock`） | |
| `tests/test_commands_builtin.py` | 組み込みの5つ・引数を取らないコマンド・`/help` の一覧の形 | |
| `tests/test_repl_commands.py` | REPL の中（偽物のモデル）: 組み込みはモデルを呼ばない・`/clear`・`/context`・`/mode` で次の判定が変わる・`/exit`・知らない名前・依頼になる行・自作のコマンドの送る形と記録・組み込みが勝つ・空・読めない・入力待ちの Ctrl-C | |
| `tests/test_loop.py` | `InputTokensTest`（入力トークン数）。`Run` が `result` を持つ | |
| `tests/test_messages.py`・`tests/test_context.py`・`tests/test_main.py`・`tests/test_thinking.py` | `<metadata>` のコマンドの行・既定の指示・起動の行・`run_turn(...).history` | |

依存の向き: `cli/repl.py` → `commands/builtin.py`・`commands/custom.py`・`commands/parse.py`・`loop/turn.py`・`cli/conversation.py`。`commands/builtin.py` → `cli/conversation.py`・`commands/custom.py`・`permissions/policy.py`（`MODES`・`is_mode`）・`model/messages.py`。`commands/custom.py` → `commands/parse.py`（`NAME`）。`cli/conversation.py` → `loop/session.py`・`model/messages.py`。`loop/` は `commands/` を知らない。

### データの流れ（1行）

1. `repl.run` が `Conversation(session)` を作り、`finished` になるまで `session.read_line("> ")` で1行を読む（EOF で終わる・入力待ちの Ctrl-C は改行を出して次を読む・空の行は捨てる）
2. `handle_line`: `parse_command(line)` が `None` なら `_send(conversation, line)`（F-06 までの依頼と同じ）
3. コマンドなら `find_builtin(name)` → あれば `run_builtin`（引数を取らないコマンドに引数があれば `/<名前> は引数を取らない`）→ 新しい `Conversation` と画面の文 → `_show` が文を出し、記録に `command` の1件（`kind: builtin`）
4. 組み込みでなければ `find_custom(cwd, name)`: ファイルが無ければ `None` → 知らない名前の誤り（`kind: unknown`）。読めなければ `CommandError` → `誤り: /<名前> を読めない: <理由>`（`kind: custom`）
5. あれば `_send_custom`: `expand` で引数を入れる → 本文が空か、置き換えた文が空なら誤り → `[コマンド] …` を出し、記録に1件（`turn`・`source`・`text`）→ `_send(conversation, text, command.line)`
6. `_send`: `run_turn(session, history, text, next_turn, command)` → `TurnResult` の `history` と `input_tokens`（`None` なら前の値を保つ）で新しい `Conversation`
7. `run_turn` は、`user_text(text, sent_at=now(), command=command)` を足して回を始める。送る直前に `metadata_text` が `<metadata>` に `送った時刻:` と `コマンド:` の行を入れる（`model/ollama_messages.py` の `_content`）

## 設計の選択と理由・捨てた案

- **REPL の状態を `Conversation` にまとめた**: 組み込みのコマンドは、履歴（`/clear`）・許可のモード（`/mode`）・終える印（`/exit`）を変える。どれも「受けて新しいものを返す」関数にすると、コマンドが REPL の変数を直に書き換えずに済み、テストでも1つの値を比べればよい。捨てた案: REPL の局所変数のまま、コマンドごとに返す値の形を変える（コマンドが増えると、REPL の中の分岐が増える）
- **`Session` は凍ったまま、`/mode` が替えた `Session` を作る**: F-03 から `Session` は「会話の間は変えない」ものだったが、`replace` で作り直すので、ループの側は変えずに済んだ。`Session` の docstring（「起動のときに1度作り、会話の間は変えない」）は直していない。厳密には `/mode` で作り直す（下の「分かっている問題」）
- **`run_turn` の戻り値を `TurnResult` にした**: `/context` の入力トークン数は、ループの中の応答（`Done.stats`）にしか無い。捨てた案: モデルの発言（`Message`）に数を持たせる（`assistant_text` との等しさを比べる既存のテストが崩れる。Messages API の発言にも無い欄）・走行の記録の書き出し先を包んで覗く（読みにくい）
- **入力トークン数は Ollama の数をそのまま出す**: 手元にはトークンを数える道具が無い。Claude Code の `/context` は区分ごとに出すが、ここは合計だけである
- **コマンドの行を `<metadata>` に入れる**: 持ち主の選択。F-02 の送った時刻と同じ形（本文の前の文）にしたので、変換の層（`ollama_messages.py`）は変えずに済んだ。`Message.command` は、自作のコマンドで送った発言だけが持つ
- **名前の形を英小文字・数字・`-`・`_` に限った**: `.` と `/` を許さないので、`/../x` で置き場の外を指せない。`/tmp/a.txt` のようなパスを書いた依頼を、コマンドと取り違えない。Claude Code の名前の決まりは、このセッションでは確かめていない
- **知らない名前は送らない**: `/tmp を見て` を依頼として送ると、打ち間違えたコマンド（`/claer`）もモデルに渡る。送らずに誤りにし、頭に空白で送れるようにした
- **組み込みを先に探す**: 自作のファイルで `/clear` を上書きできると、組み込みの振る舞いが作業ディレクトリによって変わる。一覧で呼べないことを示す
- **自作のコマンドは呼ぶたびに読む**: 起動のときに読むと、書き換えるたびに起動し直すことになる。読む量は1ファイルで小さい
- **前付けは `description` だけを読む**: 標準ライブラリに YAML の読み手が無いので、`key: value` の行を見るだけにした。ほかの欄を誤りにしないのは、Claude Code のファイルを写しても使えるため
- **本文が空なら、引数があっても送らない**: 見直しの指摘。仕様の「置き換えた文が空なら」のままだと、`ARGUMENTS: <引数>` だけの依頼になる
- **`/help` の自作の一覧に `Listed` を返す**: `custom.py` が「呼べない理由」まで決め、`builtin.py` は並べるだけにした。組み込みと同じ名前かは、組み込みの名前を受けて `custom.py` が決める（`custom.py` は `builtin.py` を知らない）

### 見直しで直したこと

コードの見直しのエージェント（Claude Code の subagent）の指摘のうち、次を直した。

- **本文が空で引数があると、`ARGUMENTS: <引数>` だけを送っていた**: 本文が空なら送らないようにした（`_send_custom`）
- **置き場の中を見られないと、`/help` で REPL ごと落ちた**（`iterdir` の `PermissionError`）: 置き場を読めないことの1行を一覧に出すようにした
- **同じ回の中で、後の応答が `prompt_eval_count` を持たないと、前の応答の数が消えた**: 前の数を残すようにした（`_input_tokens(outcome, before)`）
- **読めない理由に手元の絶対パスが入った**（`OSError` の文）: `strerror` だけにした（`_reason`）
- **読みやすさ**: `_show` の後ろの引数をキーワードだけにし、`kind` を `Literal` にした（`CommandKind`）。次の回の番号を2か所で計算していたのを、`Conversation.next_turn` にした
- **テスト**: 入力待ちの Ctrl-C と EOF・本文が空で引数がある・本文が `$ARGUMENTS` だけで引数が無い・置き場が読めない・読めない理由・後の応答に数が無い、を足した

直さなかった指摘:

- **置き場の `.md` がシンボリックリンクなら、作業ディレクトリの外を読める**: 置き場は利用者が書くもので、読むのは利用者が `/<名前>` を打ったときだけである。`implementation.md` に、辿って読むことを書いた。モデルが `run_command` で置き場にリンクを作れば、利用者が呼んだときに外のファイルが依頼の本文になる（読むのはモデルではなくハーネスだが、中身はモデルに渡る）
- **見直しのエージェントの「branch が main の後ろにある」**: CLAUDE.md の取り決めどおり、main の取り込みは main 側が行う（上の「main 側に頼むこと」）

## 実装前の仕様との違い

`implementation.md` の「実装前の仕様との違い」の表のとおり。大きいのは、本文が空なら引数があっても送らないこと（見直しの指摘）で、ほかは仕様に書いていなかった細部（置き場が読めないときの一覧・読めない理由・入力トークン数の残し方・記録の `source` と `output`・`Conversation`）である。振る舞いの大筋（行の見分け・組み込みの5つ・置き場・前付け・`$ARGUMENTS`・`<metadata>`・誤り・記録の欄）は仕様のとおりである。

## テストで確かめたこと・確かめていないこと

- 確かめた（F-07 で足した・直したもの）:
  - 行の見分け（`ParseCommandTest`）: 名前だけ・引数の前後の空白・タブ・`-`・`_`・数字・コマンドでない行11通り（頭に空白・`/tmp/a.txt`・`/`・`/ help`・大文字・`-` と `_` で始まる・`.` を含む・`/../x`・日本語）
  - 自作のコマンド（`FrontMatterTest`・`DescriptionTest`・`ExpandTest`・`FindCustomTest`・`ListCustomTest`）: 前付けの有る無し・閉じない前付け・`---` の後ろの空白・空のファイル・`description` の囲み（`"…"` の中の `:`）・ほかの欄を使わない・説明の代わりの最初の行・`$ARGUMENTS` の複数か所と空の引数・末尾の `ARGUMENTS:`・空の本文・呼ぶたびに読む・無いファイル・ディレクトリ・UTF-8 でない・読めない理由に絶対パスが入らない・一覧の並び（`.md` だけ・ディレクトリを除く）・呼べない理由3つ・置き場が読めない
  - 組み込み（`test_commands_builtin.py`）: 5つの名前と順・`/clear` が履歴とトークン数を空にし、回の番号を保ち、受けたものを書き換えない・`/context` の数え方（知らせの付いた道具の結果）と `まだ無い`・`/mode` の表示と、モードだけを替える（規則は残る）・知らないモード・`/exit`・引数を取らない4つ・`/help` の列の揃えと呼べない理由と `（無し）`
  - REPL（`test_repl_commands.py`）: 上の「ファイル」の表のとおり
  - ループ（`InputTokensTest`）: 最後の応答の数・止まった回は前の歩みの数・1つも届かない回・数えない API・後の応答に数が無い
  - 既定の指示が `「コマンド: 」の行` に触れている・起動の行の最後
- Claude Code が手元で確かめた（モデルは使っていない）: `tasks/f-07-slash-commands/project/` で、`/help` の一覧と3つのコマンドの置き換えた文を、`help_text`・`list_custom`・`expand` に掛けた。判定のコマンド（`tasks/f-05-run-command/judge.py`）は、写したばかりの状態で4件のうち3件が失敗し、終了コード 1 だった
- 確かめていない:
  - 実物のモデルが、`<metadata>` のコマンドの行をどう扱うか（依頼の一部と読むか・無視するか）・末尾の `ARGUMENTS:` を読むか
  - 実物の端末での表示（`/help` の列の揃え。日本語の説明は揃えの外なので、名前の列だけが揃う）
  - `main()` から `/help` を打つまでの通し（`repl.run` はテストで偽物の入力を渡した）
  - main の `--directory` と合わせたときの、`--directory` の下の `.local-coding-agent/commands/` を読むこと（`Session.cwd` を使うので読むはずだが、取り込んだ後のテストは走らせていない）

## 人が問いそうなことと答え

- **組み込みのコマンドはモデルに何か渡るか**: 何も渡らない。`/help` を打っても、要求は送られず、数値の行も出ない。走行の記録にも `request` の件は無く、`command` の件だけがある
- **`/clear` の後、モデルは前の話を覚えているか**: 覚えていない。モデルの API は会話の状態を持たず、ハーネスが次の要求に前の発言を入れないだけである（F-01 で確かめたことの裏返し）。Ollama の KV キャッシュ（前の要求の計算の使い回し）は、速さに効くだけで、モデルが読む中身には影響しない
- **自作のコマンドとモデルへの依頼はどう違うか**: モデルから見ると、`<metadata>` の `コマンド:` の行が付くほかは、打った依頼と同じである。ファイルを読み、引数を入れるのはハーネスである
- **`/mode` で変えたモードは残るか**: その会話の間だけ。設定ファイルには書かないので、次の起動では設定ファイル（または `--permission-mode`）のモードに戻る
- **`/context` の数はどこから来るか**: Ollama の応答の `prompt_eval_count`。最後に終わりまで届いた応答の要求の、入力の全体の数である（使い回した分も含む）。次の要求は、これに最後の応答と次の依頼を足したものになる
- **なぜ `/tmp を見て` が誤りになるのか**: 名前の形（英小文字など）に合う語で始まるので、コマンドとして探し、見つからないからである。打ち間違えたコマンドをモデルに送らないためで、依頼として送るなら頭に空白を置く
- **Claude Code の自作のコマンドのファイルは使えるか**: `.claude/commands/<名前>.md` を `.local-coding-agent/commands/` に写せば、本文と `description` と `$ARGUMENTS` は効く。`$0`・`$1`・`` !`コマンド` ``・`@ファイル`・`allowed-tools` などは効かない（`$1` などは文字のまま送られる）
- **自作のコマンドで許可は変わるか**: 変わらない。Claude Code の `allowed-tools` のような、その回だけ問わずに通す仕組みは作っていない

## 分かっている問題・残したこと

- **`Session` の docstring**: 「起動のときに1度作り、会話の間は変えない」のままだが、`/mode` は許可を替えた `Session` を作り直す。書き換えはしない（凍ったまま）ので、「変えない」は個々の `Session` には当たる
- **置き場のシンボリックリンク**: 辿って読む（上の「直さなかった指摘」）
- **`/help` の列**: 名前の列だけを揃える。名前が長い自作のコマンド（例えば 30 字）があると、全ての行がその幅になる
- **`$` の印**: `$ARGUMENTS` のほかの `$…`（`$1`・`$HOME`）は、字のまま送る
- **履歴に残らない組み込みのコマンド**: `/clear` と `/mode` をしたことは、モデルには分からない。走行の記録の `command` の件で分かる
- **`tasks/f-02-system-prompt/short.md`**: 既定の指示とさらに離れた（F-07 で `<metadata>` の項を足した）
- F-06 から引き継いだもの: 会話の途中でモードを変える（F-07 で `/mode` として作った）・問いの場で「以後は問わない」を選べない・照合の限界

## main と衝突しそうな所

F-07 は、main の次のファイルを直した。main は分岐の後に `01f8c74`（`--directory`）・`8b9aed9`・`c1bcf86` を積んだ。`git merge-tree` では文字の衝突は出なかったが、取り込んだ後にテストを走らせて確かめる。

- `local_coding_agent/__main__.py`: F-07 は `describe(loaded)` の行の後に1行足しただけ。main は docstring・`parse_args`・`cwd` と走行の記録の置き場を直した（離れた行）
- `tests/test_main.py`: F-07 は `PermissionsAtStartTest` に1つ足した（`test_start_lines_end_with_how_to_list_commands`。起動の出力が `コマンド: /help で一覧\n` で終わる）。main は末尾に `DirectoryTest` を足した。main の `DirectoryTest` は `assertIn` で見るので、F-07 の行で崩れない
- `README.md`: F-07 は「できること」の表・画面の例・使い方の「slash commands」と「Ctrl-D」と「走行の記録」の項・材料の項を直した。main は引数の表に `--directory` の行を足した
- `local_coding_agent/cli/repl.py`（書き直した）・`loop/turn.py`（`run_turn` の戻り値が `TurnResult` に変わった。main で `run_turn` を呼ぶコードやテストを足したら、`.history` を付ける）・`model/messages.py`・`context/system_prompt.py`
- `tests/test_loop.py`・`tests/test_thinking.py`（`run_turn(...).history`）
- `docs/features.md` の表（F-07 の行を足しただけ）・`docs/how-coding-agents-work.md`（「コマンド」の節と、ハーネスとモデルの分担の表の1語）

## worktree の運用で分かったこと

- **WebFetch の結果が大きいと、リポジトリの外に保存される**（F-03〜F-06 と同じ）: `https://code.claude.com/docs/en/commands` は、`prompt` を絞っても結果が 56.7 KB で、Claude Code のセッションのディレクトリに保存された。保存先は読んでいない（progress.md の申し送り）。組み込みのコマンドと `/context`・モードの切り替えは、WebSearch（`allowed_domains` を `code.claude.com`）の結果で確かめた。`https://code.claude.com/docs/en/slash-commands` は skills の頁に替わっていて（117,904 字）、始めの 100,000 字だけが答えに使われた
- **Grep・Glob の道具が、このセッションにも無かった**（F-05・F-06 と同じ）。探すのは `git grep` と Read で行った
- **整形は `ruff format <ファイル>` で行った**: 新しく書いたテストとコードの整形に使った。Edit・Write の道具を通らない書き換えだが、触ったのは F-07 で書いたファイルだけで、hook が守るパスではない
- **見直しのエージェントは読むだけで指摘を出した**（`python -c` などは走らせないよう頼んだ）。指摘は Claude Code がテストを書いて確かめた
- `.venv/` は、前のセッションが作ったものがそのまま使えた。`poetry install` は走らせていない
- main の取り込みを試すのに `git merge-tree --write-tree` を使った（作業ツリーと branch を変えない）

## 読む順の案内（案）

呼ばれる側を挙げるときは、それを呼ぶ入口を一緒に挙げる（F-01 からの申し送り）。

1. `local_coding_agent/cli/repl.py` の `run` と `handle_line`（`__main__.py` の `main` から `repl.run(session)` で呼ばれる）: 行を、依頼・組み込み・自作に振り分ける所。F-07 の流れの中心
2. `local_coding_agent/cli/conversation.py`（`repl.py` が作り、組み込みのコマンドが受けて返す）: REPL が会話の間に持つもの
3. `local_coding_agent/commands/parse.py`（`handle_line` の最初に呼ばれる）: コマンドとみなす行
4. `local_coding_agent/commands/builtin.py`（`handle_line` の `find_builtin`・`run_builtin`）: 組み込みの5つ。`/clear` と `/mode` が `replace` で新しいものを作る所
5. `local_coding_agent/commands/custom.py`（`handle_line` の `find_custom`・`_send_custom` の `expand`・`/help` の `list_custom`）: ファイル・前付け・引数の入れ方
6. `repl.py` の `_send_custom`・`_send` → `local_coding_agent/loop/turn.py` の `run_turn`（`TurnResult` と `command`）→ `local_coding_agent/model/messages.py` の `metadata_text`（`ollama_messages.py` の `_content` から呼ばれる）: 自作のコマンドの文がモデルに届くまで
7. `local_coding_agent/context/system_prompt.py`: 既定の指示の `<metadata>` の項
8. テスト: `tests/test_repl_commands.py`（REPL の振る舞いを掴む）→ `test_commands_parse.py` → `test_commands_builtin.py` → `test_commands_custom.py` → `test_loop.py` の `InputTokensTest`
9. `tasks/f-07-slash-commands/`（README → `project/.local-coding-agent/commands/` の3つ）と、試した後の走行の記録（`command` の件と、次の `request` の最後の発言）

## 問いと答えの記録

main 側のセッションが、人から来た問いと答え・直したことを足す。

### main への取り込み（2026-10-28）

- `/merge-feature f-07-slash-commands` で取り込んだ（`40a8ab7`。基点 `2efe1b4`）。main は分岐（`eceac9c`）の後に、上の「main 側に頼むこと」が挙げた `01f8c74`・`8b9aed9`・`c1bcf86` のほかに、F-06 の確認の間の直し（`de294e6`: 規則に理由を添え、拒んだときに理由と意図をモデルに伝える・`baca12d`: コマンドのコメントの中の引用符で deny が外れるのを直し、問いの答えに拒む理由を書ける）と、F-06 の記録を積んでいた。早送りにはならなかった
- 衝突したのは `README.md` と `docs/features.md`。上の「main と衝突しそうな所」と、worktree 側の `git merge-tree`（衝突は出なかった）は、`de294e6` より前の main で見たもので、main の F-06 の直しが同じ所を触っていた
  - `README.md`: main が使い方の「許可」の項の最後の行（照合の限界とその文書へのリンク）と「実行の前の問い」の項（`[y/N/拒む理由]`・規則の理由）を直し、branch がその直後に「slash commands」の項を足した。main の2行を残し、branch の「slash commands」の項をその後に置いた。「Ctrl-D」「走行の記録」と材料の項は、branch の直しのまま（main は触っていない）
  - `docs/features.md`: main が F-06 の行に「計測の結果」を足し、branch が F-07 の行を足した。main の F-06 の行を残し、F-07 の行をその下に置いた
- 意味の衝突は無かった
  - main の F-06 の直しは `permissions/policy.py`（`Decision.rule_reason`・`denial`・`DENIED_NOTE`）・`permissions/confirm.py`（答えの型）・`loop/tool_call.py`・`permissions/settings.py` で、F-07 が使う `MODES`・`is_mode`・`Permissions.mode` は変わっていない。`/mode` は `replace(permissions, mode=…)` なので、理由を添えた規則もそのまま残る
  - `context/system_prompt.py` は、branch が `<metadata>` の項を、main が「規則で拒んだ」の項と「理由: 」の項を直した（間に1行あり、自動で合わさった）
  - `run_turn` の戻り値が `TurnResult` になったが、main は分岐の後に `run_turn` の呼び出しを足していない。ほかのテストの呼び出し（`test_file_tools.py`・`test_permission_loop.py`・`test_run_command.py`）は戻り値を使わない（`git grep` で確かめた）
  - `--directory`（`01f8c74`）と合わせて: `handle_line` は `find_custom(conversation.session.cwd, …)`、`/help` は `list_custom(conversation.session.cwd, …)` を呼び、`main` は `--directory` を解いたパスを `Session.cwd` にするので、`--directory` の下の `.local-coding-agent/commands/` を読む（コードで確かめた。テストは無い）
- 検査: テスト356件（main の289件に、F-07 の67件）・`ruff check`・`ruff format --check`・mypy が通った
- main で直したことは無い
- 持ち主のメモ `docs/features/f-07-slash-commands/memo.md` を空で作った
- 前の機能の guide.md（F-05・F-06）は、F-07 で動かなくなった所が無い。どちらも依頼の文が `/` で始まらず、起動の3行目・`[許可]` の行・走行の記録の `tool` の件は変わらない（起動の行が1行増え、`command` の件はコマンドを打ったときだけ入る）。Ctrl-C と EOF の扱いも基点と同じである。注釈は足していない

### README の材料の見出し（2026-10-28）

- 問い（main 側から持ち主へ）: README の使い方に「コマンドを試す材料」が F-05 と F-07 の2つある。F-07 の方を「slash commands を試す材料」に直してよいか
- 答え: 直してよい
- 直したこと: README の F-07 の材料の項の見出しを「slash commands を試す材料」にし、guide.md の「文書・試す材料・設定」の README の項を合わせた
