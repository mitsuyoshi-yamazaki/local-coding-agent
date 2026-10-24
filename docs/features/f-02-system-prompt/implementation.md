# F-02 system prompt と環境の知らせ: 実装した仕様と仕組み

[実装前の仕様](spec.md) に対して、実際に実装した仕様と、その仕組みである。

## 使い方

```sh
.venv/bin/python -m local_coding_agent --model qwen3.5:9b
.venv/bin/python -m local_coding_agent --model qwen3.5:9b --system-prompt-file tasks/f-02-system-prompt/long.md
```

起動すると、走行の記録の場所と、使う指示（`既定` か、ファイルのパス）を表示する。

```text
走行の記録: traces/20261024-153012.jsonl
指示: 既定
>
```

`--system-prompt-file` は、指示の部分だけを、ファイルの中身（UTF-8）に差し替える。「# 環境」の節は残る。空のファイル（`/dev/null` など）を渡すと、system prompt は「# 環境」の節だけになる。ファイルが無い・読めないときは、誤りを表示して、終了コード 2 で終わる。

## 仕組み

### モデルに届く文

1回目の依頼で Ollama に送る `messages` は、次の形になる（作業ディレクトリと時刻は例）。

```json
[
  {"role": "system",
   "content": "あなたは、利用者の端末で動くコーディングエージェントである。…（指示の部分）\n\n# 環境\n\n- 作業ディレクトリ: /path/to/project\n- 作業ディレクトリは git のリポジトリの中か: はい\n- OS: macOS 15.6（Darwin 24.6.0）"},
  {"role": "user",
   "content": "<metadata>\n送った時刻: 2026-10-24 15:30 (+09:00)\n</metadata>\n今何時？"}
]
```

Ollama は、この `messages` を、モデルごとの雛形（Modelfile の `TEMPLATE`）で1つの文に組み立ててから、モデルに渡す。モデルが読むのは、その1つの文である。system prompt は、その文の先頭に置かれた指示であり、利用者の発言の前のメタデータも、発言の文の一部として読まれる。

ハーネスが指示を入れる場所は2つある。

| 場所 | 入れるもの | いつ作るか |
|---|---|---|
| 先頭の system の発言 | 指示の部分と「# 環境」の節。セッション（起動から終わりまで）の間に変わらないもの | 起動のときに1度 |
| 利用者の発言の先頭 | 送った時刻（メタデータ）。発言ごとに変わるもの | 発言を送るとき |

どちらも毎回の要求に入る。前の回の発言のメタデータは送った時のまま変えないので、毎回の要求の、前の回までの部分は同じ文になる。

Claude Code は、作業ディレクトリ・OS などの環境の知らせを、system prompt ではなく会話の中に入れる。ここでは、セッションの間に変わらないものを system prompt に、変わるものを発言ごとのメタデータに入れる。

### system prompt の組み立て

`__main__.py` が、起動のときに次の順で組み立て、`cli/repl.py` の `Session.system` に渡す。REPL は、毎回の要求に同じ文を渡す。

1. `context/system_prompt.py` の `read_instructions`: 指示の部分を決める。`--system-prompt-file` が無ければ既定の文（`DEFAULT_INSTRUCTIONS`）、あればファイルの中身
2. `context/environment.py` の `collect_environment`: 環境を集める
3. `context/environment.py` の `environment_section`: 環境を「# 環境」の節の文にする
4. `context/system_prompt.py` の `build_system_prompt`: 指示の部分の前後の空白を除き、空の行を挟んで環境の節をつなぐ。指示が空なら、環境の節だけにする

既定の指示（日本語）は、次の節からなる。

| 節 | 中身 |
|---|---|
| （始め） | 役割: 利用者の端末で動くコーディングエージェントで、ソフトウェア開発を手伝う |
| 答え方 | 利用者が書いた言語で、簡潔に答える。分からないことは分からないと答え、推測なら推測と書く |
| できること | ファイルを読む・書く・コマンドを走らせる道具を持たない。会話に貼られたもの以外のファイルの中身を、読んだように答えない |
| ハーネスが入れる情報 | 「# 環境」の節と、発言の先頭の `<metadata>` は、ハーネスが書いたもので、利用者が書いたものではない |

指示をファイルで差し替えると、「ハーネスが入れる情報」の節も差し替わる。モデルに `<metadata>` の意味を伝えたいときは、ファイルにも書く。

### 環境の節

| 項目 | 集め方 |
|---|---|
| 作業ディレクトリ | 起動したディレクトリの絶対パス（`Path.cwd()`） |
| git のリポジトリの中か | 作業ディレクトリか、その上のどれかに `.git` があれば「はい」。git worktree では `.git` がファイルなので、ディレクトリかどうかは見ない。`git` のコマンドは走らせない |
| OS | `platform` の値。macOS では「macOS <版>（Darwin <版>）」、ほかの OS では「<名前> <版>」 |

### 発言ごとのメタデータ

- `model/messages.py` の `Message` は、本文の塊の並び（`content`）のほかに、送った時刻の欄（`sent_at`）を持つ。Claude の Messages API の発言も、Ollama の `/api/chat` の発言も、メタデータの欄を持たない。`sent_at` は、このリポジトリの会話の形だけにある欄である
- `cli/repl.py` の `run_turn` が、利用者の発言を作るときに、`Session.now`（この機械の時差つきの今の時刻）を入れる。モデルの発言には入れない
- `model/ollama.py` が送る直前に、`model/messages.py` の `metadata_text` で、`sent_at` を `<metadata>` の文にし、本文の前に入れる。時刻は分まで、時差を添える

### 会話の形と、Ollama の形への変換

| | このリポジトリの会話の形 | Ollama の `/api/chat` | Claude の Messages API |
|---|---|---|---|
| system prompt | 発言の並びとは別の文字列（`ChatModel.build_request` の引数 `system`） | `messages` の先頭の、`role` が `system` の発言 | 発言の並びとは別の引数 `system` |
| 発言の本文 | 塊（`TextBlock`）の並び | 1つの文字列（`content`） | 塊の並び |
| 発言のメタデータ | 欄 `sent_at` | 欄が無い。`content` の先頭に文として入れる | 欄が無い |

`model/ollama.py` の `to_ollama_messages` が、system prompt が空でなければ先頭に system の発言を置き、発言ごとに、メタデータの文と本文の塊をつないで1つの文字列にする。

## 試すための指示のファイル

`tasks/f-02-system-prompt/` に置く。指示の長さによる違いを見るためのもので、`--system-prompt-file` で渡す。

| ファイル | 字数 | 中身 |
|---|---|---|
| `short.md` | 397 | 既定の指示に、規則「どの答えも、最後の行を「以上。」の1行で終える」を「答え方」の節の末尾に足したもの |
| `long.md` | 1569 | 既定の指示の各節に、依頼の受け方・コードの書き方・説明の仕方・テスト・git の規則を足したもの。同じ規則を、中ほどの「説明の仕方」の節の、他の規則の間に置く |

規則が守られたかは、答えの最後の行を見れば分かる。指示を送らない場合と比べるときは、`--system-prompt-file /dev/null` を渡す（環境の節だけが送られる）。

## 実装前の仕様との違い

仕様の振る舞いは変えていない。仕様に書いていなかった細部は次のとおり。

| 点 | 実装 |
|---|---|
| 指示のファイルを読めないとき | 標準エラー出力に「指示のファイルを読めない（<パス>）: <理由>」を出し、終了コード 2 で終わる。UTF-8 として読めないときも同じ。走行の記録は作らない |
| 指示の部分の前後の空白 | 除いてから、環境の節とつなぐ |
| git のリポジトリの中かの判じ方 | `.git` が在るかだけを見る（`git` のコマンドを走らせない） |
| 時差を持たない時刻 | メタデータの時刻に時差を添えない（REPL は常に時差つきの時刻を入れる） |

## ファイル

| ファイル | 行数の目安 | 中身 |
|---|---|---|
| `local_coding_agent/context/system_prompt.py` | 50 | 既定の指示・指示のファイルの読み込み・system prompt の組み立て |
| `local_coding_agent/context/environment.py` | 50 | 環境を集め、「# 環境」の節の文にする |
| `local_coding_agent/model/messages.py` | 60 | 発言の欄 `sent_at` と、メタデータの文（`metadata_text`） |
| `local_coding_agent/model/chat.py` | 60 | `build_request` が system prompt を受ける |
| `local_coding_agent/model/ollama.py` | 140 | system の発言を先頭に置く・メタデータを本文の前に入れる |
| `local_coding_agent/cli/repl.py` | 160 | `Session` に `system` と `now` を足す。利用者の発言に時刻を入れる |
| `local_coding_agent/__main__.py` | 80 | `--system-prompt-file` を読み、system prompt を組み立てる |
| `tasks/f-02-system-prompt/` | | 試すための指示のファイル（`short.md`・`long.md`） |
| `tests/` | 600 | 偽物と、変換・メタデータ・環境・system prompt・起動・REPL・記録のテスト |

## 出典

確かめた日は 2026-10-24。

- Ollama の Chat（`messages` の発言の欄は `role`・`content`・`images`・`tool_calls` で、メタデータの欄は無い。`role` に `system` がある）: https://docs.ollama.com/api/chat
- Ollama の Modelfile（`TEMPLATE` は、モデルに渡す文の全体の雛形。`SYSTEM` は雛形に入れる system の発言）: https://docs.ollama.com/modelfile
- Claude の Messages API（`system` は発言の並びとは別の引数。発言は `role` と `content` だけを持つ）: https://platform.claude.com/docs/en/api/messages
- Claude Code が、環境の知らせを system prompt ではなく会話の中に入れること: https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts
