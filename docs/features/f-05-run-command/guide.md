# F-05 コマンドの実行と、結果を読んで直すループ: 確かめる案内

F-05 を試し、コードを読むための案内である。動作の確かめ方・読む順・既存の実装（F-04 まで）からの変わりを書く。

main に取り込んだ後のコードと差分（基点 `880a336` から、取り込んだ commit `8eb7ad6` まで）と、[実装前の仕様](spec.md)・[実装した仕様と仕組み](implementation.md)・[引き継ぎ](handoff.md) から書いた。行の番号は、この案内を最後に直した commit のコードのものである（`git log -1 -- docs/features/f-05-run-command/guide.md` で分かる）。

## 動作の確かめ方

### 準備

- モデルは `qwen3.5:9b`（F-04 と同じ）。`pyproject.toml`・`poetry.lock` は変わっていないので、`poetry install` は要らない
- 文脈の長さを `ollama ps` で確かめる（[README](../../../README.md) の「Ollama を設定する」）。テストの失敗の出力（最大 10,000 字）が道具の結果に入るので、F-04 より入力が長くなる

### 起動

リポジトリの根で、試す材料を写し、写しの中で起動する（`duration` の例。`words` も同じ）。

```sh
cp -R tasks/f-05-run-command/duration .tmp/f-05-duration
cd .tmp/f-05-duration
PYTHONPATH=../.. ../../.venv/bin/python -m local_coding_agent --model qwen3.5:9b
```

- 試し直すときは、前の写しを消してから写す（`cp -R` は、写し先のディレクトリがあると、その中に写す）
- 走行の記録は、写しの中の `traces/` に書かれる

### 課題

依頼の文は、どちらも `テストを走らせて、通らないものを直せ` である。

| 課題 | 期待する答え | 画面で見る所 | 判定（リポジトリの根で） |
|---|---|---|---|
| `duration` | 誤りの2か所を直す: `parse_duration` が、読んだ数字を空に戻さない・`format_duration` が、残りの秒数を `rest % 60` にしている | `$ python3 -m unittest` の後の結果が、`→ 終了コード: 1・N 行` から `→ 終了コード: 0・N 行` に変わるか。直した後に走らせ直すか。通ったことを確かめてから答えるか | `.venv/bin/python tasks/f-05-run-command/judge.py .tmp/f-05-duration` |
| `words` | `start = end` を `start = end + 1` にする | `→ 時間切れ: 120 秒で止めた・N 行` を読み、終わらない所を見つけるか。`timeout` を短くする・`-v` を付けるか | `.venv/bin/python tasks/f-05-run-command/judge.py .tmp/f-05-words` |

- `words` では、モデルが `timeout` を渡さないと、始めの1回で 120 秒、画面が止まったように見える。仕様どおりである
- 判定は、終了コードが 0 なら通った。写したばかりの状態では、どちらも通らない
- 走行の記録では、`type` が `tool` で `name` が `run_command` の件を順に見る。`input.command`（何を走らせたか）・`result` の1行目（終了コードか時間切れか）・`confirmed`・`seconds`・`preview`（`$ …`）
- ほかに、問いに `n` と答えて拒んだときと、コマンドの途中で Ctrl-C を押したときに、モデルがどうするかを見る

### テストで確かめておらず、実物で見てほしいこと

- モデルが、直した後にテストを走らせるか・失敗の出力から直す所を見つけるか・時間切れの結果をどう読むか
- 実物の端末での Ctrl-C で、コマンドと、それが起こしたプロセスが止まり、その回が止まるか（テストは SIGALRM の信号で Ctrl-C を真似た）
- 実物の端末での表示（呼び出しの1行 `[道具] run_command {…}` の後に、下見の `$ …` が出る）

### テストを走らせる

- `.venv/bin/python -m unittest tests.test_run_command`: F-05 の22件。本物の `/bin/sh` で走らせるので、約 6 秒かかる（実測）
- `.venv/bin/python -m unittest`: 全て（193件）

## 読む順

1. [default.py](../../../local_coding_agent/tools/default.py#L12) の `DEFAULT_TOOLS`
   - 入口: [__main__.py](../../../local_coding_agent/__main__.py#L54) の `main` が、[L71](../../../local_coding_agent/__main__.py#L71) で `Session` に渡す
   - 分かること: 道具が1つ増えた。約20行
2. [run_command.py](../../../local_coding_agent/tools/run_command.py) の [`DEFINITION`](../../../local_coding_agent/tools/run_command.py#L21)・[`run`](../../../local_coding_agent/tools/run_command.py#L50)・[`preview`](../../../local_coding_agent/tools/run_command.py#L64)・[`_command`](../../../local_coding_agent/tools/run_command.py#L84)・[`_status`](../../../local_coding_agent/tools/run_command.py#L94)・[`_output`](../../../local_coding_agent/tools/run_command.py#L100)・[`clip`](../../../local_coding_agent/tools/run_command.py#L75)
   - 入口: [tool_call.py](../../../local_coding_agent/loop/tool_call.py#L75) の `execute` が、[L87](../../../local_coding_agent/loop/tool_call.py#L87) で下見を作り、問いの後に [`_run`](../../../local_coding_agent/loop/tool_call.py#L98) で `run` を呼ぶ。`execute` は F-04 から変わっていない
   - 分かること: 道具の入力と、結果の文の形（1行目が終了コードか時間切れ、2行目からが出力）。約110行
3. [process.py](../../../local_coding_agent/tools/process.py) の [`run_shell`](../../../local_coding_agent/tools/process.py#L30)・[`_drain`](../../../local_coding_agent/tools/process.py#L57)・[`_stop_group`](../../../local_coding_agent/tools/process.py#L72)
   - 入口: `run_command.run`（[L56](../../../local_coding_agent/tools/run_command.py#L56)）
   - 分かること: コマンドを新しいセッションで走らせ、時間切れ・Ctrl-C・終わったときに、プロセスのグループごと SIGKILL で止める。F-05 の中心である。約80行
   - [L76](../../../local_coding_agent/tools/process.py#L76) の `except ProcessLookupError, PermissionError:` は、括弧を付けない Python 3.14 の書き方である
4. [tool.py](../../../local_coding_agent/tools/tool.py#L37) の `Tool.summary` と、[tool_call.py](../../../local_coding_agent/loop/tool_call.py#L63) の `run_tool_call` → [`result_summary`](../../../local_coding_agent/loop/tool_call.py#L122)
   - 入口: [loop/tool_call.py](../../../local_coding_agent/loop/tool_call.py#L44) の `run_tool_calls`（F-04 から変わっていない）
   - 分かること: 画面の結果の1行に終了コードを出す所。`loop/` は `run_command` の結果の文の形を知らずに済む。約20行
5. [input_check.py](../../../local_coding_agent/tools/input_check.py#L48) の `_property_problem` と [`_is_number`](../../../local_coding_agent/tools/input_check.py#L68)
   - 入口: `execute` の [L81](../../../local_coding_agent/loop/tool_call.py#L81) の `input_problem`
   - 分かること: `timeout` の上限 600 を照らす。約25行
6. [system_prompt.py](../../../local_coding_agent/context/system_prompt.py#L18-L49) の `DEFAULT_INSTRUCTIONS` の「できること」「道具の使い方」「ハーネスが入れる情報」
   - 入口: [__main__.py](../../../local_coding_agent/__main__.py#L57) の `read_instructions`
   - 分かること: モデルに、直した後にテストを走らせるよう促す指示。約30行
7. [test_run_command.py](../../../tests/test_run_command.py) の [`RunShellTest`](../../../tests/test_run_command.py#L32) → [`RunCommandTest`](../../../tests/test_run_command.py#L95) → [`CommandInLoopTest`](../../../tests/test_run_command.py#L158)
   - 分かること: プロセス・道具・ループの順に確かめたこと。約190行
8. [tasks/f-05-run-command/README.md](../../../tasks/f-05-run-command/README.md) → `duration/` → `words/` → [judge.py](../../../tasks/f-05-run-command/judge.py)
   - 分かること: 試す材料の誤りと、判定の仕方

## 既存の実装からの変わり

### 足したファイル・直したファイル

- 足した:
  - [process.py](../../../local_coding_agent/tools/process.py): 子のプロセスで走らせ、止める。標準ライブラリだけに依る
  - [run_command.py](../../../local_coding_agent/tools/run_command.py): 道具 `run_command`
  - [test_run_command.py](../../../tests/test_run_command.py)
  - `tasks/f-05-run-command/`（`duration/`・`words/`・`judge.py`・README）
- 直した（移した関数は無い）:
  - [tool.py](../../../local_coding_agent/tools/tool.py): 道具の形に `summary` の欄を足した
  - [tool_call.py](../../../local_coding_agent/loop/tool_call.py): `run_tool_call` が道具を探し直し、`result_summary` に道具を渡す
  - [input_check.py](../../../local_coding_agent/tools/input_check.py): 下限の判定 `_below` を `_is_number`（`TypeIs`）に替え、上限（`maximum`）を足した
  - [default.py](../../../local_coding_agent/tools/default.py)・[system_prompt.py](../../../local_coding_agent/context/system_prompt.py)・`tests/test_tools.py`

### 振る舞いの変わり

- 利用者から見て:
  - モデルが `run_command` を呼ぶと、`$ <コマンド>` を表示して問う。結果の1行は `→ 終了コード: N・M 行` か `→ 時間切れ: <秒> 秒で止めた・M 行`
  - Ctrl-C で、コマンドと、それが起こしたプロセスも止まる
  - 終了コードが 0 でないときと時間切れは、誤りの結果（`is_error`）にしない（持ち主の選択）
- モデルへ送る要求: 道具の定義が5つになり、既定の指示に `run_command` の使い方が加わったので、入力のトークンが増える
- 走行の記録: 欄は F-04 と同じ。`run_command` の件では、`preview` が `$ …`、`result` の1行目が終了コードか時間切れになる

### 依存の向き

`tools/run_command.py` → `tools/process.py`・`tools/tool.py`・`model/chat.py`（`ToolDefinition`）。`loop/` の依存の向きは変わらない。依存のパッケージは足していない。

### 文書・試す材料・設定

- README: 「できること」の表に F-05 の行を足した（「コマンドを走らせる道具は、まだ無い」の1行を除いた）。使い方に「コマンド」と「コマンドを試す材料」の項を足し、「道具」「実行の前の問い」「Ctrl-C」の項を直した
- [コーディングエージェントの仕組み](../../how-coding-agents-work.md): 「コマンドの実行」の節を足した
- [作る機能](../../features.md): F-05 の行を足した
- 設定（`.claude/`・`pyproject.toml`）は変わらない

### 取り込みで branch から変えた所

README の使い方の項の並びだけである。main の「推論の文」の項を先に、F-05 の4項を後に置いた。コードは変えていない。
