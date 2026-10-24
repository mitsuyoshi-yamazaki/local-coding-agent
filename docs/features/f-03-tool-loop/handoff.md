# F-03 引き継ぎ

F-03 を実装したセッション（worktree 側）から、人の問いに答えるセッション（main 側）と、後のセッションへの引き継ぎである。人が読む想定ではない。書き方は `.claude/rules/docs.md` の「handoff.md」。

## 進み具合

- 段: **実装が済んだ**（2026-10-24）。main に取り込み、人が読む・試す段へ進める
- branch: `f-03-2`（main の `225acce` から）。`f-03` ではない（下の「仕様を決めるときに人と話したこと」）
- commit:
  - `771849f`: `spec.md` と、この引き継ぎの始めの版（前のセッションが `f-03` に書いた `6fc4e6f` を cherry-pick した）
  - `625e393`: コード・テスト・試す材料（`tasks/f-03-tool-loop/`）・README
  - `203be12`: `implementation.md`・`docs/features.md`・`docs/how-coding-agents-work.md` の「道具の呼び出し」の節・`docs/technologies/ollama.md` の「道具の呼び出しと推論」の節
  - この引き継ぎの書き直し（この commit）
- テスト: 102件が通る（F-02 までの45件を含む）。Ruff・Ruff の整形・mypy（strict）も通る
- 実物のモデルでは走らせていない（F-06 まで、実物のモデルで走らせるのは人だけ）。作るエージェントの起動も行っていない（下の「worktree の運用で分かったこと」）

## main 側に頼むこと

- **取り込む**: `git merge f-03-2`（F-02 の確認が済んでから）
- **progress.md**: worktree 側の branch は `f-03-2` である。progress.md の「`f-03`（まだ commit は無い）」は古い
- **人に消してもらうもの**（Claude Code は消さない）:
  - branch `f-03`（`6fc4e6f` の仕様の commit だけを持つ。同じ中身を `771849f` に取り込んだ）: `git branch -D f-03`
  - stash の `WIP on f-03: 6fc4e6f …`（前のセッションの、途中までの実装。持ち主の指示で使わなかった）: `git stash list` で番号を確かめてから `git stash drop stash@{<番号>}`
  - 取り込んだ後の `f-03-2`
- **outbox の機能の記録**（`docs/outbox/F-03-…md`）: 実装の要点・設計の選択・読む順の案内（案）は、この引き継ぎから写す
- **上流に上げてよいこと**: 下の「worktree の運用で分かったこと」と、「分かっている問題・残したこと」の「判定のコマンドが無い」

## 仕様を決めるときに人と話したこと

### 前のセッション（branch `f-03`）

- 持ち主の始めの指示: 「f-03 を実装せよ」。Claude Code は、仕様の案（ループ・会話の形・道具・確かめる・表示と記録・system prompt・試す材料・作らないこと）を示し、4つを問うた。持ち主は4つとも推奨の案を選び、ほかの部分に異論は無かった
- **道具**: 「read_file と list_directory」を選んだ（「read_file だけ」を選ばなかった）。モデルが一覧を見て、読み、答えるという、ループが何歩も回る様子を見せるため
- **確かめる**: 「仕組みだけ作る」を選んだ。道具に「変更を伴うか」の印を持たせ、印のある道具だけを y/N で問う。F-03 では偽物の道具のテストで確かめ、実際に問いが出るのは F-04 から（「作業ディレクトリの外を読むときも問う」「F-04 に回す」を選ばなかった）
- **止めた回**: 「その回の全体を履歴に足さない」を選んだ（F-01 と同じ。「済んだ歩みまでは残す」を選ばなかった）。書く道具ができる F-04 で見直す
- **行番号**: 「付ける」を選んだ（`cat -n` の形。Claude Code の Read と同じ）
- 拒んだときにループを続けること（Claude Code は理由を添えずに拒むとその回を止める）・回数の上限を作らないこと（F-10）・`tasks/f-02-system-prompt/` を直さないことは、案のとおり
- 機能のディレクトリの名前は `f-03-tool-loop` にした
- 前のセッションは、仕様を commit し、実装の途中で終わった。途中の実装は stash に残っていた

### このセッション（branch `f-03-2`）

- 持ち主の指示: 「f-03 の実装を行え」。Claude Code は、`f-03` の承認済みの仕様と stash を見つけ、2つを問うた
- **仕様**: 持ち主の答え「承認済みの仕様で実装するので良いが、以前のブランチはprogress.mdを持たない状態で仕様を定めたものであることに注意せよ。progress.mdの内容や最新のCLAUDE.mdの内容に照らして、策定する必要のある内容があれば質問せよ」
  - Claude Code は照らし合わせて、新しく決めることは無いと判断し、そう伝えて進めた。見た点: main を学習用の簡素な実装に保つ（polish を足したときの要件）に対し、仕様の中身（行番号・`offset`/`limit`・長い行を切る・入力の検査・id を付ける）は Claude Code の Read を手本にした小さな処理で、学ぶ範囲に入る／F-02 が main でまだ読む段にあり、同じファイルを触るので衝突しうる（下の「main と衝突しそうな所」）／読む順の案内は、呼ばれる側と呼ぶ入口を一緒に挙げる（progress.md の申し送り）／branch の名前が `f-03-2` であること
  - 持ち主から異論は来ていない
- **stash**: 持ち主の答え「使わずに一から書く」。stash は apply せず、一から書いた（Claude Code は、問う前に stash の差分を一度見ている。分け方の考え（変換の層を別のファイルにする）は似たが、コードは写していない）

## 実装の全体像

### ファイル

| ファイル | 役目 | 主な名前 |
|---|---|---|
| `local_coding_agent/__main__.py` | 既定の道具の組と作業ディレクトリを `Session` に渡す | `main` |
| `local_coding_agent/loop/session.py` | ループと REPL が使うもの。`cli/repl.py` から移した | `Session`（`tools`・`cwd` を足した） |
| `local_coding_agent/cli/repl.py` | 1行ずつ受けて `run_turn` に渡し、履歴を持つ | `run`・`PROMPT` |
| `local_coding_agent/loop/turn.py` | ループ | `run_turn`・`CANCELLED` |
| `local_coding_agent/loop/model_call.py` | モデルを1回呼び、表示し、記録する。F-01 の `receive`・`response_record`・`summary` を `cli/repl.py` から移した | `call_model`・`receive`・`Outcome`・`response_record`・`summary` |
| `local_coding_agent/loop/tool_call.py` | 呼び出しを1つずつ処理し、表示し、記録する | `run_tool_calls`・`run_tool_call`・`execute`・`ToolRun`・`result_summary`・`tool_record` |
| `local_coding_agent/tools/tool.py` | 道具の形 | `Tool`・`ToolError`・`ToolInput`・`find_tool`・`resolve` |
| `local_coding_agent/tools/input_check.py` | 入力を JSON Schema の一部と照らす | `input_problem` |
| `local_coding_agent/tools/read_file.py` | `read_file` | `DEFINITION`・`run`・`TOOL`・`DEFAULT_LIMIT`・`MAX_LINE_LENGTH` |
| `local_coding_agent/tools/list_directory.py` | `list_directory` | `DEFINITION`・`run`・`TOOL` |
| `local_coding_agent/tools/default.py` | 既定の道具の組 | `DEFAULT_TOOLS` |
| `local_coding_agent/permissions/confirm.py` | 実行の前に確かめる | `confirm`・`PROMPT`・`YES`・`REFUSED` |
| `local_coding_agent/model/messages.py` | `tool_use`・`tool_result` の塊 | `ToolUseBlock`・`ToolResultBlock`・`assistant_message`・`tool_results`・`text_of` |
| `local_coding_agent/model/chat.py` | 道具の定義・応答の中の呼び出し | `ToolDefinition`・`ToolCall`・`ChatModel.build_request(system, messages, tools)` |
| `local_coding_agent/model/ollama_messages.py` | `/api/chat` の形への変換。`model/ollama.py` から `to_ollama_messages`・`chat_request_body` を移した | `chat_request_body`・`to_ollama_tools`・`to_ollama_messages`・`ERROR_PREFIX` |
| `local_coding_agent/model/ollama.py` | 接続と応答の読み取り（`tool_calls` を足した） | `read_stream`・`OllamaChat` |
| `local_coding_agent/context/system_prompt.py` | 既定の指示（できること・道具の使い方・ハーネスが入れる情報） | `DEFAULT_INSTRUCTIONS` |
| `tasks/f-03-tool-loop/project/` | 試すための小さなプロジェクト（README・設定・2400 行の記録） | |
| `tests/fakes.py` | `ScriptedModel.tools`・`ScriptedLines`（例外を投げる・問いの文を覚える）・`RecordingTrace.of_type`・`fake_tool`・`fake_session`・`START` を足した | |
| `tests/test_loop.py` | ループ（台本どおりに道具を呼ぶ偽物のモデルで） | |
| `tests/test_tools.py` | 道具・入力の照らし方・既定の組 | |
| `tests/test_ollama_tools.py` | 道具の変換と、応答の `tool_calls` の読み取り | |
| `tests/test_confirm.py` | 確かめる問い | |

依存の向き: `__main__` → `cli` → `loop` → `model`・`tools`・`permissions`・`trace`。`loop` は `cli` に依らない（そのために `Session` を `loop/` に移した）。`tools` は `model/chat.py` の `ToolDefinition` だけに依る。

### データの流れ

1. 起動: `main` が `Session(tools=DEFAULT_TOOLS, cwd=Path.cwd(), …)` を作り、`repl.run` を呼ぶ
2. `repl.run` が1行を受け、`run_turn(session, history, line, turn)` を呼ぶ
3. `run_turn` が `user_text(…, sent_at=now())` を下書き `messages` に足し、`step` を 1 から数えて `call_model` を呼ぶ
4. `call_model`: `tools = tuple(t.definition for t in session.tools)` → `model.build_request(system, messages, tools)` → 要求の件を記録（`step` 付き）→ `receive` が流れを読み、本文は表示、`ToolCall` は集める。終わったら id の無い呼び出しに `call_<turn>_<step>_<i>` を付けて `ToolUseBlock` にする → 応答の件を記録 → 数値の1行を表示
5. `OllamaChat.build_request` → `chat_request_body` → `to_ollama_messages`（呼び出しの id から名前を引く表を作り、発言ごとに変換）・`to_ollama_tools`
6. `run_turn`: 状態が `done` でなければ元の `history` を返す。`assistant_message(text, tool_uses)` を下書きに足す。呼び出しが無ければ下書きを返す
7. `run_tool_calls` → 呼び出しごとに `run_tool_call`: `[道具] …` を表示 → `execute`（探す → 照らす → 要れば `confirm` → `tool.run(input, cwd)`）→ `→ …` を表示 → 道具の件を記録
8. `tool_results(results)` を下書きに足して 4. へ
9. どこかで `KeyboardInterrupt` が上がれば（道具の実行・問いの途中）、`run_turn` の `except` が `CANCELLED` を表示して元の `history` を返す。応答の途中の Ctrl-C は `receive` が捕まえて `cancelled` にする（F-01 と同じ）

## 設計の選択と理由・捨てた案

- **ループ本体を `loop/turn.py` の30行に収めた**: 「チャットとエージェントの違いはループにある」を、`while True` の1か所で読めるようにするため。モデルを呼ぶ処理と道具を実行する処理は、別のファイルに出した
- **`Session` を `loop/session.py` へ移した**: ループが `cli/` に依らないようにするため。捨てた案: `cli/repl.py` に残し、ループが `cli` を import する（依存の向きが逆になる）
- **`receive`・`summary`・`response_record` を `cli/repl.py` から `loop/model_call.py` へ移した**: ループの1歩なので。中身で変えたのは、`ToolCall` を集めること・`step` と `tool_calls` の欄・最初の時間に呼び出しも数えること・id を付けることだけ。差分は大きく見えるが、ほぼ移動である
- **変換の層を `model/ollama_messages.py` に分けた**: `model/ollama.py` に全部入れると 200 行を超えるため。分け目は「送る形を作る」と「繋いで読む」
- **流れの中の呼び出し（`ToolCall`）と、履歴の塊（`ToolUseBlock`）を分けた**: API が id を付けないことがあるので、`ToolCall.id` は任意、`ToolUseBlock.id` は必須にした。id を付けるのは `loop/model_call.py`
- **id の形 `call_<回>_<歩み>_<順>`**: テストで決まった値になり、走行の記録で読める。セッションの中で重ならない。捨てた案: uuid（テストで値が決まらない）
- **入力の照らし方を1か所（`tools/input_check.py`）にした**: Messages API の文書の「入力の誤りも結果として返す」に倣い、ハーネスが定義と照らす。道具の関数は、照らした後の入力を `cast` で受ける。捨てた案: 道具ごとに型を見る（定義と検査が二重になる）
- **照らす順は 道具 → 入力 → 確かめる → 実行**: 入力が誤っているのに人に問わないため
- **確かめる時間は `seconds` に入れない**: 人の待ち時間を、道具の時間に混ぜないため。`seconds` は道具の関数だけを測る
- **`tool_name` は id で引く**: `ToolResultBlock` に名前を足すと、Messages API の形から外れるため
- **誤りの印「誤り: 」**: Ollama の `tool` の発言に `is_error` が無いため。既定の指示の「ハーネスが入れる情報」で説明する
- **結果の1行は、結果の文の行数**: 捨てた案: 道具ごとに要約の文を返させる（道具の形が増える）
- **`ValueError`（パスに NUL の字）を `ToolError` にした**: コードの見直しのエージェントの指摘。`read_text`・`iterdir` が `ValueError` を投げると、REPL が落ちていた。`UnicodeDecodeError` は `ValueError` の一種なので、その後に置いた。捨てた案: `execute` で全ての例外を捕まえる（ハーネスの誤りまで隠す）
- **試す材料の答えを `tasks/` の下に置かない**: モデルが材料と一緒に答えを読まないため。答えは `implementation.md` にある

## 実装前の仕様との違い

振る舞いは変えていない。仕様に書いていなかった細部は、`implementation.md` の「実装前の仕様との違い」の表のとおり（ファイルの分け方・id の付け方・`offset` が行数を超えるとき・空のディレクトリ・結果の1行の行数・読めない呼び出し・入力の照らし方・誤りの印の説明・既定の指示の「できること」・最初の時間・道具や問いの途中の Ctrl-C・パスとして使えない入力）。

## テストで確かめたこと・確かめていないこと

- 確かめた（102件）:
  - 変換: 道具の定義が `tools` になる・道具が無ければ `tools` が無い・`tool_use` が `tool_calls`（`index` は発言の中の順）・本文が空の呼び出し・`tool_result` が結果ごとの `tool` の発言（名前を id で引く・誤りの印）・結果の後の本文は `user` の発言
  - 読み取り: `id` のある・無い呼び出し・本文と呼び出しを全ての行から集める・`done` の行に載る呼び出し・読めない呼び出しは `ModelError`
  - 道具: 行番号・末尾の改行の有無・絶対パス・`offset` と `limit` と読み残しの知らせ・既定の 2000 行・長い行・空のファイル・`offset` が行数を超える・無い・ディレクトリ・UTF-8 でない・NUL の字／名前の順と `/`・相対パス・空・無い・ファイル・NUL の字
  - 入力の照らし方: 合う・定義に無い欄・必須の欄が無い・型（文字列・整数に文字列・真偽値・小数）・下限
  - 確かめる問い: `y`・`yes`・大文字・空白・それ以外・入力の終わり・問いの文・Ctrl-C を捕まえない
  - ループ: 結果を足してもう一度呼ぶ・毎回道具の定義を送る・呼び出しの無い応答で終わる・前の履歴を残す・1回の応答の複数の呼び出し（順と id）・3回回る・知らない道具・入力の誤り・`ToolError`・変更を伴う道具を許す／拒む（拒んでも続ける）・読むだけの道具は問わない・1回目と2回目の応答の途中・道具の途中・問いの途中の Ctrl-C と、2回目の誤りで、その回の全体を足さない・表示・記録の並びと欄・最初の時間に呼び出しを数える
  - 起動: 既定の道具の組と作業ディレクトリが `Session` に届く・既定の指示が既定の道具の名前と誤りの印を書いている
- Claude Code が手元で確かめた: 道具を `tasks/f-03-tool-loop/project/` に掛けた結果（`logs/inspection.log` の1回目は 2002 行・36038 字、`offset` 2001 からは 400 行・7220 字。`config/server.toml` は 8 行）
- 確かめていない:
  - 実物のモデルが道具を呼ぶか・何回呼ぶか・`offset` で続きを読むか（人が試す）
  - Ollama が呼び出しに `id` を付けるか（付けなくても動く）
  - 推論の文を捨てたまま、多段の呼び出しがうまくいくか
  - 実物の端末での Ctrl-C（道具の途中・問いの途中）と、問いでの Ctrl-D の後の振る舞い
  - 2つ目の問いで、文脈の長さが足りるか（結果の字数は上のとおり。トークン数は測っていない）

## 人が問いそうなことと答え

- **チャットとエージェントの違いはどこに見えるか**: `loop/turn.py` の `while True`。F-02 までは1回の依頼でモデルを1回呼んだ。F-03 は、モデルが道具を呼ぶ間、何度も呼ぶ。走行の記録では、1つの `turn` に `step` が 1, 2, … と並ぶ
- **モデルは道具を実行するのか**: しない。応答の `tool_calls` で「この道具をこの入力で呼びたい」と返すだけ。実行するのは `loop/tool_call.py` の `execute` が呼ぶ `tool.run` である
- **道具の定義は、どこからモデルに届くか**: 要求の `tools`。system prompt には入れない。Ollama がモデルごとの雛形で、道具の定義も1つの文に組み立てる。毎回の要求に入るので、毎回の入力のトークン数を増やす
- **なぜ道具の結果が利用者の発言なのか**: Messages API の形。Ollama の形では `role` が `tool` の発言になり、変換の層が変える
- **なぜ毎回、道具の定義と会話の全体を送るのか**: API が状態を持たないため（F-01 と同じ）。2回目の呼び出しの要求には、1回目の呼び出しと結果も入る
- **確かめる問いは、いつ出るか**: F-03 では出ない。既定の道具が読むだけで、`changes` の印を持たないため。仕組みはテストの偽物の道具で確かめた。問いが出るのは、書く道具ができる F-04 から
- **なぜ Ctrl-C でその回を全て捨てるのか**: 持ち主の選択（F-01 と同じ）。F-03 の道具は読むだけなので、捨てても失われるものは無い。F-04 で見直す
- **`call_1_2_0` は何か**: 1回目の依頼（turn）の、2回目のモデルの呼び出し（step）の、最初の（0 番目の）呼び出しに、ハーネスが付けた id。Ollama が id を付ければ、そちらを使う
- **入力の照らし方が要るのはなぜか**: モデルは、定義に合わない入力（欄の名前の誤り・型の誤り）で呼ぶことがある。合わない入力で道具を走らせず、どこが合わないかを結果として返すと、モデルが直して呼び直せる
- **`read_file` の既定の 2000 行と、1行の 2000 字は何から来たか**: 仕様で決めた値（Claude Code の Read に倣った）。結果の総量の上限は無い（下の「分かっている問題」）
- **`arguments` が文字列で来ることは無いか**: `/api/chat` は `arguments` を JSON の object で出す（Ollama の `api/types.go` の `ToolCallFunctionArguments` の `MarshalJSON`）。文字列で来るのは OpenAI 互換の口の形。object でなければ `ModelError` にして、その回を捨てる
- **なぜ表示で、道具を呼ぶだけの応答の前に空の行が出るのか**: 数値の1行の前に改行を出すのは F-01 から同じで、本文が空のときも出すため

## 分かっている問題・残したこと

- **推論の文を捨てている**: Ollama の文書の例は、道具を使うときに推論の文（`thinking`）も履歴に戻す。戻さないと、推論を学習したモデルの多段の呼び出しが弱くなるかもしれない（F-09）
- **結果の総量の上限が無い**: `read_file` は 2000 行 × 2000 字（最大約 400 万字）を1回で返しうる。圧縮した JS などでは、次の要求が文脈を超え、その回が誤りで捨てられる。同じファイルを読めば繰り返す。ファイルは全体を読み込む（コードの見直しのエージェントの指摘。仕様の範囲なので直していない）
- **ループの上限が無い**（F-10）。同じ呼び出しの繰り返しも止めない（F-17）
- **`done_reason` が `length` の応答**: 出力の長さの上限で切れた応答も、済んだ回として扱う。呼び出しの途中で切れると、空の発言が履歴に入りうる。数値の1行に `done_reason` は出ない（F-01 から同じ。見直しのエージェントの指摘）
- **パスの制限が無い**: `~` を解かない。`..` や作業ディレクトリの外の絶対パスも読める（要件の「素の状態では基本的に全て許可」。規則は F-06）
- **道具や問いの途中の Ctrl-C は、`tool` の件を書かない**: 記録は、呼び出しを返した `response` の件で途切れる
- **問いで Ctrl-D を押すと、改行が出ない**: 次の `→ 誤り: 利用者が実行を拒んだ` が、問いの行に続く
- **`ToolError`・`OSError`・`ValueError` 以外の例外は REPL を止める**（ハーネスの誤りを隠さないため）
- **大きなディレクトリの一覧に上限が無い**
- **整数の欄は `10.0` を受けない**: JSON Schema では整数だが、Python では `float` になるため。誤りの結果を読んで、モデルが直せる
- **呼び出しの id が重なったとき**: 名前を引く表は後のもので上書きする。id はセッションの中で重ならないので、今は起きない
- **判定のコマンドが無い**: 要件は「通ったかをコマンドの終了コードで判定する」だが、F-03 の問いの答えは文なので、人が答えと走行の記録を読む（仕様の試し方のとおり）
- **答えを読まれうる**: 作業ディレクトリはリポジトリの根なので、モデルが `docs/features/f-03-tool-loop/implementation.md` を読めば答えが見える
- **`tasks/f-02-system-prompt/short.md`**: 既定の指示と1行だけ違う写しだったが、F-03 で既定の指示を直したので、もう揃っていない（仕様のとおり直していない。F-02 の試し方は、F-03 を取り込む前の main で行う）

## worktree の運用で分かったこと

- **作るエージェントの起動は、Claude Code の auto mode の判定で止まった**: 配線を確かめるために `printf … | .venv/bin/python -m local_coding_agent --model qwen3.5:9b` を走らせようとしたら、「Create Unsafe Agents」の理由で拒まれた。回避せず、テスト（`tests/test_main.py`）で足りるとした。要件の「F-06 ができたら、Claude Code も実物のモデルで走らせてよい」を行うときは、この判定にも当たりうる。上流に上げてよい
- **web の文書が大きいと、要約されずにリポジトリの外へ保存される**: Claude Code の tools reference と permissions の文書は、WebFetch の結果が大きすぎて、リポジトリの外（Claude Code の設定のディレクトリの下）のファイルに保存された。CLAUDE.md の「リポジトリの外を読まない」に従い、そのファイルは読まなかった。そのため、拒んだときの Claude Code の振る舞いは、このセッションでは確かめ直していない（`spec.md` には前のセッションが確かめたとおりに書いてある。`implementation.md` には、確かめた範囲だけを書いた）
- `.venv/` は、前のセッションが作ったものがそのまま使えた（Python 3.14.4）。`poetry install` は走らせていない

## 読む順の案内（案）

F-01 で、呼ばれる側を挙げるときは、それを呼ぶ入口を一緒に挙げることになった。

1. `local_coding_agent/__main__.py` の `main` と `loop/session.py`: 道具の組と作業ディレクトリが、どこで `Session` に入るか。入口なので先に読む
2. `local_coding_agent/cli/repl.py` の `run`（`main` から呼ばれる）と `loop/turn.py` の `run_turn`（`run` から呼ばれる）: ループの全体。ここが F-03 の中心
3. `local_coding_agent/loop/model_call.py` の `call_model`（`run_turn` から呼ばれる）: F-01 の `receive` が、呼び出しを集めるようになったところ
4. `local_coding_agent/loop/tool_call.py` の `execute`（`run_turn` → `run_tool_calls` → `run_tool_call` から呼ばれる）と、そこから呼ぶ `tools/tool.py`・`tools/input_check.py`・`permissions/confirm.py`
5. `local_coding_agent/tools/read_file.py`・`tools/list_directory.py`・`tools/default.py`（組は `main` が渡し、`execute` が `tool.run` で呼ぶ）
6. `local_coding_agent/model/messages.py` と `model/chat.py`: 塊と、流れの中の呼び出し
7. `local_coding_agent/model/ollama_messages.py`（`OllamaChat.build_request` から呼ばれる）と `model/ollama.py` の `read_stream`（`OllamaChat.stream` から呼ばれる）: 手元の形と送る形の違いが見えるところ
8. `local_coding_agent/context/system_prompt.py`: 既定の指示の直し
9. `tests/test_loop.py` → `tests/test_tools.py` → `tests/test_ollama_tools.py` → `tests/test_confirm.py`
10. `tasks/f-03-tool-loop/project/` と、試した後の走行の記録（`step` と `tool` の件）

## main と衝突しそうな所

F-03 は、F-02 のファイル（`model/messages.py`・`model/chat.py`・`model/ollama.py`・`cli/repl.py`・`__main__.py`・`context/system_prompt.py`・`tests/fakes.py`・`tests/test_ollama.py`・`tests/test_repl.py`・`tests/test_main.py`・`tests/test_context.py`・`README.md`）を直した。ほかに `docs/features.md`・`docs/how-coding-agents-work.md`・`docs/technologies/ollama.md` を直した。

- 特に、`cli/repl.py` の `receive`・`summary`・`response_record` と `Session` は `loop/` へ、`model/ollama.py` の `to_ollama_messages`・`chat_request_body` は `model/ollama_messages.py` へ移した。main で F-02 の確認の間にこれらを直したら、取り込むときに、直しを移した先へ写す
- `context/system_prompt.py` の `DEFAULT_INSTRUCTIONS` を main で直したら、F-03 の直し（できること・道具の使い方・ハーネスが入れる情報）と合わせる
- branch を作った時点（`225acce`）より後の main の変更は、このセッションからは見えない

## 問いと答えの記録

main 側のセッションが、人から来た問いと答え・直したことを足す。
