# F-07 slash commands: 実装した仕様と仕組み

[実装前の仕様](spec.md) に対して、実際に実装した仕様と、その仕組みである。

## 使い方

`/` で始まる行は、ハーネスがコマンドとして処理する。組み込みのコマンドは、モデルを呼ばない。

```text
コマンド: /help で一覧
> /help
組み込みのコマンド:
  /help     コマンドの一覧を出す
  /clear    会話の履歴を消し、新しい会話にする
  /context  今の履歴の発言の数と、最後の要求の入力トークン数を出す
  /mode     許可のモードを見る。/mode <モード> で変える（ask・accept-edits・allow-all）
  /exit     終える
自作のコマンド（.local-coding-agent/commands/）:
  /explain  ファイルの役目を短く説明する（引数: ファイルのパス）
  /fix      テストを走らせ、失敗していれば直す（引数: 対象のテスト）
  /review   コードを読み、誤りがありそうな所を挙げよ。ファイルは書き換えない。
> /mode accept-edits
許可のモード: allow-all → accept-edits
> /fix test_temperature.py
[コマンド] /fix → .local-coding-agent/commands/fix.md（3 行を依頼として送る）
…（ここから、打った依頼と同じく回が進む）
> /context
[文脈] 発言 9（依頼 1・モデル 4・道具の結果 4）・最後の要求の入力 3210 トークン
> /clear
（会話を消した。次の依頼から新しい会話になる）
```

自作のコマンドは、作業ディレクトリの `.local-coding-agent/commands/<名前>.md` に書く。

```markdown
---
description: テストを走らせ、失敗していれば直す（引数: 対象のテスト）
---

テストを走らせよ。失敗していれば、出力を読んでコードを直し、もう一度走らせよ。テストのファイルは書き換えない。

対象のテスト: $ARGUMENTS
```

## 仕組み

### 行の流れ

`cli/repl.py` の `handle_line` が、1行ずつ次の順で振り分ける。

1. `commands/parse.py` の `parse_command` で、コマンドかを見分ける。コマンドでなければ、依頼として回を始める（F-06 までと同じ）
2. 組み込みのコマンド（`commands/builtin.py` の `BUILTINS`）を名前で探す。あれば、その処理を行う。モデルは呼ばない
3. 自作のコマンドのファイルを探す（`commands/custom.py` の `find_custom`）。あれば、引数を入れて、依頼として回を始める
4. どちらにも無ければ、`誤り: 知らないコマンド: /<名前>（/help で一覧。依頼として送るなら、行の頭に空白を置く）` を出す

組み込みを先に探すので、組み込みと同じ名前の自作のコマンド（`clear.md` など）は呼べない。誤りのときと、組み込みのコマンドでは、回の番号は進まない。

### コマンドとみなす行

行の頭（前に空白が無い）が `/` で、`/` から空白（タブを含む）までの語が、名前の形に合うものである。名前の形は、英小文字か数字で始まり、英小文字・数字・`-`・`_` が続くもの。語の後ろの文から前後の空白を除いたものが、引数である。

| 行 | 扱い |
|---|---|
| `/fix  test_a.py -v` | コマンド。名前 `fix`・引数 `test_a.py -v` |
| `/tmp/a.txt を読んで` | 依頼（語に `/` を含む） |
| `/tmp を見て` | コマンドの形だが、知らない名前なので誤り |
| ` /tmp を見て`（頭に空白） | 依頼 |
| `/`・`/ help`・`/Help`・`/a.md` | 依頼（名前の形に合わない） |

名前は `.` と `/` を含めないので、自作のコマンドの名前は、置き場のディレクトリの外のファイルを指せない（`/../x` はコマンドにならない）。

### 組み込みのコマンド

どのコマンドも、REPL が持つもの（下の「REPL が持つもの」）と引数を受け、新しいものと、画面に出す文を返す。受けたものは書き換えない。

| コマンド | すること |
|---|---|
| `/help` | 組み込みの名前と説明と、自作のコマンドの一覧を出す。名前の列を揃える |
| `/clear` | 履歴を空にし、最後の要求の入力トークン数を忘れる。回の番号は続けて数える |
| `/context` | 履歴の発言の数を、依頼（利用者の発言のうち、道具の結果を持たないもの）・モデル・道具の結果（利用者の発言のうち、道具の結果を持つもの）に分けて出す。最後の要求の入力トークン数を出す（無ければ `まだ無い`） |
| `/mode` | 引数が無ければ今のモードを出す。あれば、許可のモードを替えた session を作る。規則は変えない。設定ファイルには書かない |
| `/exit` | 終える印を立てる。REPL は次の行を読まずに終わる |

- 引数を取るのは `/mode` だけである。ほかのコマンドに引数を付けると、何もせず `/<名前> は引数を取らない` を出す
- `/mode` の知らないモードは、何もせず `誤り: 知らないモード: <値>（ask・accept-edits・allow-all のどれか）` を出す
- `/clear` の後、モデルは前の会話を知らない。履歴を持つのはハーネスで、次の要求に前の発言を入れないだけだからである
- `/mode` で変えたモードは、次の道具の呼び出しの判定から効く。モデルには、変えたことを知らせない（F-06 と同じく、モデルはモードを知らない）

### 自作のコマンド

`commands/custom.py` が扱う。ファイルは、呼ぶたびに読む（書き換えは次に呼んだときから効く）。

- **前付け**: 1行目が `---`（後ろの空白は可）で、閉じる `---` の行があれば、その間を前付けとして読む。前付けの中で使うのは `description: <文>` の行だけで、値を `"…"` か `'…'` で囲んでいれば外す。ほかの行（`allowed-tools:` など）は使わず、誤りにもしない。閉じる `---` が無ければ、全体が本文である
- **説明**: 前付けの `description`。無ければ、本文の最初の空でない行（前後の空白を除く）
- **引数の入れ方**（`expand`）: 本文の `$ARGUMENTS` を、全て引数に置き換える（引数が無ければ空の文字列）。本文に `$ARGUMENTS` が無く、引数があれば、本文の末尾に空の行を挟んで `ARGUMENTS: <引数>` を足す。最後に前後の空白を除く
- **送らないとき**: 本文が空（空白だけ）のときと、置き換えた文が空のとき（本文が `$ARGUMENTS` だけで、引数が無い）は、`誤り: /<名前> の中身が空なので送らない` を出す
- **読めないとき**: UTF-8 でない・権限が無いなどで読めなければ、`誤り: /<名前> を読めない: <理由>` を出す。理由は OS の誤りの文（`Permission denied` など）で、手元の絶対パスを含めない
- **一覧**（`list_custom`）: 置き場の `.md` のファイル（ディレクトリは除く）を名前の順に並べる。呼べないものには理由を付ける

| 呼べない理由 | 一覧の行 |
|---|---|
| 名前の形に合わない（`Fix.md` など） | `Fix.md    （名前に使えない字があるので呼べない）` |
| 読めない | `/broken   （読めない: <理由>）` |
| 組み込みと同じ名前 | `/clear    <説明>（組み込みと同じ名前なので呼べない）` |
| 置き場の中を見られない | `.local-coding-agent/commands/  （読めない: <理由>）` |

置き場のファイルがシンボリックリンクなら、辿って読む（リンクの先が作業ディレクトリの外でも読む）。置き場は利用者が書くものとして、確かめない。

### モデルに送る発言

自作のコマンドで送る利用者の発言は、本文が置き換えた文で、メタデータに打った行（`/fix test_temperature.py`）を持つ（`model/messages.py` の `Message.command`）。送る直前に、送った時刻と並べて `<metadata>` に入れる（`metadata_text`）。

```text
<metadata>
送った時刻: 2026-10-28 15:30 (+09:00)
コマンド: /fix test_temperature.py
</metadata>
テストを走らせよ。失敗していれば、出力を読んでコードを直し、もう一度走らせよ。テストのファイルは書き換えない。

対象のテスト: test_temperature.py
```

モデルが受け取るのは、この文だけである。ファイルのパス・前付け・`$ARGUMENTS` の印は渡らない。その後の回の流れ（応答・道具・許可・Ctrl-C）は、打った依頼と同じである。

### REPL が持つもの

`cli/conversation.py` の `Conversation` に、会話の間に REPL が持つものをまとめた。回ごと・コマンドごとに、新しい `Conversation` を作る。

| 欄 | 中身 | 変えるもの |
|---|---|---|
| `session` | ループに渡すもの（F-03 から）。許可の設定を含む | `/mode` |
| `history` | 会話の履歴 | 回・`/clear` |
| `turn` | 始めた回の数。走行の記録の `turn` | 回（打った依頼・自作のコマンド） |
| `input_tokens` | 最後の要求の入力トークン数 | 回・`/clear` |
| `finished` | 終えるか | `/exit` |

### ループが返すもの

`loop/turn.py` の `run_turn` は、新しい履歴に加えて、入力トークン数を返す（`TurnResult`）。入力トークン数は、その回で最後に終わりまで届いた応答の `prompt_eval_count`（Ollama が数えた、要求の入力のトークン数）である。後の応答がこの数を持たなければ、前の応答の数を残す。回の中で応答が1つも終わりまで届かなければ（1回目の応答の途中で止めた・誤り）、無しを返し、REPL は前の回の値を保つ。

`prompt_eval_count` は、Ollama が前の要求の計算を使い回した分も含めた全体の数である（[Ollama の文書](../../technologies/ollama.md#前の要求の計算の使い回しkv-キャッシュ)）。次の要求は、これに最後の応答と次の依頼を足したものになる。

### system prompt

`context/system_prompt.py` の既定の指示の「ハーネスが入れる情報」の `<metadata>` の項に、「「コマンド: 」の行があれば、利用者がそのコマンドを呼び、ハーネスが、コマンドのファイルの中身（引数を入れたもの）を、その発言の本文として送った」を足した。組み込みのコマンドは書いていない。モデルには何も渡らないためである。

### 起動

起動の行の最後に `コマンド: /help で一覧` を出す。

### 走行の記録

コマンドの行ごとに1件を書く。

| 欄 | 中身 |
|---|---|
| `type` | `command` |
| `line` | 打った行（末尾の空白を除く） |
| `name` | 名前 |
| `kind` | `builtin`（組み込み）・`custom`（自作。読めない・空で送らなかったものを含む）・`unknown`（知らない名前） |
| `turn` | 自作のコマンドで依頼を送ったときは、その回の番号。ほかは `null` |
| `source` | 自作のコマンドのファイル（作業ディレクトリからのパス）。読めなかったときと、ほかの種類では `null` |
| `text` | 自作のコマンドで送った本文（置き換えた後）。送らなければ `null` |
| `output` | 画面に出した文（`/help` の一覧・`/mode` の変わり・誤りの文など）。`/exit` は空 |

自作のコマンドで送った発言は、次の `request` の件の `body.messages` の最後に、`<metadata>` を入れた形のまま入る。

## 試すための材料

`tasks/f-07-slash-commands/` に置く。写し方と課題と判定のコマンドは `tasks/f-07-slash-commands/README.md` にある。

| 材料 | 中身 |
|---|---|
| `project/temperature.py`・`test_temperature.py` | 摂氏と華氏の変換と、そのテスト。写したばかりの状態では、4つのうち3つが失敗する |
| `project/.local-coding-agent/commands/fix.md` | 前付けの `description` と `$ARGUMENTS` を持つ |
| `project/.local-coding-agent/commands/explain.md` | `description` を `"…"` で囲む。`$ARGUMENTS` をファイルのパスに使う |
| `project/.local-coding-agent/commands/review.md` | 前付けも `$ARGUMENTS` も無い |

| 課題 | 打つもの | 見ること |
|---|---|---|
| 一覧 | `/help` | 組み込みの5つと自作の3つが出る。モデルを呼ばない |
| 自作のコマンドで直させる | `/fix test_temperature.py` | 送った発言が、置き換えた本文と `<metadata>` のコマンドの行を持つ。テストが通ったか（判定のコマンドの終了コード） |
| 引数を末尾に足す | `/review temperature.py` | 送った本文の末尾の `ARGUMENTS: temperature.py` を、モデルが読むか |
| 会話を消す | 何かを話す → `/context` → `/clear` → `/context` → 前の話を尋ねる | 発言の数が 0 になる。モデルが前の話を知らない |
| モードを変える | `/mode ask` → `/fix` | 書く前とコマンドの前に問う |

`tasks/f-07-slash-commands/project/` の設定で、`/help` の一覧と、3つのコマンドの置き換えた文を、`help_text`・`list_custom`・`expand` に掛けて確かめた（実測。モデルは使っていない）。

## 実装前の仕様との違い

振る舞いの大筋は仕様のとおりである。仕様に書いていなかった細部と、変えたことは次のとおり。

| 点 | 実装 |
|---|---|
| 本文が空で引数があるとき | 送らない。仕様の「置き換えた文が空なら送らない」のままでは、`ARGUMENTS: <引数>` だけの依頼を送ることになるためである |
| 置き場の中を見られないとき | `/help` の一覧に、置き場を読めないことの1行を出す（REPL は止まらない） |
| 読めないときの理由 | OS の誤りの文だけにし、手元の絶対パスを含めない |
| 入力トークン数 | 回の中で、後の応答が `prompt_eval_count` を持たなければ、前の応答の数を残す |
| 走行の記録の `source` | 読めなかった自作のコマンドでは `null` |
| `/exit` の `output` | 空の文字列 |
| REPL が持つもの | `cli/conversation.py` の `Conversation` にまとめ、次に始める回の番号（`next_turn`）を持たせた |

## ファイル

| ファイル | 行数の目安 | 中身 |
|---|---|---|
| `local_coding_agent/commands/parse.py` | 35 | 行がコマンドか・名前と引数（`parse_command`・`NAME`） |
| `local_coding_agent/commands/custom.py` | 165 | 自作のコマンドの読み取り・前付け・引数の入れ方・一覧 |
| `local_coding_agent/commands/builtin.py` | 135 | 組み込みのコマンドと `/help` の一覧・`/context` の1行 |
| `local_coding_agent/cli/conversation.py` | 30 | REPL が会話の間に持つもの |
| `local_coding_agent/cli/repl.py` | 140 | 行を、組み込み・自作・依頼に振り分ける。走行の記録の1件 |
| `local_coding_agent/loop/turn.py` | 105 | 入力トークン数を返す（`TurnResult`）。依頼にコマンドの行を付けて受ける |
| `local_coding_agent/model/messages.py` | 130 | 利用者の発言のメタデータに、コマンドの行（`command`）を足した |
| `local_coding_agent/context/system_prompt.py` | 70 | 既定の指示 |
| `local_coding_agent/__main__.py` | 115 | 起動の行に `/help` の案内を足した |
| `tasks/f-07-slash-commands/` | | 試すための材料 |
| `tests/test_commands_*.py`・`tests/test_repl_commands.py` | | 行の見分け・自作のコマンド・組み込み・REPL の中の振る舞い |

## 出典

確かめた日は 2026-10-28。

- Claude Code の skills と自作のコマンド（`.claude/commands/` が skills にまとめられた・`$ARGUMENTS`・`$ARGUMENTS` が無いときに末尾へ `ARGUMENTS: <引数>` を足す・`description` が無いときは本文の最初の空でない行）: https://code.claude.com/docs/en/slash-commands
- Claude Code の組み込みのコマンド（コマンドは行の頭でだけ認める・名前の後ろの文が引数・`/clear`・`/help`・`/exit`）: https://code.claude.com/docs/en/commands
- Claude Code の `/context`（文脈窓の使い方を区分ごとに出す）: https://code.claude.com/docs/en/context-window
- Claude Code のモードの切り替え（端末の Shift+Tab・`/permissions` は規則を扱う）: https://code.claude.com/docs/en/permission-modes
