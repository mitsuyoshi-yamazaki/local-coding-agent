# コーディングエージェントの仕組み

コーディングエージェントは、LLM（大規模言語モデル）に、ファイルを読む・書く・コマンドを走らせるといった操作をさせるプログラムである。Claude Code はその1つで、このリポジトリはそれを手本にする。ここでは、作るものの全体像を説明する。

## LLM は何をするか

- LLM は、入力の文の続きを、トークン（語や語の一部などの断片）を1つずつ選んで足していくことで生成する
- LLM の API は会話の状態を持たない。2回目の質問をするときは、1回目の質問と答えを含めた**履歴の全体**を毎回送る。履歴を持っているのは、API を呼ぶ側のプログラムである
- モデルが一度に読める量には上限がある（文脈窓。トークン数で決まる）。履歴が長くなれば、いつか入りきらなくなる

## 指示（system prompt）

- 呼ぶ側のプログラムは、会話の先頭に、モデルへの指示を置く。これを system prompt と呼ぶ。役割・答え方・道具の使い方・守る規則などを書く
- system prompt も、会話のほかの部分と同じく文である。手元でモデルを動かす Ollama は、指示と発言の並びを、モデルごとの雛形（テンプレート）で1つの文に組み立ててから、モデルに渡す。モデルは、指示を、入力の文の先頭の部分として読む
- 指示は毎回の要求に入る。長い指示は、毎回の入力のトークン数を増やす
- 指示の入り口は system prompt だけではない。Claude Code は、作業ディレクトリ・OS などの環境の知らせと、指示ファイル（CLAUDE.md）を、system prompt ではなく会話の中に入れる。system prompt を変わらない文に保ち、キャッシュ（前の要求で処理した部分の使い回し）を効かせるためである

## 道具の呼び出し

LLM が出せるのは文だけで、自分ではファイルを読めず、コマンドも走らせられない。そこで、次の往復を行う。これを道具の呼び出し（tool use / function calling）と呼ぶ。

1. 呼ぶ側のプログラムが、道具の名前・説明・入力の形（JSON Schema）をモデルに渡す。例: `read_file`（入力は `path`）
2. モデルは、道具を使いたいときに、本文の代わりに「`read_file` を `{"path": "src/main.py"}` で呼びたい」という構造化した出力を返す
3. **プログラムが**その道具を実行し、結果（ファイルの中身）を履歴に足して、もう一度モデルを呼ぶ

モデルは道具を実行しない。実行するのは、いつも呼ぶ側のプログラムである。

## エージェントのループ

エージェントは、モデルが道具を呼ぶ間、「モデルを呼ぶ → 道具を実行する → 結果を履歴に足す」を繰り返す。モデルが道具を呼ばずに本文だけを返したら、ループを終えて人に答えを見せる。

1. 人の依頼を履歴に足し、モデルを呼ぶ
2. 応答が道具の呼び出しなら、実行してよいかを確かめ、道具を実行し、結果を履歴に足して 1 のモデルの呼び出しへ戻る
3. 応答が本文だけなら、人に見せて終わる

コードを直すときは、たとえば「テストを走らせる → 失敗の出力を読む → ファイルを編集する → もう一度テストを走らせる」が、このループの中で起きる。

## ハーネスとモデルの分担

モデルの周りで、ループ・道具の実行・履歴の管理・許可の判定を受け持つプログラムを、ハーネス（harness）と呼ぶ。エージェントは、モデルとハーネスの組である。

| 担い手 | 受け持つもの |
|---|---|
| モデル | どの道具をどの引数で呼ぶか。編集で書き換える文字列。コードと説明の本文。答えの前の推論 |
| ハーネス | 指示（system prompt）と道具の定義の組み立て。履歴の保持と毎回の送信。道具の実行。実行してよいかの判定。ループの継続と終了。履歴が長くなったときの要約 |

Claude Code の機能の多くはハーネスの側にある。だから、モデルを自分で作らなくても、ハーネスを書けば仕組みの大半を確かめられる。このリポジトリでは、モデルにはローカル LLM を使い、ハーネスを自分で書く。

## 出典

確かめた日は、断りが無ければ 2026-10-22。

- How tool use works（Anthropic）: https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works
- Building effective agents（Anthropic）: https://www.anthropic.com/engineering/building-effective-agents
- How Claude Code works: https://code.claude.com/docs/en/how-claude-code-works
- How the agent loop works（Claude Agent SDK）: https://code.claude.com/docs/en/agent-sdk/agent-loop
- Messages API（`system` は発言の並びとは別の引数。2026-10-24）: https://platform.claude.com/docs/en/api/messages
- Modifying system prompts（Claude Code が環境の知らせと CLAUDE.md を会話の中に入れること。2026-10-24）: https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts
- Ollama の Modelfile（`TEMPLATE` は、モデルに渡す文の全体の雛形。2026-10-24）: https://docs.ollama.com/modelfile
