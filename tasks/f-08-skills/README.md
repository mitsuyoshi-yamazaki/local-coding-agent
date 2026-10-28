# F-08 を試す材料

skills（F-08）を試すための、小さなプロジェクトと、3つのスキルである。プロジェクトを写し、スキルを写しの `.local-coding-agent/skills/` に写して、写しを作業ディレクトリにしてエージェントを起動する。エージェントが写しを書き換えるので、試すたびに写し直す。

| ファイル | 中身 |
|---|---|
| `project/convert.py` | 長さの単位の変換。変換の表 `RATES` に km → m と mile → km がある |
| `project/test_convert.py` | テスト。写したばかりの状態では全て通る |
| `project/CHANGELOG.md`・`project/VERSION` | 変更の記録と版 |
| `skills/add-conversion/SKILL.md` | 変換を足す手順。表に足す・テストに足す・変更の記録に足す・テストを走らせる。変更の記録に足すことは、頼まれなければモデルがしない |
| `skills/review/SKILL.md`・`skills/review/checklist.md` | 観点に沿ってコードを読む手順。観点は付いているファイル `checklist.md` にだけあり、本文には無い |
| `skills/release/SKILL.md` | 版を上げる手順。下の課題のどの依頼にも合わない |

## 写して起動する

リポジトリの根で:

```sh
cp -R tasks/f-08-skills/project .tmp/f-08-project
mkdir .tmp/f-08-project/.local-coding-agent
cp -R tasks/f-08-skills/skills .tmp/f-08-project/.local-coding-agent/skills
.venv/bin/python -m local_coding_agent --model qwen3.5:9b --directory .tmp/f-08-project
```

- 起動の行に `スキル: 3（add-conversion・release・review）` が出る
- 写し直すときは、前の写しを消してから写す。`cp -R` は、写し先のディレクトリがあると、その中に写す
- 走行の記録は、写しの中の `traces/` に書かれる。起動のときの `skills` の件に、一覧に入ったスキルがある。モデルに送った一覧は、`request` の件の system prompt の「# スキル」の節にある。`load_skill` の呼び出しと、返した中身は `tool` の件にある
- 既定の許可のモードは `allow-all` である。`load_skill` は読む道具なので、`ask` でも問わずに通る

## 課題

| 課題 | 打つもの | 見ること |
|---|---|---|
| 合う依頼で読み込む | `インチとセンチメートルの変換を足して` | `load_skill` で `add-conversion` を読み込むか。手順どおり、変更の記録にも足したか（下の判定） |
| 付いているファイルを読む | `convert.py をレビューして` | `review` を読み込んだ後に、`checklist.md` を `read_file` で読むか。答えが4つの観点に沿うか（人が判定） |
| 合わない依頼で読まない | `convert.py の役目を1行で説明して` | `load_skill` を呼ばないか |
| `/<名前>` で呼ぶ | `/review convert.py` | `[スキル]` の行が出る。送った発言が `<metadata>` の `スキル: /review convert.py` を持つ。モデルが `load_skill` で読み込み直さないか |
| 一覧 | `/help` | 自作のコマンドの後に、スキルの3つが出る。モデルを呼ばない |
| 一覧の大きさ | スキルを写した写しと、写さない写し（上の `mkdir` と2つ目の `cp` をしない）で、それぞれ `こんにちは` を送る | 1つ目の要求の入力トークン数（`/context`・走行の記録の `response` の件の `model_stats.prompt_eval_count`）の差が、一覧の大きさである |
| 本文の大きさ | 合う依頼で読み込んだ回の、`load_skill` の前と後の要求 | 入力トークン数の増えた分が、主に本文の大きさである |

課題は1つずつ、新しい写しで試す（前の課題の書き換えと履歴が、次の課題に効かないように）。`/review` と `convert.py をレビューして` の答えは、人が読んで判定する。

## 判定

「合う依頼で読み込む」の課題は、リポジトリの根で、写しに対して判定のコマンドを走らせる。4つが全て通れば、終了コードが 0 である。写したばかりの状態では、テストは通るが、ほかの3つが通らない。

```sh
.venv/bin/python tasks/f-08-skills/judge.py .tmp/f-08-project
```

| 判定の項 | 見ること |
|---|---|
| テストが全て通る | `python -m unittest` の終了コード |
| inch と cm を変換できる | `convert(1, "inch", "cm")` が 2.54 で、逆向きも求まる |
| テストに inch の場合がある | `test_convert.py` に足した |
| 変更の記録に足した | `CHANGELOG.md` の「## 未リリース」の節に、inch と cm を含む行がある（スキルの手順の3.） |
