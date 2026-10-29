# F-08 引き継ぎ

F-08 を実装したセッション（worktree 側）から、人の問いに答えるセッション（main 側）と、後のセッションへの引き継ぎである。人が読む想定ではない。書き方は `.claude/rules/docs.md` の「handoff.md」。

## 進み具合

- 段: **実装が済んだ**（2026-10-28）。main に取り込み、人が読む・試す段へ進める
- branch: `f-08-skills`（main の `4fe4670` から作った）
- commit:
  - `20e37af`: `spec.md` と、この引き継ぎの始めの版
  - `8c5cfdb`: コード・テスト・試す材料（`tasks/f-08-skills/`）・README
  - `8f485e5`: `implementation.md`・`docs/features.md`・`docs/how-coding-agents-work.md` の「スキル（skills）」の節
  - この引き継ぎの書き直し（この commit）
- テスト: 404件が通る（main の `4fe4670` の356件に、F-08 で48件を足した。F-07 の `/help` のテスト2つを直した）。Ruff・Ruff の整形・mypy（strict）も通る
- コードの見直しのエージェント（Claude Code の subagent）に見せ、指摘の一部を直した（下の「見直しで直したこと」）
- 実物のモデルでは走らせていない（CLAUDE.md の worktree 側）。試すのは main 側で行う

## main 側に頼むこと

- **取り込む**: `git merge f-08-skills`（`/merge-feature f-08-skills`）。main は分岐（`4fe4670`）の後に commit を積んでいないので、早送りになる（2026-10-28 に `git log f-08-skills..main` が空だった）。取り込む前に main が進んでいれば、下の「main と衝突しそうな所」を見る
- **progress.md**: worktree 側の branch は `f-08-skills` である
- **人に消してもらうもの**（Claude Code は消さない）: 判定と材料を確かめるために、worktree の `.tmp/` に写しを3つ作った（git には入らない）: `rm -rf .tmp/f08-judge-before .tmp/f08-judge-after .tmp/f08-materials`（worktree の中）
- **outbox の機能の記録**（`docs/outbox/F-08-…md`）: 実装の要点・設計の選択・読む順の案内（案）は、この引き継ぎから写す
- **Claude Code が実物のモデルで走らせるとき**（CLAUDE.md の main 側）: 材料の写し方は `tasks/f-08-skills/README.md` のとおり（プロジェクトを写し、`mkdir .tmp/<写し>/.local-coding-agent` の後に `skills/` を写す）。`.claude/agent-settings.json` は、同じ `.local-coding-agent/` に `settings.json` として置く。`load_skill` は読む道具なので、`accept-edits`・`ask` でも問わずに通る。依頼のファイルの1行 `/review convert.py` で、利用者がスキルを呼ぶ道も試せる
- **上流に上げてよいこと**: 下の「worktree の運用で分かったこと」（WebFetch の結果が大きい・Grep と Glob の道具が無い・`$` を含むコマンドが止まる）

## 仕様を決めるときに人と話したこと

- 持ち主の始めの指示: 「F-08を実装せよ」
- Claude Code は、仕様の案（置き場・名前と説明だけを指示に入れる・本文は選んだときに読む・付いているファイルはモデルが読む・ファイルの形は F-07 の自作のコマンドと同じ・スキルが無ければ一覧も道具も入れない・起動の行と走行の記録・作らないこと・試す材料）を示し、4つを問うた
- **読み込み方**: 「専用の道具 `load_skill`（推奨）」を選んだ（「今の `read_file` で読ませる」を選ばなかった）。ハーネスが前付けを除き、`$ARGUMENTS` を入れ、付いているファイルの一覧を添えて返す
- **置き場**: 「作業ディレクトリだけ（推奨）」を選んだ（`.local-coding-agent/skills/<名前>/SKILL.md`）。`.claude/skills/`・`.agents/skills/` は読まない
- **利用者が `/<名前>` で呼ぶ**: 「`/名前` でも呼べる」を選んだ（「モデルが選ぶだけ（推奨）」を選ばなかった）。組み込み → 自作のコマンド → スキルの順に探す。中身を利用者の発言として送り、`<metadata>` に「スキル: /<名前> <引数>」を入れる
- **一覧の置き場**: 「system prompt の節（推奨）」を選んだ（「`load_skill` の道具の説明の中」を選ばなかった）
- 案のほかの部分（名前はディレクトリの名前・前付けは `description` だけ・`disable-model-invocation` などは作らない・付いているファイルは 50 まで並べる・`enum` で名前を限る、など）は、問わずに案のまま進めた
- `/名前` でも呼べるようにしたので、Claude Code の `disable-model-invocation`（利用者だけが呼ぶ）にあたるものが欲しくなりうる。作らず、「利用者だけが呼ぶ手順は、F-07 の自作のコマンドに書く」と `spec.md` に書いた（持ち主には問うていない）
- 機能のディレクトリの名前と branch の名前は `f-08-skills` にした
- `spec.md` は、問いの答えを入れて Claude Code が書き、持ち主に改めて見せずに実装へ進んだ（F-04〜F-07 と同じ）。持ち主が `spec.md` を読んで異論があれば、main 側で受ける

## 実装の全体像

### ファイル

| ファイル | 役目 | 主な名前 |
|---|---|---|
| `local_coding_agent/skills/catalog.py` | 起動のときに置き場を探す・`SKILL.md` を読む・名前で探す・「# スキル」の節・起動の行・走行の記録の1件・`/help` の一覧 | `discover_skills`・`read_skill`・`find_skill`・`skills_section`・`describe_skills`・`skills_record`・`list_skills`・`Skill`・`Unusable`・`SkillCatalog`・`SkillError`・`SKILLS_PATH`・`SKILL_FILE`・`GUIDE` |
| `local_coding_agent/skills/content.py` | スキルの中身（本文に引数を入れ、付いているファイルを添える）。モデルの道と利用者の道で同じ | `skill_text`・`attached_files`・`MAX_FILES` |
| `local_coding_agent/tools/load_skill.py` | 道具 `load_skill`（一覧から作る。`name` の `enum`） | `load_skill_tool`・`definition`・`TOOL_NAME` |
| `local_coding_agent/tools/input_check.py` | `enum` を照らす | `_property_problem` |
| `local_coding_agent/loop/session.py` | `Session.skills`（起動のときの一覧） | |
| `local_coding_agent/cli/repl.py` | `/<名前>` でスキルを呼ぶ。`_send` の `command`・`skill` をキーワードにした | `handle_line`・`_send_skill`・`_send`・`CommandKind`（`skill` を足した） |
| `local_coding_agent/commands/builtin.py` | `/help` にスキルを並べる | `_help`・`help_text(…, skills)`・`_listed_rows` |
| `local_coding_agent/commands/custom.py` | `_reason` を `error_reason` にした（スキルでも使う）だけ | |
| `local_coding_agent/model/messages.py` | 利用者の発言のメタデータに、スキルの行 | `Message.skill`・`user_text(…, skill=None)`・`SKILL_LABEL` |
| `local_coding_agent/loop/turn.py` | 依頼にスキルの行を付けて受ける | `run_turn(…, skill=None)` |
| `local_coding_agent/context/system_prompt.py` | 「# スキル」の節をつなぐ・既定の指示の2項 | `build_system_prompt(…, skills_section="")`・`DEFAULT_INSTRUCTIONS` |
| `local_coding_agent/__main__.py` | 起動のときにスキルを探し、道具・規則・節・起動の行・走行の記録に渡す | `main`・`_start_trace` |
| `local_coding_agent/model/ollama_messages.py` | 変換の表の docstring だけ（`sent_at・command・skill`） | |
| `tasks/f-08-skills/` | 試す材料（`project/`・`skills/`・README・`judge.py`） | |
| `tests/test_skills_catalog.py` | 探す（名前の順・使えない理由・ディレクトリでないもの・シンボリックリンク・置き場が読めない）・節・起動の行・記録・`/help` の一覧 | `SkillsTestCase`・`skill`（ほかのテストも使う） |
| `tests/test_skills_content.py` | 中身（前付け・引数・末尾の `ARGUMENTS:`・付いているファイル・読むたびに読む・誤り）・付いているファイル（並び・`.` で始まるもの・50 を超えたとき・ほかのスキル） | |
| `tests/test_load_skill.py` | 定義の `enum`・種類と `target`・許可（モード・名前だけの規則・型を持つ規則は合わない）・結果・誤り | |
| `tests/test_repl_skills.py` | REPL の中（偽物のモデル）: `/<名前>` の送る形と記録・付いているファイルの行数・自作のコマンドと組み込みが勝つ・起動の後に空になった・起動の後に足した・`/help`・モデルが `load_skill` を呼んだ回の履歴 | |
| `tests/test_main.py` | 起動: 道具と節がスキルのあるときだけ入る・`--system-prompt-file` でも節が残る・記録の2件目・スキルが無くても `load_skill` の規則を読める。`StartTestCase` に共通の準備を分けた | |
| `tests/fakes.py`・`test_commands_builtin.py`・`test_context.py`・`test_messages.py`・`test_tools.py` | `fake_session(…, skills=)`・`/help` のスキルの節・既定の指示・`<metadata>` のスキルの行・`enum` | |

依存の向き: `skills/catalog.py` → `commands/custom.py`（`parse_custom`・`error_reason`・`Listed`・`COMMANDS_PATH`）・`commands/parse.py`（`NAME`）。`skills/content.py` → `skills/catalog.py`・`commands/custom.py`（`expand`）。`tools/load_skill.py` → `skills/`。`loop/session.py` → `skills/catalog.py`（`SkillCatalog`）。`cli/repl.py` → `skills/`。`commands/builtin.py` → `skills/catalog.py`（`list_skills`・`SKILLS_PATH`）。`skills/` は `tools/`・`loop/`・`cli/` を知らない。循環は無い。

### データの流れ

起動:

1. `main` が `discover_skills(cwd)` → `SkillCatalog`（使える `Skill` と使えない `Unusable`。名前の順）
2. `load_skill_tool(catalog)` で道具を作る。許可の設定ファイルは `(*DEFAULT_TOOLS, skill_tool)` で読む（スキルが無くても `load_skill` の規則を誤りにしない）
3. `build_system_prompt(instructions, environment_section(...), skills_section(catalog))`
4. `_start_trace`: 記録の1件目（許可）・2件目（`skills`）を書き、起動の行（`走行の記録`・`指示`・`許可`・`スキル`・`コマンド`）を出す
5. `Session(tools=(*DEFAULT_TOOLS, skill_tool) if catalog.skills else DEFAULT_TOOLS, skills=catalog)`

モデルが読み込む:

1. モデルが `load_skill {"name": "review", "arguments": "convert.py"}` を呼ぶ
2. `loop/tool_call.py` の `execute`（F-03・F-06 のまま）: `input_problem`（`enum` を含む）→ `decide`（読む道具・`target` 無し → モードで通す。`quiet` なので `[許可]` の行は出ない）→ `tool.run`
3. `run` が `find_skill` → `skill_text(cwd, skill, arguments.strip())`: `read_skill`（読むたびに読む）→ 本文が空なら誤り → `expand`（F-07）→ 空なら誤り → `attached_files` → 本文と一覧
4. 結果は `tool_result` として履歴に入る（後の回でも送られる）

利用者が呼ぶ:

1. `handle_line`: `parse_command` → `find_builtin` → `find_custom` → `find_skill(session.skills, name)` → `_send_skill`
2. `_send_skill`: `skill_text(cwd, skill, command.arguments)`（誤りなら `誤り: /<名前> のスキルを使えない: <理由>`・記録 `kind: skill`・`turn: null`）→ `[スキル] …` → 記録（`turn`・`source`・`text`）→ `_send(conversation, text, skill=command.line)`
3. `run_turn(…, skill=…)` → `user_text(text, sent_at, skill=…)` → 送る直前に `metadata_text` が `スキル: /review convert.py` の行を入れる

## 設計の選択と理由・捨てた案

- **一覧は起動のときに1度だけ探す**: system prompt を起動のときに1度だけ組み立てる（F-02）ので、一覧も同じ時に決まる。`/<名前>` と `/help` も同じ一覧（`Session.skills`）を使い、モデルと利用者で見えるスキルを揃えた。捨てた案: `/<名前>` だけは呼ぶたびに探す（F-07 の自作のコマンドと同じ）。モデルに見えないスキルを利用者だけが呼べるずれが出る
- **本文は読むたびに読む**: F-07 の自作のコマンドと同じ。起動の後の書き換えが効く
- **`SKILL.md` を F-07 の読み手で読む**: 形が同じ（前付けの `description`・本文・`$ARGUMENTS`）なので、`parse_custom` と `expand` を使い回した。Claude Code でも自作のコマンドは skills にまとめられている。`read_skill` は `CustomCommand` を返す（名前・パス・説明・本文の4つで、スキルにもそのまま当たる）
- **名前はディレクトリの名前で、前付けの `name` は読まない**: 名前の形（`NAME`）をディレクトリの名前に当てるだけで、置き場の外を指せないことが保てる。Claude Code も `name` を省けばディレクトリの名前になる
- **中身を作る関数を1つにした**（`skill_text`）: モデルの道と利用者の道で、送る文を同じにした（Claude Code の文書は、呼んだスキルの本文が「1つの発言として会話に入る」と書く）
- **付いているファイルのパスを作業ディレクトリからにした**: モデルがそのまま `read_file` に渡せる。スキルのディレクトリからの相対パスだと、モデルがつなぐ手間と誤りが増える（手元のモデルは小さい）
- **付いているファイルの中身は読まない**: 3段目（要るときに読む）を、モデルの判断に任せるため。読むのは既存の `read_file` で、許可の判定もそのまま効く
- **`load_skill` は `target` を持たない**: 照らす文字列を持たない道具として、名前だけの規則（`deny` の `load_skill`）だけが合う。スキルの名前を型で照らす規則（`load_skill(review)`）は、`permissions/policy.py` の `_call` に道具の種類を足すことになるので作らなかった。型を持つ規則は、誤りにもならず、黙って合わない（F-06 の「`target` を持たない道具」の扱いのまま）
- **スキルが無くても `load_skill` の規則を読む**: `.claude/agent-settings.json` のように、いくつもの写しで使い回す設定ファイルに `load_skill` を書いても、スキルの無い写しで起動が止まらないように
- **読み込み方の指示を「# スキル」の節に書いた**（既定の指示ではなく）: スキルが無いときに入らず、`--system-prompt-file` でも残る。既定の指示には「ハーネスが入れる情報」の2項だけを足した
- **`/help` の自作のコマンドと同じ名前かを、`/help` のときにファイルで見る**: `find_custom` と同じ `is_file()` の基準。捨てた案: `list_custom` の結果のラベルから名前を取り出す（ラベルの形に頼る）
- **`Message.skill` を `command` と並べた**: 捨てた案: `command` と `skill` を1つの「どこから来たか」の値にまとめる（F-07 の `command` の扱いを書き換えることになる）。見直しで「どちらか片方」と分かりにくいと指摘され、`_send` の docstring に書き、`run_turn` にはキーワードで渡すようにした

### 見直しで直したこと

コードの見直しのエージェント（Claude Code の subagent。読むだけ）の指摘のうち、次を直した。

- **付いているファイルに `.DS_Store` などが入り、50 の枠を埋めうる**: スキルのディレクトリからのパスで、`.` で始まる部分を持つものを除いた（`_hidden`）。置き場の `.local-coding-agent` は、スキルのディレクトリより上なので見ない（テストを足した）
- **`run_turn` に `command` と `skill` を位置で渡していた**: キーワードで渡し、`_send` の docstring に「どちらか片方」と書いた
- **テスト**: シンボリックリンクのディレクトリを辿ること・`.` で始まるファイルを除くこと、を足した

直さなかった指摘:

- **スキルのディレクトリがシンボリックリンクなら、作業ディレクトリの外の `SKILL.md` を読み、中身をモデルに渡す**: F-07 の自作のコマンドのファイルと同じく、置き場は利用者が書くものとして確かめない。`implementation.md` に書いた。モデルが `run_command` で置き場にリンクを作れば、次の起動で一覧に入り、外のファイルの中身がモデルに渡る（読むのはハーネス）
- **大きなディレクトリ（`node_modules` など）をスキルに置くと、読み込むたびに全てを辿る**: スキルのディレクトリは小さいものとした
- **`main` の長さ**: 45 行で、50 行の内に収まっている

## 実装前の仕様との違い

`implementation.md` の「実装前の仕様との違い」の表のとおり。仕様に無かった細部（`arguments` の前後の空白を除く・付いているファイルを見られないとき・`.` で始まるファイルを除く・自作のコマンドと同じ名前の見方・`error_reason`・`Session.skills`）だけで、振る舞いの大筋（置き場・3段・道具・中身の形・`/<名前>`・`/help`・起動の行・記録の欄・既定の指示）は仕様のとおりである。

## テストで確かめたこと・確かめていないこと

- 確かめた（F-08 で足した・直したもの）: 上の「ファイル」の表のテストのとおり
- Claude Code が手元で確かめた（モデルは使っていない）:
  - `tasks/f-08-skills/` を写した写しで、起動の行・「# スキル」の節・`/help` の一覧・`review` の中身を、`describe_skills`・`skills_section`・`help_text`・`skill_text` に掛けた。節は 290 字、3つの本文（付いているファイルの一覧を含む）は合わせて 771 字だった
  - `judge.py` は、写したばかりの写しで「テストが全て通る」だけが通って終了コード 1、手で変換・テストの場合・変更の記録を足した写しで4つとも通って終了コード 0 だった
- 確かめていない:
  - 実物のモデルが、依頼に合うときに `load_skill` を呼ぶか・合わないときに呼ばないか・`checklist.md` を読みに行くか・`/review` の後に読み込み直さないか
  - 実物の端末での `/help` の表示（日本語の説明は列の揃えの外）
  - `main()` から `/review` を打つまでの通し（`repl.run` はテストで偽物の入力を渡した）
  - Ollama が `enum` をモデルにどう見せるか（道具の定義の JSON はそのまま送るが、モデルの雛形での描き方は確かめていない）

## 人が問いそうなことと答え

- **スキルと自作のコマンド（F-07）は何が違うか**: ファイルの形は同じである。違いは誰が呼ぶかで、自作のコマンドは利用者だけが呼ぶ。スキルは、モデルが説明を見て自分で読み込む（利用者も `/<名前>` で呼べる）。そのため、スキルの名前と説明は毎回の要求に入り、自作のコマンドは何も入らない
- **一覧はどれくらい文脈を使うか**: 材料の3つで、「# スキル」の節は 290 字。トークン数は、スキルを写した写しと写さない写しの、1つ目の要求の入力トークン数の差で見る（`tasks/f-08-skills/README.md` の「一覧の大きさ」）
- **モデルが合わないスキルを読み込んだら**: 止めない。本文が道具の結果として履歴に入るだけである。どのスキルを読み込むかはモデルが決め、ハーネスは依頼と照らさない
- **同じスキルを2度読み込んだら**: もう一度読み、もう一度履歴に足す（2つ入る）。避ける仕組みは作っていない。利用者が `/<名前>` で呼んだ後は、既定の指示で「読み込み直さない」と伝える
- **`/clear` の後は**: 読み込んだ中身は履歴と一緒に消える。一覧は system prompt にあるので残り、モデルはまた読み込める
- **スキルの中のスクリプトを走らせるには**: 本文に「`.local-coding-agent/skills/<名前>/scripts/x.py` を走らせよ」と書けば、モデルが `run_command` で走らせる。許可は `run_command` の規則とモードのとおり。Claude Code の `allowed-tools` のような、スキルの間だけ通す仕組みは無い
- **Claude Code のスキルは使えるか**: `.claude/skills/<名前>/` を `.local-coding-agent/skills/` に写せば、本文・`description`・`$ARGUMENTS`・付いているファイルは効く。`name`（ディレクトリの名前が使われる）・`disable-model-invocation`・`allowed-tools`・`context: fork`・`${CLAUDE_SKILL_DIR}`・`` !`コマンド` `` は効かない（字のまま送られるか、読まれない）
- **一覧に入らないスキルがある**: `/help` に理由が出る（名前の形・`SKILL.md` が無い・読めない・本文が空）。起動の後に足したものは、起動し直すと入る

## 分かっている問題・残したこと

- **一覧の大きさに上限が無い**: スキルが多いと、毎回の要求が大きくなる。Claude Code の予算（文脈窓の 1%）と説明の切り詰めは作っていない
- **シンボリックリンク**: 上の「直さなかった指摘」
- **同じスキルを2度読み込む**: 上の「人が問いそうなこと」
- **要約（F-12）でスキルの中身が消えうる**: Agent Skills の案内は、要約で読み込んだ中身を残すことを勧めている。F-12 で考える
- **`load_skill` の型を持つ規則は、黙って合わない**: 誤りにすると親切だが、`permissions/rules.py` の `parse_rule` に道具ごとの扱いを足すことになる
- **`/help` の列**: 名前が長いスキル（`/add-conversion` の 15 字）があると、組み込みの行も全てその幅になる
- **`tasks/f-02-system-prompt/short.md`**: 既定の指示とさらに離れた（F-08 で「ハーネスが入れる情報」に2項を足した）
- F-07 から引き継いだもの: 置き場のシンボリックリンク・`/help` の列・`$` の印（`$ARGUMENTS` のほかの `$…` は字のまま）

## main と衝突しそうな所

main は分岐の後に commit を積んでいない（2026-10-28）。main で F-07 の確認の間に直しが入れば、次の所が F-08 と重なる。

- `local_coding_agent/cli/repl.py`: F-08 は `handle_line` の後半（自作のコマンドの後にスキルを探す）・`_send_skill`・`_send`（キーワードの `command`・`skill`）・`CommandKind`・docstring を直した
- `local_coding_agent/commands/builtin.py`: `_help` と `help_text`（スキルの節）・`_listed_rows`
- `local_coding_agent/commands/custom.py`: `_reason` → `error_reason` の3か所
- `local_coding_agent/model/messages.py`・`loop/turn.py`（`skill` の欄と引数）・`context/system_prompt.py`（既定の指示の「ハーネスが入れる情報」の2項と `build_system_prompt`）・`loop/session.py`・`__main__.py`（`main` の後半と `_start_trace`）
- `tests/test_commands_builtin.py`（`HelpTextTest`）・`tests/test_main.py`（`StartTestCase` に分けた）・`tests/fakes.py`
- `README.md`（「できること」の表・画面の例・道具の項・「skills」の項・走行の記録の項・材料の項）・`docs/features.md` の表・`docs/how-coding-agents-work.md`（「スキル」の節・分担の表）
- main が F-07 の `guide.md` を直すときに、`/help` の画面の例を書いていれば、F-08 の後はスキルの節（`（無し）`）が増える。F-07 の guide.md の注釈（skill `merge-feature` の 6.）が要るかもしれない

## worktree の運用で分かったこと

- **WebFetch の結果が大きい**: `https://code.claude.com/docs/en/skills` は 117,904 字で、1回目と2回目は始めの 100,000 字だけが答えに使われた。続きを `offset` で読むと、要約されずに本文がそのまま返った（約 18,000 字。リポジトリの外には保存されなかった）
- **Grep・Glob の道具が、このセッションにも無かった**（F-05〜F-07 と同じ）。探すのは `git grep` と Read で行った。`git grep` は git に入っていないファイルを探さない（新しいファイルは Read で確かめた）
- **`$` を含むコマンドは deny で止まる**（progress.md の申し送りのとおり）。`echo "exit=$?"` が止まったので、`&& echo … || echo …` にした
- **整形は `ruff format <ファイル>` で行った**: 新しく書いたファイルと、F-08 で触ったファイルだけに掛けた。Python 3.14 の Ruff は、`except (A, B):` を括弧の無い `except A, B:` に書き換える（PEP 758）
- **見直しのエージェントは読むだけで指摘を出した**（`python` などは走らせないよう頼んだ）
- `.venv/` は、前のセッションが作ったものがそのまま使えた（`pyproject.toml` は F-07 から変わっていない）。`poetry install` は走らせていない
- branch を `git switch -c f-08-skills main` で作ると、作業ツリーが main の中身（F-07 の branch より新しい CLAUDE.md など）に替わった。Claude Code は、読んだ後に変わったファイルを読み直すよう求めた

## 読む順の案内（案）

呼ばれる側を挙げるときは、それを呼ぶ入口を一緒に挙げる（F-01 からの申し送り）。

1. `local_coding_agent/__main__.py` の `main`（起動の入口）: スキルを探し、道具・規則・節・起動の行・走行の記録に渡す所。F-08 の起動の流れの全体
2. `local_coding_agent/skills/catalog.py`（`main` の `discover_skills`・`skills_section`・`describe_skills`・`skills_record`）: 置き場を探す・使えない理由・「# スキル」の節。1段目（一覧）
3. `local_coding_agent/tools/load_skill.py`（`main` の `load_skill_tool`。モデルが呼ぶと `loop/tool_call.py` の `execute` が `tool.run` を呼ぶ）: 道具の定義の `enum` と、2段目（本文）の入口
4. `local_coding_agent/skills/content.py`（`load_skill` の `run` と、`repl.py` の `_send_skill` の `skill_text`）: 本文に引数を入れ、付いているファイルを添える所。3段目（付いているファイル）は一覧を添えるだけ
5. `local_coding_agent/cli/repl.py` の `handle_line` と `_send_skill`（`__main__.py` の `repl.run` から）→ `loop/turn.py` の `run_turn(…, skill=…)` → `model/messages.py` の `metadata_text`: 利用者が `/<名前>` で呼ぶ道
6. `local_coding_agent/commands/builtin.py` の `_help`・`help_text`（`/help`）と、`catalog.py` の `list_skills`
7. `local_coding_agent/context/system_prompt.py`: 既定の指示の2項と `build_system_prompt`。`tools/input_check.py` の `enum`
8. テスト: `tests/test_repl_skills.py`（振る舞いを掴む）→ `test_skills_catalog.py` → `test_skills_content.py` → `test_load_skill.py` → `test_main.py` の `SkillsAtStartTest`
9. `tasks/f-08-skills/`（README → `skills/` の3つ → `judge.py`）と、試した後の走行の記録（`skills` の件・`request` の system prompt の「# スキル」の節・`load_skill` の `tool` の件）

## 問いと答えの記録

main 側のセッションが、人から来た問いと答え・直したことを足す。

### 取り込み（2026-10-29・main 側）

- `/merge-feature f-08-skills` で取り込んだ。取り込んだ commit は `67ebd42`、基点（取り込む前の main）は `a0e73a0`
- 早送りにはならなかった。main は分岐（`4fe4670`）の後に、F-07 の確認の間の commit を5つ積んでいた（`5e527df`・`5d225e2`・`25cefe6`・`bba0489`・`a0e73a0`）。触ったのは `README.md`・`docs/features.md`・`docs/features/f-07-slash-commands/` の下だけで、コードは触っていない
- 衝突したファイルと解き方:
  - `README.md`: 使い方の材料の項。main は F-07 の材料の見出しを「コマンドを試す材料」から「slash commands を試す材料」に直し（`5e527df`。持ち主の答え）、branch は F-07 の項の後に「スキルを試す材料」を足していた。main の見出しを残し、branch の F-08 の項を足した
  - `docs/features.md`: 表の F-07 の行。main は「計測の結果」へのリンクを足し（`a0e73a0`）、branch は F-08 の行を足していた。main の F-07 の行を残し、branch の F-08 の行を足した
- 意味の衝突は無い（main はコードを触っていない）
- 検査: テスト404件・`ruff check`・`ruff format --check`・mypy が通った
- main で直したことは無い

### implementation.md の画面の例の行数（2026-10-29・main 側）

- 問い（main 側から持ち主へ）: `implementation.md` の「使い方」の画面の例は `/review convert.py` を「12 行を依頼として送る」と書くが、材料の `review` で `skill_text` を実測すると10行（本文6行・空の行・スキルのディレクトリ・見出し・`checklist.md` の1行）だった。10行に直してよいか
- 答え: 「良い」
- 直したこと: `implementation.md` の画面の例を10行にした。`guide.md` は始めから10行と書いていたので、変えていない

### Claude Code の動作検証（2026-10-29）

- 頼み（持ち主）: 「あなたの方で課題の実施を行え」「.tmp/f-08-project/ は私が使っているため触るな」
- 走らせ方: `tasks/f-08-skills/README.md` のとおりに、材料を `.tmp/cc-f08-*` に写した（`project/` を写し、`.local-coding-agent/skills/` にスキルを写す）。写しの `.local-coding-agent/settings.json` に `.claude/agent-settings.json`（モード `accept-edits`・`allow` は `run_command(python3 -m unittest*)`）を置いた。リポジトリの根で `--directory <写し>` を付け、標準入力に依頼のファイルを渡した。モデルは `qwen3.5:9b`。課題ごとに新しい写しで、1つずつ順に走らせた。持ち主の走行と同じ Ollama を使ったので、時間はその影響を受けうる
- 結果（走行の記録は写しの `traces/` の下。git に入れていない。時間は各歩の「全体」の和）
  - 合う依頼で読み込む（`cc-f08-add`・`20261029-084630`）: 通った（`judge.py` の4つが全て通り、終了コード 0）。1歩目で `load_skill {"name": "add-conversion", "arguments": "inch → cm"}` を呼んだ（引数は説明の「例: inch → cm」と同じ形）。その後、手順どおり `convert.py`・`test_convert.py` を読んで `RATES` と `CASES`（2行）に足し、`CHANGELOG.md` を読んで「## 未リリース」の下に `- 変換 inch → cm を足した` を足した。手順の4.の `python -m unittest` は、規則の `allow`（`python3 -m unittest*`）に合わず、問われて拒まれた。モデルは `python -m unittest 2>&1`（`timeout` 30）で試し直し、また拒まれ、手で確かめるよう書いて終えた。10歩・約 198 秒
  - 付いているファイルを読む（`cc-f08-review`・`20261029-085013`）: 1歩目で `load_skill {"name": "review", "arguments": "convert.py"}`、2歩目で `convert.py` と `.local-coding-agent/skills/review/checklist.md` を同じ応答の中で読み、4つの観点の見出しで答えた。ファイルは書き換えなかった。3歩・約 94 秒。答えの中身には誤りがある（Claude Code の読み）: 1.で「`(target, source)` が `RATES` にあれば `value / RATES[(target, source)]` を返す処理は意味をなさない」と書くが、逆向きの変換として正しい。4.の「逆方向の変換比率」も同じ誤り。表に無い組（`mile` → `m` など）で `ValueError` になる点は、4.の「連鎖変換」として当たっている
  - 合わない依頼で読まない（`cc-f08-explain`・`20261029-085200`）: `load_skill` を呼ばなかった。`list_directory` → `read_file convert.py` → 1行で答えた（「長さの単位（km ↔ m, mile ↔ km など）を変換する Python モジュール」）。3歩・約 26 秒
  - `/<名前>` で呼ぶ（`cc-f08-slash`・`20261029-085235`）: `[スキル] /review → .local-coding-agent/skills/review/SKILL.md（10 行を依頼として送る）`。`command` の件は `kind: skill`・`turn: 1`・`source`・`text`（付いているファイルの一覧を含む）。要求の最後の発言は `<metadata>\n送った時刻: …\nスキル: /review convert.py\n</metadata>\n` で始まった。モデルは `load_skill` で読み込み直さず、1歩目で `convert.py` と `checklist.md` を読み、4つの観点の見出しで答えた。2歩・約 79 秒。答えの中身には誤りがある（Claude Code の読み）: 1.で「km → m の逆変換が RATES に存在しないため例外となる」と書くが、`m` → `km` は逆向きで求まる。4.で「コード自体にはテストが含まれておらず」と書くが、`test_convert.py` を読んでいない
  - 一覧（`cc-f08-hello`・`20261029-084536`）: `/help` は guide.md の画面のとおり（スキルの節に3つ・名前の列は `/add-conversion` の幅）。`command` の件は `kind: builtin`、要求は増えなかった
  - 一覧の大きさ（`cc-f08-hello`・`cc-f08-noskills`・`20261029-084434`）: `こんにちは` の1つ目の要求の `prompt_eval_count` は、スキル有りが 2446、スキル無しが 2121 で、差は 325 トークン（「# スキル」の節 290 字と、`load_skill` の定義の分）。写しのディレクトリの名前が違うので、「# 環境」の節の作業ディレクトリも数トークン違いうる。スキル無しの写しの要求は、`tools` に `load_skill` が無く、system prompt に「# スキル」の節が無かった。2つ目の件（`skills`）は、スキル有りが3つ、スキル無しは `skills`・`unusable` とも空
  - 本文の大きさ: `load_skill` の前と後の要求の `prompt_eval_count` は、`add-conversion` が 2453 → 2720（+267。結果は 319 字）、`review` が 2449 → 2661（+212。結果は 238 字）。増えた分には、モデルの呼び出しの発言も入る
  - `load_skill` の `tool` の件は、`permission` が `{"decision": "allow", "reason": "モード accept-edits", "rule": null, …}`・`confirmed` が `null` で、画面に `[許可]` の行は出なかった（読む道具をモードで通したため）
- 分かったこと
  - 3つの依頼のどれでも、モデルは合うスキルだけを読み込み、合わない依頼では読まなかった。付いているファイル `checklist.md` は、モデルの道でも利用者の道でも、一覧のパスのまま読んだ
  - `add-conversion` の手順は `python -m unittest` と書くので、Claude Code の走らせ方の規則（`python3 -m unittest*`）では走らない。既定のモード `allow-all` では走る（この機械で `python` が見つかるかは確かめていない）。F-07 の `fix.md` と同じく、F-08 の誤りではない
  - レビューの答えは、2回とも観点の形には沿ったが、中身に誤りを含んだ。判定は持ち主が行う
- 直したことは無い

### Ollama へ送る情報を組み立てる場所（2026-10-29・main 側）

- 問い: 「ソースコードの、Ollamaへ送信する情報を組み立てている場所を示せ」
- 答え（F-08 の取り込みの後のコードで確かめた）:
  - 送る JSON の全体は `model/ollama_messages.py` の `chat_request_body` で作る（`model`・`messages`・`stream: true`、道具があれば `tools`）。`to_ollama_messages`（system prompt を先頭の system の発言にする）・`_assistant`（thinking・tool_calls）・`_user`（結果の塊を tool の発言に）・`_tool_message`・`_content`（`metadata_text` と本文をつなぐ）が会話を変え、`to_ollama_tools` が道具の定義を変える
  - それを呼ぶのは `model/ollama.py` の `OllamaChat.build_request`（URL を `<host>/api/chat` にする）で、さらにそれを呼ぶのは `loop/model_call.py` の `call_model`（毎歩、`session.system`・道具の定義・会話の全体を渡し、要求の件を走行の記録に書く）。送るのは `OllamaChat.stream`（`json.dumps` して POST）
  - 材料の出所: system prompt は `__main__.py` の `main` が起動のときに1度だけ `build_system_prompt` で組む（指示・「# 環境」・「# スキル」）。道具は `main` が `Session.tools` に入れる（スキルがあれば `load_skill` を足す）。会話は `loop/turn.py` の `run_turn` が、依頼の発言（メタデータつき）・モデルの発言・結果の発言を足していく
- 直したことは無い

### 条件ごとの、モデルへ送る要求の形の一覧（2026-10-29・main 側）

- 問い: 「それぞれの条件（システムプロンプト付きの初回メッセージ、コマンド呼び出し、ツールの呼び出し、etc）でどのようなフォーマットでメッセージが送られるかの、一覧を見たい」。特に、利用者が使う機能の情報が、ハーネスが独自に定義した枠に入るのか、作り付けの引数に入るのか。最後まで知りたい情報なので、実装に入っているのが理想。人が読む markdown でもよいが、実装に追従させる工夫が要る。まず案を出せ
- 答え（案）: ①手で書く markdown と追従の規則 ②場面ごとの期待の JSON を直に書くテスト ③場面の台本から markdown を生成し、ずれをテストで止める、の3つを示し、③を勧めた
- 持ち主の答え: 「案3を実装せよ」「現段階の文書は、今あなたが作成せよ」「今後実装される機能については、機能実装のworktreeが機能を実装した際に実装されるようにせよ」「main側で `/merge-feature` による確認中に実装が変更された際には、main側で更新するようにせよ」「置き場や範囲はそれで良い」（置き場は `docs/`・場面は10個）
- 直したこと:
  - `02d49ec`: `tests/request_formats/`（場面10個・起動の入口 `main` から実物のコードに通して要求の本文を集める `harness.py`・見どころを照らす `check.py`・文書の組み立て）と `tests/test_request_formats.py`（commit した文書と今のコードから生成した文書を比べる）。生成した `docs/request-formats.md` と、`docs/README.md` の読む順
  - `ee30b22`: CLAUDE.md に「モデルへ送る要求の形」の節と、worktree 側（機能が送る形を変えるなら場面を足す）・main 側（確認の間の直しで変われば直す）の項。skill `merge-feature` に、衝突のときと検査で落ちたときの生成し直し・既存の実装からの変わりで文書の差分を確かめ、場面が無ければ足すこと・7. の追従
- 作りの要点: 差し替えるのは、モデルの応答（台本）・利用者の入力（`builtins.input`）・時刻（`local_now`）・環境（`collect_environment`）・家のディレクトリ（`Path.home`）・画面だけ。要求は実物の `OllamaChat.build_request` で作り、`stream` で `json.dumps` してから読み戻した本文を集める。一時ディレクトリのパスが要求に入れば止める。見どころは「情報・伝わり方（Ollama の欄・ハーネスの枠・ハーネスの値・そのままの文・送らない）・場所・照らした文・作る所」で、生成のときに照らし、合わなければ止める。作る所の行の番号は `inspect` で取り、文書の最後の「作る所」の節にだけ置く（行が動いただけの差分を、場面の節に出さないため）
- 一覧で分かったこと（コードは変えていない）: 止めた回と誤りで止まった回の知らせは、内部では結果の発言の末尾の本文の塊だが、Ollama の形では tool の発言の後の、別の user の発言になり、次の依頼と user の発言が2つ並ぶ。`--system-prompt-file` では、既定の指示の「# ハーネスが入れる情報」の説明が無くなるので、`<metadata>` などの枠の説明もモデルに届かない
- 持ち主に問うこと: 「今後実装される機能については…」「main 側で…更新するようにせよ」は続けて守る指示なので、要件として写しに書いて上流へ上げるか
- 持ち主の答え: 「上流へ送る必要はない」。要件として写しに書かず、上流に上げない（このリポジトリの細部として、CLAUDE.md と skill `merge-feature` にだけ書いた）

### 材料の add-conversion のテストのコマンド（2026-10-29・main 側）

- 問い（main 側から持ち主へ。Claude Code の動作検証で、手順の4.の `python -m unittest` が規則の `python3 -m unittest*` に合わず、問われて拒まれた）: 材料の `add-conversion/SKILL.md` の `python -m unittest` を、`python3 -m unittest` に替えるか
- 答え: 「そうせよ」
- 直したこと（`6d6e86e`）: `tasks/f-08-skills/skills/add-conversion/SKILL.md` の手順の4.と、それを例に引く `implementation.md` の「使い方」を `python3 -m unittest` にした。行数は変わらない（`load_skill` の結果の行数・guide.md は変わらない）。`skills/release/SKILL.md` の3.・`project/README.md`・材料の README の判定の表の `python -m unittest` は、問いの範囲の外なので変えていない

### スキルの説明・本文がコンテキストをどう使うか（2026-10-29・main 側）

- 問い: 次の5つは正しいか。このアプリと Claude Code のそれぞれについて答えよ。①適切なタイミングで呼ぶために、スキルの説明をモデルに送る必要がある ②スキルの説明は system prompt に入る（スキルを入れるほど system prompt が大きくなり、コンテキストを使う）③利用時にスキルの全文が読み込まれ、以降の履歴に入る ④同じスキルを複数回呼ぶと、全文が呼んだ回数分、履歴に入る ⑤呼ぶかはモデルの判断で、人の想定する条件と違うことは常にありうる
- 答え（このアプリ。コードで確かめた）:
  - ①正しい。モデルが選ぶには説明が要る。利用者が `/<名前>` で呼ぶだけのスキルでも、説明は必ず送る（`disable-model-invocation` にあたるものは作っていない。F-08 の仕様）
  - ②正しい。`skills_section` が「# スキル」の節を system prompt の最後に足し、`main` が道具 `load_skill`（`enum` にスキルの名前）を足す。数・字数の上限は無い。毎回の要求で送り直す。実測は3つで 325 トークン
  - ③ほぼ正しい。前付けは除き、`$ARGUMENTS` を入れた本文と、付いているファイルのパスの一覧（中身ではない）が入る。`load_skill` なら tool の発言、`/<名前>` なら依頼の発言として、`/clear` まで残り、毎回送り直す。要約（F-12）は無いので、消えない
  - ④正しい。呼ぶたびに読み直して、同じ文を返す。重ねないための仕組みは無い。既定の指示が止めるのは、`/<名前>` で送ったスキルを読み込み直すことだけ
  - ⑤正しい（モデルが読み込む道について）。確実に使わせる道は、利用者の `/<名前>` だけ。逆に、モデルに使わせない手段は無い
- 答え（Claude Code。公式の文書 https://code.claude.com/docs/en/skills を 2026-10-29 に確かめた。置き場はこのセッションで見えた形）:
  - ①正しい。ただし、一覧の予算（コンテキストの窓の 1%）を超えると、使う回数の少ないスキルから説明を落とし、名前だけにする。`disable-model-invocation: true` のスキルは、一覧に出ない（このセッションで、`merge-feature` は一覧に無かった）
  - ②前半は誤り、後半はほぼ正しい。文書は置き場を書かず、"loaded into context" とだけ書く。このセッションでは、system prompt ではなく、会話の中の system-reminder に入っていた（Skill の道具の説明も "Available skills appear in a system-reminder listing" と書く）。"Every skill in the skill listing adds to your context on every turn"。ただし、予算があるので、上限なく大きくはならない（名前は全て残る。1つの説明は 1,536 字まで。`skillListingBudgetFraction` などで変えられる）
  - ③ほぼ正しい。"the rendered SKILL.md content enters the conversation as a single message and stays there across later turns"。付いているファイルは、読んだときだけ入る。例外は `context: fork` で、本文は subagent に渡り、元の会話の履歴には入らない。要約（compaction）の後は、スキルごとに最後に呼んだ1回を、先頭の 5,000 トークンまで付け直す（全部で 25,000 トークンまで）
  - ④誤り（中身が同じなら）。"When Claude re-invokes a skill whose rendered content is identical to the copy already in context, Claude Code adds a short note that the skill is already loaded rather than a second copy"。引数や動的な中身が変われば、全文をもう一度足す
  - ⑤正しい。文書も "Seeing a skill trigger tells you Claude found it, not that it did what you intended" と書く。確実にする道は `/<名前>` と、`disable-model-invocation`（使わせない）と、必ず守る規則を hook に移すこと
- 直したことは無い

### Claude Code の skill と command の違い（2026-10-29・main 側）

- 問い: 「ClaudeCodeのskillとcommandの違いは、ClaudeCodeが自動で実行するかどうか　のみか」
- 答え（公式の文書 https://code.claude.com/docs/en/skills を 2026-10-29 に確かめた）: それだけではない。文書は "Custom commands have been merged into skills" "both create `/deploy` and work the same way" と書く。違いは、①形（command は `.claude/commands/` の .md の1ファイル、skill はディレクトリと `SKILL.md`）②付いているファイル（skill だけ。文書は "Prefer a skill for new work, since skills also support supporting files"）③前付け（command は "the same frontmatter except `name` and `paths`"。ファイルに触れたときだけ働く `paths` は skill だけ）④名前（command は下のディレクトリを `:` でつなぐ。例 `/frontend:component`）⑤同じ名前なら skill が勝つ
- 自動で使うか: 文書の中で食い違う。始めの注は skill が足すものに "the ability for Claude to load them automatically when relevant" を挙げるが、command は `disable-model-invocation` を含む同じ前付けを持ち、"work the same way" とも書く。このセッションでモデルに見える一覧には、`build-fix: Build and Fix`・`learn: /learn - Extract Reusable Patterns` のように、見出しの1行を説明にしたものがある。持ち主の `~/.claude/commands/` のファイルに見えるが、リポジトリの外なので確かめていない。どちらにしても、モデルが使うかは skill か command かより、`disable-model-invocation`・`user-invocable` で決まる
- このアプリとの違い: このアプリでは、自作のコマンド（F-07）はモデルに一覧を送らず（`docs/request-formats.md` の場面 4）、スキル（F-08）は必ず送る。本文の形は同じ（同じ読み手 `parse_custom`）で、違いはモデルが選べるかと、付いているファイルの一覧と、`load_skill` の道だけである
- 直したことは無い

### Claude Code で、人だけが呼ぶ手順をどう作るか（2026-10-29・main 側）

- 問い: 「常に人間が指定して実行させたい機能（旧来のslash commandのような）をどのように実現すべきか、想定はあるか」
- 答え（公式の文書 https://code.claude.com/docs/en/skills を 2026-10-29 に確かめた）: 想定はある。前付けの `disable-model-invocation: true`。文書は "Use this for workflows with side effects or that you want to control timing, like `/commit`, `/deploy`, or `/send-slack-message`" と書く
  - 説明はモデルに送らない（"This removes the skill from Claude's context entirely"）。モデルが呼ぼうとすると止め、"instructs it not to reproduce the deploy steps another way"。subagent への前読みと、予定の作業からの実行も止まる
  - 注意: 文の途中に `/deploy` と書くと、その発言の間はモデルが呼んでよいことになる（"The name counts as your permission for that message"）。`disable-model-invocation` のスキルにも当たるかは、文書に無い。すぐ走らせるなら、発言の頭に置く
  - ほかの手段: SKILL.md を直さずに設定の `skillOverrides` で `"user-invocable-only"` にする（モデルに見せず、`/` の一覧には出す）。許可の規則 `Skill(deploy *)` を deny にする（モデルの Skill の呼び出しを止める。利用者の `/deploy` に効くかは文書に無い）
  - 限界（Claude Code の推論）: 止めるのはスキルを呼ぶことで、モデルが同じ操作を道具で直に行うことは、指示の文で止めるだけである。必ず止めたい操作は、その操作そのもの（`git push` など）を許可の規則か hook で止める
  - このリポジトリの例: `.claude/skills/merge-feature/SKILL.md` は `disable-model-invocation: true` を持ち、このセッションのモデルに見える一覧に無い
- このアプリ: 人だけが呼ぶ手順は、F-07 の自作のコマンドに書く（F-08 の仕様）。スキルにはモデルに見せない設定が無い
- 直したことは無い
