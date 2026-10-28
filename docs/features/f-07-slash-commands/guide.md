# F-07 slash commands: 確かめる案内

F-07 を試し、コードを読むための案内である。動作の確かめ方・読む順・既存の実装（F-06 まで）からの変わりを書く。

main に取り込んだ後のコードと差分（基点 `2efe1b4` から、取り込んだ commit `40a8ab7` まで）と、[実装前の仕様](spec.md)・[実装した仕様と仕組み](implementation.md)・[引き継ぎ](handoff.md) から書いた。行の番号は、この案内を最後に直した commit のコードのものである（`git log -1 -- docs/features/f-07-slash-commands/guide.md` で分かる）。

## 動作の確かめ方

### 準備

- モデルは `qwen3.5:9b`（F-06 と同じ）。`pyproject.toml`・`poetry.lock` は変わっていないので、`poetry install` は要らない
- 文脈の長さを `ollama ps` で確かめる（[README](../../../README.md) の「Ollama を設定する」）。既定の指示が1文増えたほかは、F-06 と同じ
- 既定の許可のモードは `allow-all`（全部通す）である。材料は設定ファイルを持たないので、`/fix` は問わずに書き換え、テストを走らせる。問わせるには、起動の引数に `--permission-mode ask` を足すか、会話の中で `/mode ask` を打つ

### 起動

リポジトリの根で、試す材料を写し、写しの中で起動する。

```sh
cp -R tasks/f-07-slash-commands/project .tmp/f-07-project
cd .tmp/f-07-project
PYTHONPATH=../.. ../../.venv/bin/python -m local_coding_agent --model qwen3.5:9b
```

`cd` をせず、リポジトリの根で `--directory` を付けて起動してもよい（自作のコマンドの置き場と走行の記録は、どちらも写しの中になる）。

```sh
.venv/bin/python -m local_coding_agent --model qwen3.5:9b --directory .tmp/f-07-project
```

- 起動の行の最後（4行目）に `コマンド: /help で一覧` が出る。3行目は `許可: allow-all・規則 0（設定ファイル無し）`
- 試し直すときは、前の写しを消してから写す（`cp -R` は、写し先のディレクトリがあると、その中に写す）。`/fix` の後の写しは直っているので、`/review` と `/explain` は `/fix` の前に打つか、写し直してから打つ
- 走行の記録は、写しの中の `traces/` に書かれる

### 課題

| 課題 | 打つもの | 期待すること | 画面で見る所 | 走行の記録で見る所 |
|---|---|---|---|---|
| 一覧 | `/help` | 組み込みの5つ（`/help`・`/clear`・`/context`・`/mode`・`/exit`）と、自作の3つ（`/explain`・`/fix`・`/review`）が出る。`/explain` の説明は `"…"` の囲みが外れ、`/review` の説明は本文の最初の行になる。モデルを呼ばない | 一覧の後に数値の行（`[入力 … トークン・…]`）が出ない。名前の列が揃うか | `type` が `command` の件（`kind: builtin`・`output` に一覧）。`request` の件が増えない |
| 引数を末尾に足す | `/review temperature.py` | 本文に `$ARGUMENTS` が無いので、末尾に `ARGUMENTS: temperature.py` が足されて送られる。モデルが `temperature.py` を読み、`celsius_to_fahrenheit` の `- 32` を挙げる。本文が「書き換えない」と言うので、書き換えない（`allow-all` なので、書き換えても止まらない） | `[コマンド] /review → .local-coding-agent/commands/review.md（3 行を依頼として送る）` の後に、打った依頼と同じく回が進む | `command` の件（`kind: custom`・`turn`・`source`・`text` の末尾の `ARGUMENTS: temperature.py`）。答えは人が読んで判定する |
| 説明させる | `/explain temperature.py` | 本文の `$ARGUMENTS` が置き換わり、`temperature.py を読み、何をするファイルかを3行以内で説明せよ。ファイルは書き換えない。` が送られる | `[コマンド] /explain → …（1 行を依頼として送る）` | `command` の件の `text`。答えは人が読んで判定する |
| 自作のコマンドで直させる | `/fix test_temperature.py` | `- 32` を `+ 32` に直し、テストを走らせて通ったことを確かめてから答える | `[コマンド] /fix → .local-coding-agent/commands/fix.md（3 行を依頼として送る）`・`[道具]` の行・`→ 終了コード: 0・N 行` | `command` の件の `text`（`対象のテスト: test_temperature.py`）。次の `request` の件の `body.messages` の最後の発言の `content` が `<metadata>\n送った時刻: …\nコマンド: /fix test_temperature.py\n</metadata>\n` で始まる。判定はリポジトリの根で `.venv/bin/python tasks/f-05-run-command/judge.py .tmp/f-07-project`（終了コード 0 なら通った。写したばかりでは4件のうち3件が失敗する） |
| 会話を消す | 何かを話す（例: `私の好きな色は青だ`）→ `/context` → `/clear` → `/context` → `私の好きな色は？` | 1回目の `/context` は `[文脈] 発言 2（依頼 1・モデル 1・道具の結果 0）・最後の要求の入力 N トークン`。N は直前の数値の行の `入力 N トークン` と同じ。`/clear` は `（会話を消した。次の依頼から新しい会話になる）`。2回目は `発言 0（…）・最後の要求の入力 まだ無い`。モデルは色を知らない | `/context` の2つの行 | `/clear` の後の最初の `request` の件の `body.messages` が、system と最後の依頼の2つだけ。`turn` は `/clear` の後も続けて数える |
| モードを変える | `/mode` → `/mode ask` → `/fix test_temperature.py`（写し直した写しで） | `許可のモード: allow-all` → `許可のモード: allow-all → ask`。その後、`edit_file` と `run_command` の前に問う | `[許可] 問う: モード ask` と `実行してよいか [y/N/拒む理由]: ` | `tool` の件の `permission.reason` が `モード ask`。`/mode` の件の `output` |
| 知らない名前 | `/tmp を見て` → ` /tmp を見て`（頭に空白） | 1つ目は `誤り: 知らないコマンド: /tmp（/help で一覧。依頼として送るなら、行の頭に空白を置く）` で、送らない。2つ目は依頼として送る | 1つ目の後に数値の行が出ない | 1つ目は `command` の件（`kind: unknown`・`turn: null`）だけ。2つ目は `request` の件の最後の発言 |
| そのほかの誤りと終わり | `/help x` → `/mode foo` → `/exit` | `/help は引数を取らない`・`誤り: 知らないモード: foo（ask・accept-edits・allow-all のどれか）`。`/exit` で終わる（Ctrl-D と同じ） | 画面の文 | どれも `command` の件。`/exit` の `output` は空 |

`/help`・`/clear`・`/context`・`/mode`・知らない名前・誤りは、答えに決まった値がある（画面と走行の記録で見る）。`/review`・`/explain` の答えは、人が読んで判定する。

走行の記録の `command` の件の欄は、`line`（打った行）・`name`・`kind`（`builtin`・`custom`・`unknown`）・`turn`（自作のコマンドで送った回の番号。ほかは `null`）・`source`（自作のコマンドのファイル）・`text`（送った本文）・`output`（画面に出した文）である。

### テストで確かめておらず、実物で見てほしいこと

- 実物のモデルが、`<metadata>` の `コマンド: ` の行をどう扱うか（依頼の一部と読むか・無視するか）・末尾の `ARGUMENTS: <引数>` を読むか
- 実物の端末での `/help` の表示。揃えるのは名前の列だけで、日本語の説明は揃えの外である
- 起動（`main`）から `/help` を打つまでの通し。テストは `repl.run` に偽物の入力を渡した
- `--directory` で起動したときに、その下の `.local-coding-agent/commands/` を読むこと（コードでは `Session.cwd` を使う。テストは無い）
- 入力待ちの Ctrl-C（改行を出して次の行を読む）を、実物の端末で

### テストを走らせる

- `.venv/bin/python -m unittest tests.test_commands_parse tests.test_commands_custom tests.test_commands_builtin tests.test_repl_commands`: F-07 で足した4つのファイルの59件。約 0.02 秒（実測）
- `.venv/bin/python -m unittest tests.test_loop.InputTokensTest tests.test_messages tests.test_main`: 入力のトークン数・`<metadata>` のコマンドの行・起動の行
- `.venv/bin/python -m unittest`: 全て（356件）

## 読む順

1. [__main__.py](../../../local_coding_agent/__main__.py#L74) の `main`
   - 入口: `python -m local_coding_agent`（[L128](../../../local_coding_agent/__main__.py#L128)）
   - 分かること: 変わったのは [L105](../../../local_coding_agent/__main__.py#L105) の起動の行の1行だけである。[L119](../../../local_coding_agent/__main__.py#L119) で `repl.run(session)` を呼ぶ
2. [repl.py](../../../local_coding_agent/cli/repl.py) の [`run`](../../../local_coding_agent/cli/repl.py#L32) と [`handle_line`](../../../local_coding_agent/cli/repl.py#L48)
   - 入口: `run` は `main` の [L119](../../../local_coding_agent/__main__.py#L119)。`handle_line` は `run` の [L45](../../../local_coding_agent/cli/repl.py#L45)
   - 分かること: F-07 の流れの中心。[L50](../../../local_coding_agent/cli/repl.py#L50) でコマンドかを見分け、コマンドでなければ [L52](../../../local_coding_agent/cli/repl.py#L52) で依頼として送る（F-06 までと同じ）。組み込みは [L53-L57](../../../local_coding_agent/cli/repl.py#L53-L57)、自作は [L58-L63](../../../local_coding_agent/cli/repl.py#L58-L63)（読めない）・[L64-L70](../../../local_coding_agent/cli/repl.py#L64-L70)（知らない名前）・[L71](../../../local_coding_agent/cli/repl.py#L71)（送る）。`run` は `/exit` で `finished` が立つと終わる（[L35](../../../local_coding_agent/cli/repl.py#L35)）。約70行
3. [conversation.py](../../../local_coding_agent/cli/conversation.py#L10) の `Conversation`
   - 入口: `run` の [L34](../../../local_coding_agent/cli/repl.py#L34) で作る。組み込みのコマンドが受けて、新しいものを返す
   - 分かること: REPL が会話の間に持つもの（`session`・`history`・`turn`・`input_tokens`・`finished`）。F-06 までは `run` の局所変数だった。[`next_turn`](../../../local_coding_agent/cli/conversation.py#L25)。約30行
4. [parse.py](../../../local_coding_agent/commands/parse.py#L28) の `parse_command`
   - 入口: `handle_line` の [L50](../../../local_coding_agent/cli/repl.py#L50)
   - 分かること: コマンドとみなす行。名前の形 [`NAME`](../../../local_coding_agent/commands/parse.py#L12) は `.` と `/` を含まないので、`/tmp/a.txt` は依頼になり、名前で置き場の外を指せない。約35行
5. [builtin.py](../../../local_coding_agent/commands/builtin.py) の [`find_builtin`](../../../local_coding_agent/commands/builtin.py#L32)・[`run_builtin`](../../../local_coding_agent/commands/builtin.py#L36)・[`BUILTINS`](../../../local_coding_agent/commands/builtin.py#L77) と、各コマンドの [`_help`](../../../local_coding_agent/commands/builtin.py#L45)・[`_clear`](../../../local_coding_agent/commands/builtin.py#L51)・[`_context`](../../../local_coding_agent/commands/builtin.py#L55)・[`_mode`](../../../local_coding_agent/commands/builtin.py#L59)・[`_exit`](../../../local_coding_agent/commands/builtin.py#L73)、[`help_text`](../../../local_coding_agent/commands/builtin.py#L95)・[`context_line`](../../../local_coding_agent/commands/builtin.py#L119)
   - 入口: `handle_line` の [L53](../../../local_coding_agent/cli/repl.py#L53)・[L55](../../../local_coding_agent/cli/repl.py#L55)
   - 分かること: どのコマンドも `Conversation` を受けて、新しい `Conversation` と画面の文を返す。`/clear` は履歴を空にするだけ（[L52](../../../local_coding_agent/commands/builtin.py#L52)）。`/mode` は許可のモードだけを替えた `Session` を作る（[L68-L69](../../../local_coding_agent/commands/builtin.py#L68-L69)。規則と、規則に添えた理由は残る）。`/context` の数え方（道具の結果を持つ利用者の発言を、依頼と分ける）。約135行
6. [custom.py](../../../local_coding_agent/commands/custom.py) の [`find_custom`](../../../local_coding_agent/commands/custom.py#L55)・[`parse_custom`](../../../local_coding_agent/commands/custom.py#L70)・[`split_front_matter`](../../../local_coding_agent/commands/custom.py#L77)・[`_description`](../../../local_coding_agent/commands/custom.py#L147)・[`expand`](../../../local_coding_agent/commands/custom.py#L95)・[`list_custom`](../../../local_coding_agent/commands/custom.py#L107)・[`_listed`](../../../local_coding_agent/commands/custom.py#L127)・[`_reason`](../../../local_coding_agent/commands/custom.py#L140)
   - 入口: `find_custom` は `handle_line` の [L59](../../../local_coding_agent/cli/repl.py#L59)。`expand` は `_send_custom` の [L81](../../../local_coding_agent/cli/repl.py#L81)。`list_custom` は `_help` の [L47](../../../local_coding_agent/commands/builtin.py#L47)
   - 分かること: 置き場（[`COMMANDS_PATH`](../../../local_coding_agent/commands/custom.py#L20)）のファイルを呼ぶたびに読む。前付けは `description` の行だけを読む（YAML の読み手を使わない）。`$ARGUMENTS` の置き換えと、無いときの末尾の `ARGUMENTS:`。一覧で、呼べない理由を決めるのはこちらで、`builtin.py` は並べるだけである。約165行
7. [`_send_custom`](../../../local_coding_agent/cli/repl.py#L74) → [`_send`](../../../local_coding_agent/cli/repl.py#L101) → [turn.py](../../../local_coding_agent/loop/turn.py#L40) の `run_turn` → [messages.py](../../../local_coding_agent/model/messages.py#L114) の `metadata_text`
   - 入口: `_send_custom` は `handle_line` の [L71](../../../local_coding_agent/cli/repl.py#L71)。`run_turn` は `_send` の [L106](../../../local_coding_agent/cli/repl.py#L106)。`metadata_text` は [ollama_messages.py](../../../local_coding_agent/model/ollama_messages.py#L137) の `_content`（送る直前の変換）
   - 分かること: 自作のコマンドの文がモデルに届くまで。`_send_custom` は本文が空なら送らず（[L82-L85](../../../local_coding_agent/cli/repl.py#L82-L85)）、`[コマンド]` の行と記録の1件を書いて `_send` に打った行を渡す。`run_turn` は打った行を [`user_text`](../../../local_coding_agent/model/messages.py#L75) の `command` に入れ（[L52](../../../local_coding_agent/loop/turn.py#L52)）、[`TurnResult`](../../../local_coding_agent/loop/turn.py#L31)（履歴と入力のトークン数。[`_input_tokens`](../../../local_coding_agent/loop/turn.py#L82)）を返す。`metadata_text` が送った時刻と並べて `コマンド: ` の行を `<metadata>` に入れる（[`Message.command`](../../../local_coding_agent/model/messages.py#L72)・[`COMMAND_LABEL`](../../../local_coding_agent/model/messages.py#L19)）。記録の1件は [`_show`](../../../local_coding_agent/cli/repl.py#L116)。`turn.py` と `messages.py` で変わったのは約60行
8. [system_prompt.py](../../../local_coding_agent/context/system_prompt.py#L48) の `<metadata>` の項
   - 入口: 既定の指示は `main` の [L77](../../../local_coding_agent/__main__.py#L77) の `read_instructions`
   - 分かること: モデルが `コマンド: ` の行について知るのは、この1文だけである。組み込みのコマンドは書いていない（モデルに何も渡らない）。1行
9. テスト: [test_repl_commands.py](../../../tests/test_repl_commands.py) の [`Repl`](../../../tests/test_repl_commands.py#L34)（偽物のモデルで REPL を回す道具立て）→ [`BuiltinInReplTest`](../../../tests/test_repl_commands.py#L57) → [`PromptTest`](../../../tests/test_repl_commands.py#L112) → [`UnknownAndRequestTest`](../../../tests/test_repl_commands.py#L121) → [`CustomInReplTest`](../../../tests/test_repl_commands.py#L150) → [test_commands_parse.py](../../../tests/test_commands_parse.py#L6) → [test_commands_builtin.py](../../../tests/test_commands_builtin.py#L53) → [test_commands_custom.py](../../../tests/test_commands_custom.py#L25) → [test_loop.py](../../../tests/test_loop.py#L131) の `InputTokensTest` → [test_messages.py](../../../tests/test_messages.py#L9) の `MetadataTextTest`
   - REPL の振る舞いを先に掴み、部品のテストへ下りる。約700行
10. [tasks/f-07-slash-commands/README.md](../../../tasks/f-07-slash-commands/README.md) → `project/.local-coding-agent/commands/` の [fix.md](../../../tasks/f-07-slash-commands/project/.local-coding-agent/commands/fix.md)・[explain.md](../../../tasks/f-07-slash-commands/project/.local-coding-agent/commands/explain.md)・[review.md](../../../tasks/f-07-slash-commands/project/.local-coding-agent/commands/review.md) と、試した後の走行の記録（`command` の件と、次の `request` の最後の発言）

## 既存の実装からの変わり

### 足したファイル・直したファイル

- 足した:
  - [commands/parse.py](../../../local_coding_agent/commands/parse.py)・[commands/custom.py](../../../local_coding_agent/commands/custom.py)・[commands/builtin.py](../../../local_coding_agent/commands/builtin.py)・`commands/__init__.py`
  - [cli/conversation.py](../../../local_coding_agent/cli/conversation.py)
  - `tests/test_commands_parse.py`・`test_commands_custom.py`・`test_commands_builtin.py`・`test_repl_commands.py`
  - `tasks/f-07-slash-commands/`（`project/` と README）
- 直した（移した関数は無い）:
  - [repl.py](../../../local_coding_agent/cli/repl.py): 書き直した。`run` の局所変数（履歴・回の番号）を `Conversation` にまとめ、1行の処理を `handle_line` に出し、コマンドの振り分け（`_send_custom`・`_send`・`_show`）を足した。入力待ちの Ctrl-C・EOF・空の行の扱いは変わらない
  - [turn.py](../../../local_coding_agent/loop/turn.py): `run_turn` が履歴の代わりに `TurnResult`（履歴と入力のトークン数）を返す。引数 `command` を足した。`_input_tokens` を足した
  - [messages.py](../../../local_coding_agent/model/messages.py): `Message.command`・`user_text` の `command`・`COMMAND_LABEL`。`metadata_text` が、送った時刻とコマンドの行を並べる
  - [ollama_messages.py](../../../local_coding_agent/model/ollama_messages.py): docstring の変換の表だけ（`sent_at・command`）
  - [system_prompt.py](../../../local_coding_agent/context/system_prompt.py): 既定の指示の `<metadata>` の項（下）
  - [__main__.py](../../../local_coding_agent/__main__.py): 起動の行に `コマンド: /help で一覧`
  - テスト: `test_loop.py`（`Run` が `result` を持つ・`InputTokensTest`）・`test_thinking.py`（`run_turn(...).history`）・`test_messages.py`・`test_context.py`・`test_main.py`（起動の行の最後）

### 振る舞いの変わり

- 利用者から見て:
  - 行の頭が `/<名前>`（英小文字・数字・`-`・`_`）の行は、ハーネスがコマンドとして処理する。F-06 までは、どの行も依頼として送った。`/tmp を見て` のような行は、知らない名前の誤りになり、送られない（頭に空白を置けば送る）。`/tmp/a.txt を読んで` は今までどおり依頼である
  - 組み込みの `/help`・`/clear`・`/context`・`/mode [<モード>]`・`/exit` を使える。どれもモデルを呼ばない。`/mode` で変えたモードは、その会話の間だけ効く
  - 作業ディレクトリの `.local-coding-agent/commands/<名前>.md` を `/<名前> [引数]` で呼べる。送る前に `[コマンド] /<名前> → <ファイル>（<行数> 行を依頼として送る）` が出る
  - 起動の行が1行増えた（4行目の `コマンド: /help で一覧`）
- モデルへ送る要求:
  - 既定の指示の「ハーネスが入れる情報」の `<metadata>` の項に、「「コマンド: 」の行があれば、利用者がそのコマンドを呼び、ハーネスが、コマンドのファイルの中身（引数を入れたもの）を、その発言の本文として送った」が加わった
  - 自作のコマンドで送った発言だけ、`<metadata>` に `コマンド: <打った行>` の行が入る。本文は引数を入れた中身で、ファイルのパス・前付け・`$ARGUMENTS` の印は渡らない
  - `/clear` の後の要求は、履歴を持たない。`/mode` で変えたことは、モデルに知らせない
- 走行の記録:
  - コマンドの行ごとに、`type` が `command` の件が入る（`line`・`name`・`kind`・`turn`・`source`・`text`・`output`）
  - ほかの件（`permissions`・`request`・`response`・`tool` など）の欄は変わらない

### 依存の向き

`cli/repl.py` → `commands/parse.py`・`commands/builtin.py`・`commands/custom.py`・`cli/conversation.py`・`loop/turn.py`。`commands/builtin.py` → `cli/conversation.py`・`commands/custom.py`・`model/messages.py`・`permissions/policy.py`（`MODES`・`is_mode`）。`commands/custom.py` → `commands/parse.py`（`NAME`）。`cli/conversation.py` → `loop/session.py`・`model/messages.py`。`loop/` は `commands/` を知らない。依存のパッケージは足していない。

### 文書・試す材料・設定

- README: 「できること」に F-07 の行、画面の例に起動の4行目、使い方に「slash commands」と「slash commands を試す材料」の項を足し、「Ctrl-D」（`/exit` と同じ）と「走行の記録」（コマンドの件と F-07 の文書へのリンク）の項を直した
- [コーディングエージェントの仕組み](../../how-coding-agents-work.md): 「コマンド（slash commands）」の節を足し、「ハーネスとモデルの分担」の表のハーネスの欄に「利用者のコマンドの処理」を足した
- [作る機能](../../features.md): F-07 の行を足した
- `tasks/f-07-slash-commands/`: 通らないテストを持つ小さなプロジェクトと、自作のコマンドのファイル3つ（`$ARGUMENTS` と前付けを持つ `fix.md`・`description` を `"…"` で囲む `explain.md`・前付けも `$ARGUMENTS` も無い `review.md`）。判定は F-05 の `judge.py` を使う
- 設定（`.claude/`・`pyproject.toml`）は変わらない

### 取り込みで branch から変えた所

- コードは変えていない。衝突したのは `README.md` と `docs/features.md` だけである
- `README.md`: 使い方の「許可」の項の最後の行と「実行の前の問い」の項は、main の F-06 の直し（照合の限界の一覧へのリンク・`[y/N/拒む理由]`・規則の理由）を残した。branch はそれより前の版を持っていた。「slash commands」の項は、その後に置いた
- `docs/features.md`: F-06 の行は、main の版（計測の結果へのリンクを持つ）を残し、F-07 の行を足した
- branch が分かれた後に main で入った F-06 の直し（規則の理由・問いの拒む理由・コメントの中の引用符）と `--directory` は、F-07 のコードと重ならない。`/mode` は `replace(permissions, mode=…)` なので、理由を添えた規則もそのまま残る。`--directory` で起動すると、自作のコマンドの置き場はその下になる
