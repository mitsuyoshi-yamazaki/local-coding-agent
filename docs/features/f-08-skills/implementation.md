# F-08 skills: 実装した仕様と仕組み

[実装前の仕様](spec.md) に対して、実際に実装した仕様と、その仕組みである。

## 使い方

スキル（skill）は、作業ごとの手順書である。作業ディレクトリの `.local-coding-agent/skills/<名前>/SKILL.md` に書く。

```markdown
---
description: 長さの単位の変換を足す手順（引数: 足す変換。例: inch → cm）
---

長さの単位の変換を足すときは、次の順に行う。

1. convert.py の RATES に行を足す
2. test_convert.py の CASES に2行を足す
3. CHANGELOG.md の「## 未リリース」の見出しの下に行を足す
4. `python -m unittest` を走らせる

足す変換: $ARGUMENTS
```

起動すると、スキルを探して起動の行に出す。モデルが依頼に合うと判断すると、道具 `load_skill` で読み込む。

```text
許可: allow-all・規則 0（設定ファイル無し）
スキル: 3（add-conversion・release・review）
コマンド: /help で一覧
> インチとセンチメートルの変換を足して
[入力 2410 トークン・…]
[道具] load_skill {"name": "add-conversion", "arguments": "inch → cm"}
→ 8 行
…（ここから、読み込んだ手順に沿って道具を呼ぶ）
> /review convert.py
[スキル] /review → .local-coding-agent/skills/review/SKILL.md（12 行を依頼として送る）
…
```

## 仕組み

### 3段の読み込み

| 段 | モデルに渡るもの | いつ | 作る所 |
|---|---|---|---|
| 一覧 | 全てのスキルの名前と説明 | 毎回の要求（system prompt の「# スキル」の節） | `skills/catalog.py` の `skills_section` |
| 本文 | 選んだスキルの本文と、付いているファイルの一覧 | モデルが `load_skill` を呼んだとき（道具の結果）・利用者が `/<名前>` で呼んだとき（利用者の発言） | `skills/content.py` の `skill_text` |
| 付いているファイル | スキルのディレクトリの中のファイルの中身 | モデルが一覧を見て、要ると判断して `read_file` で読んだとき | 既存の `read_file`（F-03） |

ハーネスが毎回送るのは一覧だけである。本文は、読み込んだ回に1度だけ会話に入り、後の回では履歴の一部として送られる。付いているファイルは、ハーネスは読まない。

### 起動

`__main__.py` の `main` が、次の順に行う。

1. `discover_skills(cwd)` で置き場を探し、使えるスキル（`Skill`）と使えないスキル（`Unusable`）に分ける（`SkillCatalog`）
2. `load_skill_tool(catalog)` で道具を作る。使えるスキルが1つ以上あるときだけ、`Session.tools` に足す
3. 許可の設定ファイルは、`load_skill` を足した道具の組で読む。使えるスキルが無くても、`load_skill` の規則は誤りにならない
4. `skills_section(catalog)` を、環境の節の後に system prompt へつなぐ（`build_system_prompt` の3つ目の部分）。使えるスキルが無ければ空で、節は入らない。`--system-prompt-file` で指示を差し替えても残る
5. 走行の記録に `skills` の件を書き（許可の件の次の2件目）、起動の行を出す（`describe_skills`）
6. `Session.skills` に一覧を持たせる。REPL が `/<名前>` と `/help` で使う

一覧は起動のときに1度だけ探す。会話の途中で足したスキルは、起動し直すまで一覧に入らず、`/<名前>` でも知らない名前になる。

### スキルのファイル

- 置き場の下の一段のディレクトリだけを見る（名前の順）。ディレクトリでないもの（置き場の `README.md` など）は見ない
- シンボリックリンクのディレクトリは辿る。リンクの先が作業ディレクトリの外でも、その `SKILL.md` を読み、中身をモデルに渡す。置き場は利用者が書くものとして、確かめない（F-07 の自作のコマンドのファイルと同じ）
- スキルの名前はディレクトリの名前で、F-07 の名前の形（`commands/parse.py` の `NAME`。英小文字か数字で始まり、英小文字・数字・`-`・`_` が続く）に合うものだけを使う。`.` と `/` を含めないので、名前で置き場の外を指せない
- `SKILL.md` は、F-07 の自作のコマンドのファイルと同じ読み手（`commands/custom.py` の `parse_custom`）で読む。前付けの中で使うのは `description` だけで、無ければ本文の最初の空でない行を説明にする。`name` などのほかの欄は使わず、誤りにもしない

使えないスキルは一覧に入れず、`/help` に理由を出す。

| 理由 | `/help` の行 |
|---|---|
| ディレクトリの名前が、名前の形に合わない | `Foo/  （名前に使えない字があるので使えない）` |
| `SKILL.md` が無い | `notes/  （SKILL.md が無いので使えない）` |
| `SKILL.md` を読めない | `broken/  （SKILL.md を読めない: <理由>）` |
| 本文が空 | `empty/  （本文が空なので使えない）` |
| 置き場の中を見られない | `.local-coding-agent/skills/  （読めない: <理由>）` |

読めない理由は、OS の誤りの文（`Permission denied` など）か、UTF-8 として読めないことの文で、手元の絶対パスを含めない（F-07 と同じ `error_reason`）。

### 「# スキル」の節

```text
# スキル

スキルは、作業ごとの手順書である。下に、作業ディレクトリに置かれたスキルの名前と説明を並べる。依頼がスキルの説明に合えば、作業を始める前に load_skill の道具でそのスキルを読み込み、本文の手順に従う。合うスキルが無ければ、読み込まない。

- add-conversion: 長さの単位の変換を足す手順（引数: 足す変換。例: inch → cm）
- release: 版を上げて、リリースの準備をする（引数: 新しい版。例: 1.1.0）
- review: コードを読み、誤りや分かりにくい所を挙げる。ファイルは書き換えない（引数: 対象のファイル）
```

説明の長さに上限は置かず、一覧の全体の大きさも限らない。`tasks/f-08-skills/` の3つでは、節は 290 字、3つの本文（付いているファイルの一覧を含む）は合わせて 771 字だった（実測。`skills_section` と `skill_text` の文字数）。

### 道具 load_skill

`tools/load_skill.py` の `load_skill_tool(catalog)` が、一覧から道具を作る。

| 欄 | 型 | 中身 |
|---|---|---|
| `name` | 文字列（必須） | スキルの名前。定義の `enum` に、使えるスキルの名前を並べる |
| `arguments` | 文字列（省ける） | 本文の `$ARGUMENTS` に入れる引数。前後の空白を除く。省けば空の文字列 |

- 入力の照らし（`tools/input_check.py`）に `enum` を足した。一覧に無い名前は、実行の前に `入力が定義に合わない: name は次のどれか: add-conversion, release, review（受けた値: "x"）` の誤りになる
- 結果は、下の「スキルの中身」である。読めないときは `スキル <名前> を使えない: <理由>`（`SKILL.md を読めない: <理由>`・`本文が空`・`引数を入れた中身が空`）の誤りの結果を返す
- 種類は「読む」で、下見も、許可の規則と照らす文字列（`target`）も持たない。許可のモードでは、どのモードでも問わずに通り、`[許可]` の行も出ない（F-06 の読む道具と同じ）。名前だけの規則（`deny` の `load_skill` など）は合う。型を持つ規則（`load_skill(review)`）は、照らす文字列が無いので、どの呼び出しにも合わない
- 画面には、ほかの道具と同じく `[道具] load_skill {…}` と `→ <行数> 行` を出す

### スキルの中身

`skills/content.py` の `skill_text` が作る。モデルが `load_skill` で読み込むときも、利用者が `/<名前>` で呼ぶときも、同じ文である。

```text
対象のファイルを読み、checklist.md の観点ごとに、当てはまる所を挙げよ。ファイルは書き換えない。
…
対象: convert.py

スキルのディレクトリ: .local-coding-agent/skills/review/（本文の中の相対パスは、ここからのもの）
付いているファイル（要るときに read_file で読む）:
- .local-coding-agent/skills/review/checklist.md
```

1. `SKILL.md` を読む（読み込むたびに読む。書き換えは次に読み込んだときから効く）
2. 本文が空なら誤り
3. 本文に引数を入れる。F-07 の自作のコマンドと同じ `expand` を使う（`$ARGUMENTS` を全て置き換える。無くて引数があれば、末尾に `ARGUMENTS: <引数>` を足す。前後の空白を除く）。空になれば誤り
4. 付いているファイルを探す（`attached_files`）。スキルのディレクトリの中の、`SKILL.md` のほかのファイル（下のディレクトリも含む）を、作業ディレクトリからのパスで名前の順に並べる。`.` で始まるファイルとディレクトリ（macOS の `.DS_Store` など）は除く。中身は読まない。ディレクトリの中を見られなければ、無いものとする。下のディレクトリのシンボリックリンクは辿らない（Python の `Path.rglob` の既定）
5. 付いているファイルがあれば、本文の後に空の行を挟んで、スキルのディレクトリと一覧を足す。50 を超えたら、50 までを並べ、`（ほかに <数> 個。list_directory で見る）` を足す。無ければ、本文だけである

パスを作業ディレクトリからにしたのは、モデルがそのまま `read_file` に渡せるようにするためである。

### 利用者が /<名前> で呼ぶ

`cli/repl.py` の `handle_line` は、名前を組み込みのコマンド → 自作のコマンド → スキルの順に探す。

- スキルなら、`_send_skill` が `skill_text` で中身を作り、`[スキル] /<名前> → <SKILL.md のパス>（<行数> 行を依頼として送る）` を出して、依頼として回を始める
- 送る利用者の発言は、本文がスキルの中身で、メタデータに打った行を持つ（`model/messages.py` の `Message.skill`）。送る直前に、送った時刻と並べて `<metadata>` に `スキル: /review convert.py` の行が入る（`metadata_text`・見出しは `SKILL_LABEL`）
- 読めないときは `誤り: /<名前> のスキルを使えない: <理由>` を出し、送らない。履歴は変わらず、回の番号も進まない
- 組み込みか自作のコマンドと同じ名前のスキルは、`/<名前>` では呼べない（先に探すほうが勝つ）。モデルは `load_skill` で読み込める

### /help

`commands/builtin.py` の `help_text` が、自作のコマンドの後にスキルを並べる。一覧の行は `skills/catalog.py` の `list_skills` が作る。

```text
自作のコマンド（.local-coding-agent/commands/）:
  （無し）
スキル（.local-coding-agent/skills/。/<名前> で呼ぶか、モデルが読み込む）:
  /add-conversion  長さの単位の変換を足す手順（引数: 足す変換。例: inch → cm）
  /release         版を上げて、リリースの準備をする（引数: 新しい版。例: 1.1.0）
  /review          コードを読み、誤りや分かりにくい所を挙げる。ファイルは書き換えない（引数: 対象のファイル）
```

- 名前の列は、組み込み・自作・スキルの全体で揃える
- 使えるスキル、使えないスキルの順に並べる。スキルが無ければ `  （無し）`
- 組み込みと同じ名前のスキルには `（組み込みと同じ名前なので /<名前> では呼べない。モデルは読み込める）`、自作のコマンドと同じ名前には `（自作のコマンドと同じ名前なので /<名前> では呼べない。モデルは読み込める）` を付ける。自作のコマンドと同じ名前かは、`/help` を打ったときにファイルがあるかで見る
- スキルの一覧は、起動のときに探したもの（`Session.skills`）である

### 起動の行

許可の行の後、`コマンド: /help で一覧` の前に1行を出す。

| 一覧 | 起動の行 |
|---|---|
| 使えるスキルが3つ | `スキル: 3（add-conversion・release・review）` |
| 使えないスキルもある | `スキル: 3（add-conversion・release・review）・使えない 1（/help で理由）` |
| 無い | `スキル: 無し` |

### 既定の指示

`context/system_prompt.py` の既定の指示の「ハーネスが入れる情報」に、次の2つを足した。

- 「# 環境」の後の「# スキル」の節（あれば）: 作業ディレクトリに置かれたスキルの名前と説明。読み込み方は、その節にある
- `<metadata>` の「スキル: 」の行: 利用者がそのスキルを呼び、ハーネスが、スキルの中身（引数を入れたもの）を、その発言の本文として送った。そのスキルを `load_skill` で読み込み直さない

読み込み方（依頼が説明に合えば、作業の前に `load_skill` で読み込む）は、既定の指示ではなく「# スキル」の節に書いた。スキルが無いときに指示に入らず、`--system-prompt-file` で指示を差し替えても残るためである。

### 走行の記録

起動のときに、許可の件の次に1件を書く。

| 欄 | 中身 |
|---|---|
| `type` | `skills` |
| `skills` | 使えるスキルの並び。1つが `name`・`source`（`SKILL.md` の、作業ディレクトリからのパス）・`description` |
| `unusable` | 使えないスキルの並び。1つが `entry`（ディレクトリの名前に `/` を付けたもの、か置き場）・`problem`（理由） |

- `load_skill` の呼び出しは、ほかの道具と同じ `tool` の件に入る。`input` に名前と引数が、`result` に返した中身の全文が入る
- `/<名前>` でスキルを呼んだ行は、F-07 の `command` の件に入る。`kind` が `skill` で、`source` は `SKILL.md` のパス、`text` は送った本文（送らなければ `null`）、`turn` は始めた回の番号（送らなければ `null`）
- モデルに送った一覧は、`request` の件の system prompt の中にある

## 試すための材料

`tasks/f-08-skills/` に置く。写し方と課題と判定のコマンドは `tasks/f-08-skills/README.md` にある。

| 材料 | 中身 |
|---|---|
| `project/convert.py`・`test_convert.py` | 長さの単位の変換（km → m・mile → km）と、そのテスト。写したばかりの状態では全て通る |
| `project/CHANGELOG.md`・`VERSION` | 変更の記録と版 |
| `skills/add-conversion/SKILL.md` | 変換を足す手順。表・テスト・変更の記録に足し、テストを走らせる |
| `skills/review/SKILL.md`・`checklist.md` | 観点に沿ってコードを読む手順。観点は `checklist.md` にだけある |
| `skills/release/SKILL.md` | 版を上げる手順。課題の依頼には合わない |
| `judge.py` | 「インチとセンチメートルの変換を足して」の判定。テスト・変換・テストの場合・変更の記録の4つを見る |

スキルをプロジェクトの外（`skills/`）に置いたのは、スキルを写さない写しと比べて、一覧の大きさを入力トークン数で見るためである（写さなければ、消さずに済む）。

`judge.py` は、写したばかりの写しではテストだけが通って終了コード 1、手で変換・テストの場合・変更の記録を足した写しでは終了コード 0 だった（実測。モデルは使っていない）。

## 実装前の仕様との違い

振る舞いの大筋は仕様のとおりである。仕様に書いていなかった細部と、変えたことは次のとおり。

| 点 | 実装 |
|---|---|
| 一覧の見せ方の置き場 | 仕様の `skills/catalog.py` に、探す・読む・節・起動の行・走行の記録・`/help` の一覧の全てを置いた（170 行）。中身を作るのは `skills/content.py` |
| `load_skill` の `arguments` | 前後の空白を除いてから入れる（F-07 の引数と同じ） |
| 付いているファイルを見られないとき | 一覧を付けず、本文だけを返す |
| `.` で始まるファイル | 付いているファイルの一覧から除く（見直しの指摘。macOS で写すと `.DS_Store` が入り、50 の枠を埋めうる） |
| 自作のコマンドと同じ名前か | `/help` を打ったときに、`.local-coding-agent/commands/<名前>.md` があるかで見る（`/<名前>` で呼ぶときの探し方と同じ） |
| F-07 のコード | `commands/custom.py` の読めない理由の関数を、スキルでも使うために公開の名前（`error_reason`）にした。`/help` の自作のコマンドの一覧の後に、スキルの節が付く |
| `Session` | `skills`（起動のときの一覧）を足した。既定は空 |

## ファイル

| ファイル | 行数の目安 | 中身 |
|---|---|---|
| `local_coding_agent/skills/catalog.py` | 170 | 置き場を探す・`SKILL.md` を読む・名前で探す・「# スキル」の節・起動の行・走行の記録の1件・`/help` の一覧 |
| `local_coding_agent/skills/content.py` | 60 | スキルの中身（本文に引数を入れ、付いているファイルを添える） |
| `local_coding_agent/tools/load_skill.py` | 65 | 道具 `load_skill`（一覧から作る） |
| `local_coding_agent/tools/input_check.py` | 80 | `enum` を照らす |
| `local_coding_agent/loop/session.py` | 40 | スキルの一覧を持つ |
| `local_coding_agent/cli/repl.py` | 180 | `/<名前>` でスキルを呼ぶ（`_send_skill`） |
| `local_coding_agent/commands/builtin.py` | 150 | `/help` にスキルを並べる |
| `local_coding_agent/model/messages.py` | 140 | 利用者の発言のメタデータに、スキルの行（`skill`・`SKILL_LABEL`） |
| `local_coding_agent/loop/turn.py` | 105 | 依頼にスキルの行を付けて受ける |
| `local_coding_agent/context/system_prompt.py` | 75 | 「# スキル」の節をつなぐ・既定の指示 |
| `local_coding_agent/__main__.py` | 155 | 起動のときにスキルを探し、道具・節・起動の行・走行の記録に渡す（`_start_trace`） |
| `tasks/f-08-skills/` | | 試すための材料と判定のコマンド |
| `tests/test_skills_*.py`・`tests/test_load_skill.py`・`tests/test_repl_skills.py` | | 探す・節・中身・道具・REPL の中の振る舞い |

## Claude Code との違い

- Claude Code は、プロジェクト・個人・組織・プラグインなどの置き場を読み、一覧の大きさに予算（文脈窓の 1%）を置いて、使われることの少ないスキルから説明を落とす。ここは作業ディレクトリの置き場だけを読み、予算を置かない
- Claude Code は、前付けの多くの欄（`disable-model-invocation`・`user-invocable`・`allowed-tools`・`context: fork` など）を持つ。ここは `description` だけを読む。利用者だけが呼ぶ手順は、F-07 の自作のコマンドに書く
- Claude Code では、Claude が呼んだスキルの本文も1つの発言として会話に入る。ここでは道具の結果として入る（利用者が呼べば、利用者の発言として入る）
- Claude Code は、スキルに付いているファイルを本文から指し、`${CLAUDE_SKILL_DIR}` でスキルのディレクトリを指せる。ここは中身にディレクトリと一覧を添える

## 出典

確かめた日は 2026-10-28。

- Claude Code のスキル（置き場・前付けの欄・説明だけを文脈に入れる・Skill の道具・本文は1つの発言として会話に入る・`$ARGUMENTS`・`disable-model-invocation` と `user-invocable`・付いているファイル・一覧の予算）: https://code.claude.com/docs/en/skills
- Agent Skills の規格（3段の読み込み・名前と説明の決まり）: https://agentskills.io/specification
- Agent Skills をエージェントに組み込む案内（一覧の置き場・読み込む道具の `name` を `enum` で限る・付いているファイルを読まずに並べる）: https://agentskills.io/integrate-skills
