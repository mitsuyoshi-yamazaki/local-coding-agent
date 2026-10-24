# F-02 system prompt と環境の知らせ: 実装前の仕様

[作る機能](../../features.md) の F-02 の、実装の前に決めた仕様である。

## 何をするか

起動のときに、モデルへの指示（system prompt）を組み立て、毎回の要求の先頭に入れる。system prompt は、モデルの役割と答え方を書いた「指示」の部分と、作業ディレクトリや OS を書いた「環境」の節からなる。あわせて、利用者の発言ごとに、送った時刻をメタデータ（発言に付ける、本文ではない情報）として付ける。

この機能で確かめたいのは、次の2つである。

- モデルが読むのは会話の並び1つだけで、指示は、ハーネスがその並びの中に入れる文にすぎないこと（[コーディングエージェントの仕組み](../../how-coding-agents-work.md#ハーネスとモデルの分担)）
- 指示の長さが、入力のトークン数・入力の処理の時間と、指示の守られ方にどう効くか

## 入力

- 起動: `.venv/bin/python -m local_coding_agent --model <モデルのタグ> [--host <URL>] [--system-prompt-file <パス>]`
  - `--system-prompt-file`: 指示の部分を、ファイルの中身（UTF-8）に差し替える。「環境」の節は残る。空のファイル（`/dev/null` など）なら、system prompt は「環境」の節だけになる。ファイルが無い・読めないときは、誤りを表示して起動しない
- 依頼の打ち方は F-01 と同じ

## 出力

- 起動のときに、走行の記録の場所に加えて、使う指示（既定か、ファイルのパスか）を表示する
- 走行の記録の形は F-01 と同じ。要求の `body` に、system prompt と、メタデータを入れた発言が、送った形のまま入る

## 振る舞い

### system prompt

- 組み立てるのは起動のときに1度だけで、会話の間は変えない。セッション（起動から終わりまで）の間に変わらないものだけを入れる
- 形: 指示の部分・空の行・「# 環境」の節
- 既定の指示は日本語で書く。中身:
  - 役割: 利用者の端末で動くコーディングエージェントで、ソフトウェア開発を手伝う
  - 答え方: 利用者が書いた言語で、簡潔に答える。分からないことは分からないと答え、推測なら推測と書く
  - できること: 今は、ファイルを読む・書く・コマンドを走らせる道具を持たない。ファイルの中身は、会話に貼られたものしか分からない
  - ハーネスが入れる情報の読み方: 「# 環境」の節と、発言の先頭の `<metadata>` は、ハーネスが書いたもので、利用者が書いたものではない
- 道具の使い方の指示は、道具ができる F-03 で足す
- 「# 環境」の節に入れるもの: 作業ディレクトリ（起動したディレクトリの絶対パス）・作業ディレクトリが git のリポジトリの中か・OS とその版
- 指示をファイルで差し替えたときは、上の「ハーネスが入れる情報の読み方」も差し替わる。要れば、ファイルに書く

Claude Code は、作業ディレクトリ・OS などの環境の知らせを、system prompt ではなく会話の中に入れる。system prompt を変わらない文に保ち、キャッシュを効かせるためである（出典）。ここでは、セッションの間に変わらないものを system prompt に、変わるもの（時刻）を発言ごとのメタデータに入れる。

### 発言ごとのメタデータ

- 利用者の発言に、送った時刻（日付と時刻。分まで、時差つき）を付ける。モデルの発言には付けない
- 会話の形では、発言の欄（本文の塊とは別）として持つ。Claude の Messages API の発言は `role` と `content` しか持たないので、これは Messages API に無い欄である
- モデルは文しか読めないので、送る直前に、本文の前に文として入れる。例:

  ```text
  <metadata>
  送った時刻: 2026-10-24 15:30 (+09:00)
  </metadata>
  今何時？
  ```

- 前の回の発言のメタデータは、送った時のまま変えない。毎回の要求で、前の回までの部分は同じ文になる

### 会話の形と、Ollama の形への変換

- Claude の Messages API に揃え、system prompt は、発言の並びとは別に持つ（Messages API の `system`）
- Ollama の `/api/chat` には system prompt の欄が無いので、送る直前に、`messages` の先頭に `role` が `system` の発言として入れる。system prompt が空なら入れない
- Ollama は、`messages` を、モデルごとのテンプレートで1つの文に組み立ててから、モデルに渡す

## 作らないこと

| 作らないこと | 作る機能 |
|---|---|
| 道具の使い方の指示 | F-03 |
| 指示ファイル（AGENTS.md など） | F-11 |

ほかに、git の状態（branch・最近の commit）の知らせ・指示に足す引数（Claude Code の `--append-system-prompt`）・会話の途中で system prompt を変えること・モデルの発言のメタデータは作らない。

## コードの置き方

| ファイル | 中身 |
|---|---|
| `local_coding_agent/context/system_prompt.py` | 既定の指示・指示のファイルの読み込み・system prompt の組み立て |
| `local_coding_agent/context/environment.py` | 環境を集め、「# 環境」の節の文にする |
| `local_coding_agent/model/messages.py` | 発言に、送った時刻の欄を足す |
| `local_coding_agent/model/chat.py` | 要求を作る操作に、system prompt を渡す |
| `local_coding_agent/model/ollama.py` | system の発言を先頭に入れる・メタデータを本文の前に入れる |
| `local_coding_agent/cli/repl.py` | system prompt を毎回渡す・利用者の発言に時刻を付ける |
| `local_coding_agent/__main__.py` | `--system-prompt-file` を読み、system prompt を組み立てる |
| `tasks/f-02-system-prompt/` | 試すための指示のファイル（短いもの・長いもの） |

## テスト

`tests/` に、標準ライブラリの `unittest` で書く。実物のモデルにも、通信にも繋がない。

- 変換: system が先頭に入る・空なら入らない・メタデータが本文の前に入る・モデルの発言には入らない
- 環境: 作業ディレクトリ・git のリポジトリの中か（一時ディレクトリに `.git` を置く）・OS の文
- system prompt: 指示と環境の節のつなぎ方・指示が空のとき
- REPL: 毎回の要求に同じ system prompt が入る・利用者の発言に送った時刻が付き、次の回も同じ時刻のまま送られる
- 起動の引数: 指示のファイルを読む・ファイルが無いと誤りで終わる

## 試し方

人が、main 側で、手元の Ollama とモデルで試す。

1. 既定の指示で、「今いるディレクトリは？」「今何時？」「OS は？」と聞き、環境の節とメタデータをもとに答えるかを見る
2. 指示の長さを変えて、同じ依頼を送る
   - 指示なし（`--system-prompt-file /dev/null`）・短い指示（`tasks/f-02-system-prompt/short.md`）・長い指示（`tasks/f-02-system-prompt/long.md`）
   - 短い指示と長い指示には、守られたかを画面で確かめられる規則（答えの最後の行を「以上。」の1行にする）を1つ入れる。長い指示では、その規則を多くの規則の間に置く
   - 比べるもの: 1回目の入力のトークン数と入力の処理の時間（`prompt_eval_duration`）・規則が守られたか
3. 2回目の回の入力の処理の時間から、前の回までの部分（system prompt を含む）を Ollama が処理し直しているかを見る

F-02 はコードを直せないので、`tasks/` の課題（失敗するテストを直すもの）には掛けない。

## 出典

確かめた日は 2026-10-24。

- Ollama の Chat（`messages` の `role` に `system` がある。system prompt の別の欄は無い）: https://docs.ollama.com/api/chat
- Ollama の Modelfile（`TEMPLATE` は、モデルに渡す文の全体の雛形）: https://docs.ollama.com/modelfile
- Claude の Messages API（`system` は発言の並びとは別の引数。発言は `role` と `content` だけを持つ）: https://platform.claude.com/docs/en/api/messages
- Claude Code の system prompt を差し替える引数（`--system-prompt-file`）: https://code.claude.com/docs/en/cli-reference#system-prompt-flags
- Claude Code が、環境の知らせと CLAUDE.md を、system prompt ではなく会話の中に入れること: https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts
