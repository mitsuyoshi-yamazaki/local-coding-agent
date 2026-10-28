# F-08 skills: 確かめる案内

F-08 を試し、コードを読むための案内である。動作の確かめ方・読む順・既存の実装（F-07 まで）からの変わりを書く。

main に取り込んだ後のコードと差分（基点 `a0e73a0` から、取り込んだ commit `67ebd42` まで）と、[実装前の仕様](spec.md)・[実装した仕様と仕組み](implementation.md)・[引き継ぎ](handoff.md) から書いた。行の番号は、この案内を最後に直した commit のコードのものである（`git log -1 -- docs/features/f-08-skills/guide.md` で分かる）。

## 動作の確かめ方

### 準備

- モデルは `qwen3.5:9b`（F-07 と同じ）。`pyproject.toml`・`poetry.lock` は変わっていないので、`poetry install` は要らない
- 文脈の長さを `ollama ps` で確かめる（[README](../../../README.md) の「Ollama を設定する」）。スキルを置いた写しでは、system prompt に「# スキル」の節（材料の3つで 290 字）が足され、読み込んだスキルの本文が履歴に入る。既定の指示も2項増えた
- 既定の許可のモードは `allow-all`（全部通す）である。材料は設定ファイルを持たない。`load_skill` は読む道具なので、`--permission-mode ask` でも問わずに通り、`[許可]` の行も出ない

### 起動

リポジトリの根で、プロジェクトを写し、写しのスキルの置き場（`.local-coding-agent/skills/`）にスキルを写して、`--directory` で起動する。

```sh
cp -R tasks/f-08-skills/project .tmp/f-08-project
mkdir .tmp/f-08-project/.local-coding-agent
cp -R tasks/f-08-skills/skills .tmp/f-08-project/.local-coding-agent/skills
.venv/bin/python -m local_coding_agent --model qwen3.5:9b --directory .tmp/f-08-project
```

- 起動の行は5行になる。4行目が `スキル: 3（add-conversion・release・review）`、5行目が `コマンド: /help で一覧`。3行目は `許可: allow-all・規則 0（設定ファイル無し）`
- 課題は1つずつ、新しい写しで試す（前の課題の書き換えと履歴が、次の課題に効かないように）。写し直すときは、前の写しを消してから写す（`cp -R` は、写し先のディレクトリがあると、その中に写す）
- 「一覧の大きさ」の課題では、スキルを写さない写しも作る（`mkdir` と2つ目の `cp` をしない。例: `cp -R tasks/f-08-skills/project .tmp/f-08-noskills`）。起動の4行目は `スキル: 無し` になる
- 走行の記録は、写しの中の `traces/` に書かれる

### 課題

| 課題 | 打つもの | 期待すること | 画面で見る所 | 走行の記録で見る所・判定 |
|---|---|---|---|---|
| 合う依頼で読み込む | `インチとセンチメートルの変換を足して` | 作業の前に `load_skill` で `add-conversion` を読み込み、手順の4つ（`RATES`・`CASES`・`CHANGELOG.md`・テスト）に沿って直す。変更の記録に足すことは、手順を読まなければ頼まれていない | `[道具] load_skill {"name": "add-conversion", …}` と `→ 8 行`（引数を渡したとき）。その後の `[道具]` の行 | `tool` の件（`name` が `load_skill`）の `input`・`result`（返した中身の全文）。判定はリポジトリの根で `.venv/bin/python tasks/f-08-skills/judge.py .tmp/f-08-project`（4つが通れば終了コード 0。写したばかりでは「テストが全て通る」だけが通る） |
| 付いているファイルを読む | `convert.py をレビューして` | `review` を読み込んだ後に、結果の一覧にある `.local-coding-agent/skills/review/checklist.md` を `read_file` で読み、4つの観点（誤り・端の値・名前・テスト）ごとに答える。ファイルは書き換えない | `[道具] load_skill {"name": "review", …}` の後の `[道具] read_file {"path": ".local-coding-agent/skills/review/checklist.md"…}` | `load_skill` の件の `result` の末尾の「付いているファイル」の行。答えが観点に沿うかは、人が読んで判定する |
| 合わない依頼で読まない | `convert.py の役目を1行で説明して` | `load_skill` を呼ばない | `[道具] load_skill` の行が出ない | `name` が `load_skill` の `tool` の件が無い |
| `/<名前>` で呼ぶ | `/review convert.py` | 本文の `$ARGUMENTS` が `convert.py` に置き換わり、付いているファイルの一覧を添えた中身が依頼として送られる。モデルは `load_skill` で読み込み直さない（既定の指示がそう言う） | `[スキル] /review → .local-coding-agent/skills/review/SKILL.md（10 行を依頼として送る）` の後に、打った依頼と同じく回が進む | `command` の件（`kind: skill`・`turn`・`source`・`text`）。次の `request` の件の `body.messages` の最後の発言の `content` が `<metadata>\n送った時刻: …\nスキル: /review convert.py\n</metadata>\n` で始まる。その回に `load_skill` の `tool` の件が無いか |
| 一覧 | `/help` | 自作のコマンド（`（無し）`）の後に、`スキル（.local-coding-agent/skills/。/<名前> で呼ぶか、モデルが読み込む）:` の節と3つ（`/add-conversion`・`/release`・`/review`）が出る。名前の列は、最も長い `/add-conversion` の幅で、組み込みの行も揃う。モデルを呼ばない | 一覧の後に数値の行（`[入力 … トークン・…]`）が出ない | `command` の件（`kind: builtin`・`output` に一覧）。`request` の件が増えない |
| 一覧の大きさ | スキルを写した写しと、写さない写しで、それぞれ `こんにちは` | 写した写しのほうが、1つ目の要求の入力トークン数が多い。差が一覧（「# スキル」の節と `load_skill` の定義）の大きさである | 数値の行の `入力 N トークン`（`/context` でも出る） | 1つ目の `response` の件の `model_stats.prompt_eval_count`。`request` の件の `body.messages` の最初（system）の末尾の「# スキル」の節と、`body.tools` の `load_skill`（`name` の `enum` に3つの名前）が、写さない写しには無い |
| 本文の大きさ | 「合う依頼で読み込む」の回 | `load_skill` の後の要求で、入力トークン数が増える。増えた分は、主に本文の大きさである | `load_skill` の前と後の数値の行 | `load_skill` の前と後の `response` の件の `model_stats.prompt_eval_count` |

`/help` の画面（材料の写しで）:

```text
組み込みのコマンド:
  /help            コマンドの一覧を出す
  …
  /exit            終える
自作のコマンド（.local-coding-agent/commands/）:
  （無し）
スキル（.local-coding-agent/skills/。/<名前> で呼ぶか、モデルが読み込む）:
  /add-conversion  長さの単位の変換を足す手順（引数: 足す変換。例: inch → cm）
  /release         版を上げて、リリースの準備をする（引数: 新しい版。例: 1.1.0）
  /review          コードを読み、誤りや分かりにくい所を挙げる。ファイルは書き換えない（引数: 対象のファイル）
```

起動の行・`/help`・`/review` の `[スキル]` の行と `<metadata>` は、答えに決まった値がある（画面と走行の記録で見る）。モデルが `load_skill` を呼ぶか・`checklist.md` を読むか・レビューの答えは、人が走行の記録と答えを読んで判定する。「合う依頼で読み込む」の直しは `judge.py` の終了コードで判定する。

走行の記録の、起動のときの2件目（`type` が `skills`）は、`skills`（1つが `name`・`source`・`description`）と `unusable`（1つが `entry`・`problem`）を持つ。材料の写しでは `skills` に3つ、`unusable` は空、写さない写しではどちらも空である。

### テストで確かめておらず、実物で見てほしいこと

- 実物のモデルが、依頼に合うときに `load_skill` を呼ぶか・合わないときに呼ばないか・`checklist.md` を読みに行くか・`/review` の後に読み込み直さないか
- Ollama が、道具の定義の `enum` をモデルにどう見せるか（定義の JSON はそのまま送るが、モデルの雛形での描き方は確かめていない）
- 実物の端末での `/help` の表示。揃えるのは名前の列だけで、日本語の説明は揃えの外である
- 起動（`main`）から `/review` を打つまでの通し。テストは `repl.run` に偽物の入力を渡した

### テストを走らせる

- `.venv/bin/python -m unittest tests.test_skills_catalog tests.test_skills_content tests.test_load_skill tests.test_repl_skills`: F-08 で足した4つのファイルの38件。約 0.04 秒（実測）
- `.venv/bin/python -m unittest tests.test_main.SkillsAtStartTest tests.test_commands_builtin tests.test_messages tests.test_context`: 起動・`/help` のスキルの節・`<metadata>` のスキルの行・既定の指示
- `.venv/bin/python -m unittest`: 全て（404件）

## 読む順

1. [__main__.py](../../../local_coding_agent/__main__.py#L83) の `main`
   - 入口: `python -m local_coding_agent`（[L154](../../../local_coding_agent/__main__.py#L154)）
   - 分かること: 起動の流れの全体。[L96](../../../local_coding_agent/__main__.py#L96) でスキルを探し、[L97](../../../local_coding_agent/__main__.py#L97) で道具を作る。許可の設定ファイルは `load_skill` を足した組で読む（[L101-L102](../../../local_coding_agent/__main__.py#L101-L102)。スキルが無くても `load_skill` の規則を誤りにしない）。[L108-L110](../../../local_coding_agent/__main__.py#L108-L110) で「# スキル」の節を system prompt につなぎ、[L115](../../../local_coding_agent/__main__.py#L115) で使えるスキルがあるときだけ道具を渡し、[L124](../../../local_coding_agent/__main__.py#L124) で一覧を `Session` に持たせる。[`_start_trace`](../../../local_coding_agent/__main__.py#L130) は記録の2件目（[L140](../../../local_coding_agent/__main__.py#L140)）と起動の4行目（[L144](../../../local_coding_agent/__main__.py#L144)）を書く。変わったのは約30行
2. [catalog.py](../../../local_coding_agent/skills/catalog.py) の [`discover_skills`](../../../local_coding_agent/skills/catalog.py#L65)・[`_examine`](../../../local_coding_agent/skills/catalog.py#L82)・[`read_skill`](../../../local_coding_agent/skills/catalog.py#L98)・[`skills_section`](../../../local_coding_agent/skills/catalog.py#L112)・[`describe_skills`](../../../local_coding_agent/skills/catalog.py#L120)・[`skills_record`](../../../local_coding_agent/skills/catalog.py#L129)
   - 入口: `main` の [L96](../../../local_coding_agent/__main__.py#L96)・[L109](../../../local_coding_agent/__main__.py#L109)、`_start_trace` の [L140](../../../local_coding_agent/__main__.py#L140)・[L144](../../../local_coding_agent/__main__.py#L144)
   - 分かること: 1段目（一覧）。置き場（[`SKILLS_PATH`](../../../local_coding_agent/skills/catalog.py#L22)）の下の一段のディレクトリを名前の順に見て、使えるもの（[`Skill`](../../../local_coding_agent/skills/catalog.py#L37)）と使えないもの（[`Unusable`](../../../local_coding_agent/skills/catalog.py#L49)）に分ける。名前の形は F-07 の `NAME`（[L84](../../../local_coding_agent/skills/catalog.py#L84)）で、`SKILL.md` は F-07 の `parse_custom` で読む（[L104](../../../local_coding_agent/skills/catalog.py#L104)）。節の始めの文は [`GUIDE`](../../../local_coding_agent/skills/catalog.py#L25) で、読み込み方の指示はここにある。`/help` の [`list_skills`](../../../local_coding_agent/skills/catalog.py#L147) は 6. で読む。約170行
3. [load_skill.py](../../../local_coding_agent/tools/load_skill.py) の [`definition`](../../../local_coding_agent/tools/load_skill.py#L19) と [`load_skill_tool`](../../../local_coding_agent/tools/load_skill.py#L49)
   - 入口: `load_skill_tool` は `main` の [L97](../../../local_coding_agent/__main__.py#L97)。モデルが呼ぶと、[tool_call.py](../../../local_coding_agent/loop/tool_call.py#L84) の `execute` が入力を照らし（[L92](../../../local_coding_agent/loop/tool_call.py#L92)）、許可を判定し（[L96](../../../local_coding_agent/loop/tool_call.py#L96)。読む道具をモードで通すときは [L108](../../../local_coding_agent/loop/tool_call.py#L108) で何も出さない）、`run`（[L52](../../../local_coding_agent/tools/load_skill.py#L52)）を呼ぶ
   - 分かること: 2段目（本文）の入口。`name` の `enum`（[L33](../../../local_coding_agent/tools/load_skill.py#L33)）に使えるスキルの名前を並べ、一覧に無い名前は [input_check.py](../../../local_coding_agent/tools/input_check.py#L52-L55) の `enum` の照らしで、実行の前に誤りになる。種類は `read`（[L64](../../../local_coding_agent/tools/load_skill.py#L64)）で、`target` を持たない。約65行
4. [content.py](../../../local_coding_agent/skills/content.py) の [`skill_text`](../../../local_coding_agent/skills/content.py#L18)・[`attached_files`](../../../local_coding_agent/skills/content.py#L35)・[`_files_text`](../../../local_coding_agent/skills/content.py#L58)
   - 入口: `load_skill` の `run` の [L60](../../../local_coding_agent/tools/load_skill.py#L60) と、`repl.py` の `_send_skill` の [L112](../../../local_coding_agent/cli/repl.py#L112)
   - 分かること: モデルの道と利用者の道で同じ中身を作る所。`SKILL.md` を読むたびに読み直し（[L23](../../../local_coding_agent/skills/content.py#L23)）、F-07 の `expand` で引数を入れる（[L26](../../../local_coding_agent/skills/content.py#L26)）。3段目（付いているファイル）は、中身を読まず、作業ディレクトリからのパスの一覧を添えるだけである（`.` で始まるものは [`_hidden`](../../../local_coding_agent/skills/content.py#L54) で除く。[`MAX_FILES`](../../../local_coding_agent/skills/content.py#L15) まで並べる）。約65行
5. [repl.py](../../../local_coding_agent/cli/repl.py) の [`handle_line`](../../../local_coding_agent/cli/repl.py#L51) と [`_send_skill`](../../../local_coding_agent/cli/repl.py#L107) → [`_send`](../../../local_coding_agent/cli/repl.py#L132) → [turn.py](../../../local_coding_agent/loop/turn.py#L40) の `run_turn` → [messages.py](../../../local_coding_agent/model/messages.py#L125) の `metadata_text`
   - 入口: `handle_line` は `repl.run`（`main` の [L126](../../../local_coding_agent/__main__.py#L126)）の [L48](../../../local_coding_agent/cli/repl.py#L48)。`run_turn` は `_send` の [L146](../../../local_coding_agent/cli/repl.py#L146)。`metadata_text` は [ollama_messages.py](../../../local_coding_agent/model/ollama_messages.py#L137) の `_content`（送る直前の変換）
   - 分かること: 利用者が `/<名前>` で呼ぶ道。組み込み → 自作のコマンドの後に、スキルを探す（[L69-L71](../../../local_coding_agent/cli/repl.py#L69-L71)）。`_send_skill` は読めなければ送らず（[L113-L116](../../../local_coding_agent/cli/repl.py#L113-L116)）、`[スキル]` の行と記録の1件を書いて、打った行を `skill` として `_send` に渡す（[L129](../../../local_coding_agent/cli/repl.py#L129)）。`_send` は `command` と `skill` の片方だけをキーワードで受ける。`run_turn` は打った行を [`user_text`](../../../local_coding_agent/model/messages.py#L79) の `skill` に入れ（[L54](../../../local_coding_agent/loop/turn.py#L54)）、`metadata_text` が [`SKILL_LABEL`](../../../local_coding_agent/model/messages.py#L21) の行を `<metadata>` に入れる（[L131](../../../local_coding_agent/model/messages.py#L131)。[`Message.skill`](../../../local_coding_agent/model/messages.py#L76)）。変わったのは約60行
6. [builtin.py](../../../local_coding_agent/commands/builtin.py) の [`_help`](../../../local_coding_agent/commands/builtin.py#L46)・[`help_text`](../../../local_coding_agent/commands/builtin.py#L98)・[`_listed_rows`](../../../local_coding_agent/commands/builtin.py#L120) と、[catalog.py](../../../local_coding_agent/skills/catalog.py) の [`list_skills`](../../../local_coding_agent/skills/catalog.py#L147)・[`_listed`](../../../local_coding_agent/skills/catalog.py#L160)
   - 入口: `_help` は `handle_line` の [L58](../../../local_coding_agent/cli/repl.py#L58) の `run_builtin`。`list_skills` は `_help` の [L50](../../../local_coding_agent/commands/builtin.py#L50)
   - 分かること: `/help` のスキルの節（[L114-L115](../../../local_coding_agent/commands/builtin.py#L114-L115)）。名前の列は組み込み・自作・スキルの全体で揃える。一覧は起動のときに探したもの（`Session.skills`）で、組み込みか自作のコマンドと同じ名前かは `_listed` が `/help` のときに見る（[L164](../../../local_coding_agent/skills/catalog.py#L164)）。変わったのは約30行
7. [system_prompt.py](../../../local_coding_agent/context/system_prompt.py#L49-L50) の既定の指示の2項と [`build_system_prompt`](../../../local_coding_agent/context/system_prompt.py#L70)、[session.py](../../../local_coding_agent/loop/session.py#L41) の `skills`
   - 入口: `build_system_prompt` は `main` の [L108](../../../local_coding_agent/__main__.py#L108)
   - 分かること: 既定の指示に足したのは「# スキル」の節があることと、`<metadata>` の「スキル: 」の行の意味（読み込み直さない）の2つだけで、読み込み方は 2. の `GUIDE` にある。`--system-prompt-file` で指示を差し替えても、節は残る（3つ目の部分）。約10行
8. テスト: [test_repl_skills.py](../../../tests/test_repl_skills.py) の [`SkillRepl`](../../../tests/test_repl_skills.py#L32)（偽物のモデルで REPL を回す道具立て）→ [`UserCallsSkillTest`](../../../tests/test_repl_skills.py#L58) → [`ModelLoadsSkillTest`](../../../tests/test_repl_skills.py#L131) → [test_skills_catalog.py](../../../tests/test_skills_catalog.py#L22) の `SkillsTestCase`・[`DiscoverTest`](../../../tests/test_skills_catalog.py#L44)・[`SectionTest`](../../../tests/test_skills_catalog.py#L116)・[`DescribeTest`](../../../tests/test_skills_catalog.py#L133)・[`ListSkillsTest`](../../../tests/test_skills_catalog.py#L167) → [test_skills_content.py](../../../tests/test_skills_content.py#L11) の `SkillTextTest`・[`AttachedFilesTest`](../../../tests/test_skills_content.py#L62) → [test_load_skill.py](../../../tests/test_load_skill.py#L14) の `DefinitionTest`・[`PermissionTest`](../../../tests/test_load_skill.py#L33)・[`RunTest`](../../../tests/test_load_skill.py#L49) → [test_main.py](../../../tests/test_main.py#L156) の `SkillsAtStartTest`（共通の準備は [`StartTestCase`](../../../tests/test_main.py#L78)）
   - REPL の振る舞いを先に掴み、部品のテストへ下りる。約600行
9. [tasks/f-08-skills/README.md](../../../tasks/f-08-skills/README.md) → `skills/` の [add-conversion/SKILL.md](../../../tasks/f-08-skills/skills/add-conversion/SKILL.md)・[review/SKILL.md](../../../tasks/f-08-skills/skills/review/SKILL.md)・[review/checklist.md](../../../tasks/f-08-skills/skills/review/checklist.md)・[release/SKILL.md](../../../tasks/f-08-skills/skills/release/SKILL.md) → [judge.py](../../../tasks/f-08-skills/judge.py) と、試した後の走行の記録（2件目の `skills`・`request` の system prompt の「# スキル」の節・`load_skill` の `tool` の件）

## 既存の実装からの変わり

### 足したファイル・直したファイル

- 足した:
  - [skills/catalog.py](../../../local_coding_agent/skills/catalog.py)・[skills/content.py](../../../local_coding_agent/skills/content.py)・`skills/__init__.py`
  - [tools/load_skill.py](../../../local_coding_agent/tools/load_skill.py)
  - `tests/test_skills_catalog.py`・`test_skills_content.py`・`test_load_skill.py`・`test_repl_skills.py`
  - `tasks/f-08-skills/`（`project/`・`skills/`・README・`judge.py`）
- 直した（移した関数は無い）:
  - [__main__.py](../../../local_coding_agent/__main__.py): `main` がスキルを探し、道具・許可の設定を読む道具の組・節・`Session` に渡す。走行の記録を始める所と起動の行を `_start_trace` に出し、記録の2件目と起動の4行目を足した
  - [repl.py](../../../local_coding_agent/cli/repl.py): `handle_line` が、自作のコマンドの後にスキルを探す。`_send_skill` を足した。`_send` の `command` をキーワードだけにし、`skill` を足した。`CommandKind` に `skill`
  - [builtin.py](../../../local_coding_agent/commands/builtin.py): `_help` と `help_text` にスキルの節。自作のコマンドの行を作る所を `_listed_rows` に出した
  - [custom.py](../../../local_coding_agent/commands/custom.py): 読めない理由の関数 `_reason` を `error_reason` にした（スキルでも使う）だけ
  - [messages.py](../../../local_coding_agent/model/messages.py): `Message.skill`・`user_text` の `skill`・`SKILL_LABEL`。`metadata_text` が、送った時刻・コマンドの行・スキルの行を並べる
  - [turn.py](../../../local_coding_agent/loop/turn.py): `run_turn` に引数 `skill`
  - [session.py](../../../local_coding_agent/loop/session.py): `skills`（起動のときの一覧。既定は空）
  - [system_prompt.py](../../../local_coding_agent/context/system_prompt.py): 既定の指示の2項（下）と、`build_system_prompt` の3つ目の部分
  - [input_check.py](../../../local_coding_agent/tools/input_check.py): `enum` を照らす
  - [ollama_messages.py](../../../local_coding_agent/model/ollama_messages.py): docstring の変換の表だけ（`sent_at・command・skill`）
  - テスト: `fakes.py`（`fake_session` の `skills`）・`test_commands_builtin.py`（`/help` のスキルの節。F-07 の `/help` のテスト2つを直した）・`test_context.py`（既定の指示）・`test_messages.py`（`<metadata>` のスキルの行）・`test_tools.py`（`enum`）・`test_main.py`（`StartTestCase` に共通の準備を分け、`SkillsAtStartTest` を足した）

### 振る舞いの変わり

- 利用者から見て:
  - 起動の行が1行増えた（4行目の `スキル: <数>（<名前>・…）`。無ければ `スキル: 無し`、使えないものがあれば `・使えない <数>（/help で理由）`）。`コマンド: /help で一覧` は5行目になった
  - 作業ディレクトリの `.local-coding-agent/skills/<名前>/SKILL.md` を置くと、モデルが依頼に合うと判断したときに `load_skill` で読み込む。画面には、ほかの道具と同じく `[道具] load_skill {…}` と `→ <行数> 行` が出る
  - `/<名前> [引数]` でスキルを呼べる。組み込み → 自作のコマンド → スキルの順に探す。送る前に `[スキル] /<名前> → <SKILL.md のパス>（<行数> 行を依頼として送る）` が出る。F-07 では知らない名前の誤りになった名前が、スキルとして送られる
  - `/help` の最後に、スキルの節が付く（スキルが無ければ `  （無し）`）。名前の長いスキルがあれば、組み込みの行もその幅で揃う
  - 一覧は起動のときに1度だけ探す。本文は読み込むたびに読む
- モデルへ送る要求:
  - 既定の指示の「ハーネスが入れる情報」に2項が加わった。「# 環境」の後の「# スキル」の節（あれば）と、`<metadata>` の「スキル: 」の行（利用者がスキルを呼び、中身を本文として送った。読み込み直さない）。スキルが無くても、この2項は入る
  - 使えるスキルがあれば、system prompt の「# 環境」の後に「# スキル」の節（読み込み方の文と、名前と説明の並び）が入り、道具の定義に `load_skill`（`name` の `enum` に名前）が加わる。無ければ、どちらも入らない
  - `load_skill` の結果（本文に引数を入れ、付いているファイルの一覧を添えたもの）は、道具の結果として履歴に入り、後の回でも送られる
  - `/<名前>` で呼んだ発言は、本文がスキルの中身で、`<metadata>` に `スキル: <打った行>` の行が入る
- 走行の記録:
  - 起動のときの2件目に、`type` が `skills` の件が入る（`skills`・`unusable`）。F-07 までは、1件目（`permissions`）の次が最初の `request` かコマンドの件だった
  - `load_skill` の呼び出しは、ほかの道具と同じ `tool` の件に入る
  - `/<名前>` でスキルを呼んだ行は、`command` の件の `kind` が `skill` になる（`source` は `SKILL.md` のパス）
  - ほかの件の欄は変わらない

### 依存の向き

`skills/catalog.py` → `commands/custom.py`（`parse_custom`・`error_reason`・`Listed`・`COMMANDS_PATH`）・`commands/parse.py`（`NAME`）。`skills/content.py` → `skills/catalog.py`・`commands/custom.py`（`expand`）。`tools/load_skill.py` → `skills/`・`model/chat.py`・`tools/tool.py`。`loop/session.py` → `skills/catalog.py`（`SkillCatalog`）。`cli/repl.py` → `skills/`。`commands/builtin.py` → `skills/catalog.py`（`list_skills`・`SKILLS_PATH`）。`__main__.py` → `skills/catalog.py`・`tools/load_skill.py`。`skills/` は `tools/`・`loop/`・`cli/` を知らない。依存のパッケージは足していない。

### 文書・試す材料・設定

- README: 「できること」に F-08 の行、画面の例に起動の4行目（`スキル: 無し`）、使い方に「skills」と「スキルを試す材料」の項を足し、「道具」（`load_skill`）と「走行の記録」（2件目と F-08 の文書へのリンク）の項を直した
- [コーディングエージェントの仕組み](../../how-coding-agents-work.md): 「スキル（skills）」の節を足し、「ハーネスとモデルの分担」の表に、モデルの「どのスキルを読み込むか」とハーネスの「スキルの一覧の組み立てと、本文の読み出し」を足した
- [作る機能](../../features.md): F-08 の行を足した
- `tasks/f-08-skills/`: 長さの単位の変換の小さなプロジェクト（写したばかりではテストが全て通る）と、写しの置き場に写す3つのスキル（変更の記録まで書く手順の `add-conversion`・観点を `checklist.md` にだけ持つ `review`・どの依頼にも合わない `release`）。判定は `judge.py`（「合う依頼で読み込む」の課題だけ）
- 設定（`.claude/`・`pyproject.toml`）は変わらない

### 取り込みで branch から変えた所

- コードは変えていない。衝突したのは `README.md` と `docs/features.md` だけである
- `README.md`: 使い方の F-07 の材料の項は、main の見出し「slash commands を試す材料」を残した（branch は前の「コマンドを試す材料」を持っていた）。「スキルを試す材料」の項は、その後に置いた
- `docs/features.md`: F-07 の行は、main の版（計測の結果へのリンクを持つ）を残し、F-08 の行を足した
- branch が分かれた後に main で入った commit は、F-07 の確認の文書と README の見出しだけで、F-08 のコードと重ならない
