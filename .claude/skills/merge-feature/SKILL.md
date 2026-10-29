---
name: merge-feature
description: worktree 側で実装が済んだ機能の branch を main に取り込み（要れば衝突を解き）、人が確かめるための案内（動作の確かめ方・読む順・既存の実装からの変わり）を機能のディレクトリの guide.md に書いて示す。main 側のセッションで、人が /merge-feature <branch> で呼ぶ
argument-hint: <branch>
arguments: [branch]
disable-model-invocation: true
---

# 機能の branch を main に取り込み、確かめる案内を示す

取り込む branch: `$branch`

CLAUDE.md の「main と worktree の分担」の、main 側の「worktree 側の実装が済んだら、`git merge f-NN-<機能名>` で main に取り込む」と、その後の確認の始めを行う。人への返答は日本語で書く。

`$` を含む Bash のコマンドは deny で止まる。commit の hash は変数に入れず、控えた値をコマンドに直に書く。以下では、取り込む前の main の commit を「基点」と呼ぶ。

## 1. 前提を確かめる

次のどれかに当たれば、取り込まずに止め、人に伝える。

- `git branch --show-current` が `main` でない（main 側のセッションでだけ使う）
- `git status` に未コミットの変更がある（捨てない・stash しない。どうするかを人に問う）
- branch が指定されていない、または `polish` である（polish は main に取り込まない）
- `git rev-parse --verify $branch` が失敗する（branch が無い）

基点を控える。

- まだ取り込んでいない（`git log --oneline main..$branch` に commit がある）: `git rev-parse --short HEAD` の値が基点
- もう取り込んである（上が空）: `git log --merges --oneline -1 --grep "Merge branch '$branch'"` で取り込んだ commit を探し、`git rev-parse --short <その commit>^1` の値を基点にする。3. の「取り込む」と 4. の検査・記録は飛ばし（記録のうち、memo.md を作ることだけは行う）、下の確かめと案内（5.）を行う。見つからなければ、基点を人に問う
  - 衝突の解き方を `git show --remerge-diff <その commit>` で確かめる。git が自動で合わせた結果（衝突の印を含む）と、実際に commit した結果の差が出る。出たファイルが、衝突した（または取り込みのときに手で直した）ファイルである。`git log -p --left-right` で両側が触ったファイルを見るだけでは、どこが衝突したかを取り違える（F-03 で取り違えた）
  - 解いた所で main の変更が落ちていれば（3. の方針に合わなければ）、main で直して commit し（`docs: …`・`fix: …`）、handoff.md の「問いと答えの記録」に、衝突したファイル・解き方・直したことを書く。振る舞いが変わる直しは、直す前に人に示す

## 2. 引き継ぎを読む

- 機能のディレクトリ `docs/features/f-NN-<機能名>/` を、`git diff --name-only <基点>...$branch -- docs/features/` から得る
- まだ取り込んでいなければ、`git show $branch:docs/features/f-NN-<機能名>/handoff.md` で読む（取り込んだ後なら Read で読む）
- 「進み具合」の段が「実装が済んだ」でなければ、取り込まずに止め、人に問う
- 「main 側に頼むこと」と「main と衝突しそうな所」を読む。取り込みの前にすることがあれば、人に示す

## 3. 取り込む

`git merge --no-edit $branch` で取り込む。

衝突したら、次のように解く。

- 衝突したファイルを `git diff --name-only --diff-filter=U` で出す
- 両側の変更の意図を `git log -p --left-right HEAD...MERGE_HEAD -- <ファイル>` で読む
- 方針: main の変更（確認の間の直し・要件・設定）を残し、branch の実装をそれに合わせる。branch が関数を別のファイルへ移していて、main がその関数を直していれば、直しを移した先へ写す（handoff.md の「main と衝突しそうな所」に、移した先が書いてある）
- 次のときは解かずに止め、両側の違いと解き方の案を示して人に問う
  - 両側で振る舞い（仕様）が違い、どちらかを選ぶことになる
  - `docs/requirements.md`・`CLAUDE.md`・`.claude/`・`pyproject.toml`・`poetry.lock` の衝突（人と相談して変えるもの）
- `docs/request-formats.md`（生成する文書）の衝突は、手で解かない。ほかの衝突（`tests/request_formats/` の場面を含む）を解いた後に、`.venv/bin/python -m tests.request_formats` で生成し直し、`git add docs/request-formats.md` する
- 解いたら `git add <ファイル>` し、4. の検査を通してから commit する。message の1行目は `Merge branch '<branch>'`、本文に衝突したファイルと、どう解いたかを書く
- 取り込みをやめる（`git merge --abort`）ときは、人に確かめてから行う

衝突が無くても、意味の衝突はありうる（main で直した関数を、branch が移した・名前を変えた）。「main と衝突しそうな所」に挙がった所は、`git diff <基点> HEAD -- <ファイル>` で、main の直しが残っているかを見る。

## 4. 検査し、記録する

CLAUDE.md の「Python の環境」の4つ（unittest・`ruff check`・`ruff format --check`・mypy）を走らせる。落ちたら原因を調べ、取り込みで生じたものなら main で直して commit する（`fix: …`）。branch の実装そのものの誤りなら、直す前に人に示す。`tests/test_request_formats.py` だけが落ちたら（main の直しと branch の変わりが合わさり、`docs/request-formats.md` が古い）、差分が両側の変わりの和であることを読んでから生成し直し、commit する（`docs: 取り込んだ後のコードで、モデルへ送る要求の形を生成し直す`）。取り込みでは、作るエージェントを実物のモデルで走らせない（試すのは人。Claude Code が走らせるのは、人に頼まれたとき。CLAUDE.md の main 側）。

記録する。

- handoff.md の「問いと答えの記録」に、取り込みの節を足す: 日付・取り込んだ commit・基点・衝突したファイルと解き方・検査の結果・main で直したこと。commit する（`docs: …`）
- `docs/progress.md` を書き直す（CLAUDE.md の「記録」）: 「機能ごとの段」の実装を済にする・「現在の状況」の確認中の機能・「人を待っていること」（読む・試す）・「経過」に足す。書き直したら、CLAUDE.md の main 側のとおり、`.worktrees/next/` と `.worktrees/polish/` へ写しを置く
- 持ち主のメモ `docs/features/f-NN-<機能名>/memo.md` を、`touch` で空のファイルとして作る。`.gitignore` で git に入れないので、取り込みでは届かず、main 側で作る。あれば中身を変えない（中身は持ち主が書く）

## 5. 確かめる案内を書き、人に示す

次の3つを、この順で、確かめる案内 `docs/features/f-NN-<機能名>/guide.md` に書き、返答でも示す。handoff.md を写すだけにせず、取り込んだ後のコードと差分で確かめる。handoff.md と食い違えば、コードと差分を正とし、食い違いも示す（食い違いは返答で示し、guide.md には正しい方だけを書く）。ファイルと関数は、行へのリンクで示す。行の番号は Read で確かめる。

- guide.md の始めに、何の案内か・基点と取り込んだ commit・出所（`spec.md`・`implementation.md`・`handoff.md`）と、行の番号は guide.md を最後に直した commit のコードのものであることを書く。形は F-05 の `docs/features/f-05-run-command/guide.md` に揃える
- リンクのパスは、guide.md の中では guide.md からの相対パス（`../../../local_coding_agent/…#L12`）、返答の中ではリポジトリの根からのパスにする
- guide.md に書くのは3つだけで、取り込みの結果（検査・記録）と人に頼むことは書かない（handoff.md と返答に書く）
- `docs/features.md` の表の、その機能の行に、`[確かめる案内](features/f-NN-<機能名>/guide.md)` を足す
- もう guide.md があれば（取り込み済みで呼んだときなど）、今のコードと差分で確かめ直し、違う所を直す
- commit する（`docs: F-NN の確かめる案内を書く`）

### 動作の確かめ方

出所: `spec.md` の「試し方」・`implementation.md` の「使い方」と試す材料の節・`README.md` の「起動」・handoff.md の「テストで確かめたこと・確かめていないこと」。

- 準備: 要るモデルと Ollama の設定（文脈の長さなど）。`git diff --stat <基点> HEAD -- pyproject.toml poetry.lock` が空でなければ、`poetry install` を人に頼む
- 起動のコマンド（そのまま打てる形）
- 課題ごとに: 打つ依頼の文・期待する答え・見る所（画面の表示と、`traces/` の走行の記録のどの件のどの欄か）
- テストで確かめておらず、実物で見てほしいこと
- 人がテストを走らせるコマンド

### 読む順

出所: handoff.md の「読む順の案内（案）」。

- 項ごとに: ファイルと関数・それを呼ぶ入口（呼ばれる側を挙げるときは、呼ぶ入口を一緒に挙げる。F-01 で持ち主が求めた）・読むと分かること・おおよその行数
- 取り込んだ後のコードで、ファイルと関数が今もあるかを確かめる（衝突を解いた所・main の直しで変わった所）
- ほぼ移しただけのファイルは、そう書き、中身で変わった所だけを挙げる

### 既存の実装からの変わり

出所: `git diff --stat <基点> HEAD`・`git diff <基点> HEAD -- local_coding_agent tests`・`git diff <基点> HEAD -- docs/request-formats.md`・handoff.md の「実装の全体像」「設計の選択と理由・捨てた案」「実装前の仕様との違い」。

- 足したファイル・直したファイル・移した関数（どこからどこへ。移しただけか、中身も変えたか）
- 振る舞いの変わり: 利用者から見て・モデルへ送る要求の中身・走行の記録の欄。要求の中身の変わりは、`docs/request-formats.md` の差分で確かめ、変わった場面と見どころを示す
  - 機能が送る形を変えたのに、その場面か見どころが無ければ（新しい欄・枠・利用者の操作が、文書の「一覧」に無い）、main で `tests/request_formats/` に足して生成し直し、guide.md と別の commit にする（`test: F-NN の、モデルへ送る要求の形の場面を足す`）。足したことを、handoff.md の「問いと答えの記録」と返答に書く
- 依存の向きの変わり
- 文書・試す材料・設定の変わり（短く）
- 衝突を解いて、branch の実装から変えた所

## 6. 前の機能の guide.md に注釈を足す

取り込んだ機能のほかの guide.md（前の機能のもの）は、直さない。後の変更に合わせて直し続けると切りが無いためである（持ち主の指示）。代わりに、取り込んだ変更で、前の機能の guide.md の確かめ方がそのままでは動かなくなったら、いつ入った変更で動かなくなったかの注釈を足す。

- 確かめるのは、`docs/features/` の下の、取り込んだ機能のほかの guide.md の全てである
- 動かなくなったかは、`git diff <基点> HEAD` のうち、起動の引数と既定の振る舞い・試す材料と判定のコマンド（`tasks/`）・画面の表示・走行の記録の欄の変わりを、各 guide.md の「動作の確かめ方」と照らして決める。行の番号が動いただけでは、注釈を足さない（行の番号がどの commit のコードのものかは、guide.md の始めに書いてある）
- 注釈は、guide.md の始めの段落の後の節「## 後の変更で動かなくなった所」に、変更ごとに1項で足す。節が無ければ作り、節の始めに「この案内の中身は、書いた時点のまま直していない。後の変更で、そのままでは動かなくなった所を、変更ごとに書く。」と書く
- 1項に書くこと: どの変更か（機能・取り込んだ commit・日付）・どの節の何がそのままでは動かないか・当時の振る舞いを得る方法（短く書けるときだけ）
- 初めて注釈を足すときは、始めの段落の「行の番号は、この案内を最後に直した commit のコードのもの（`git log -1 …` で分かる）」を、中身を最後に直した commit の hash を書いた文に替える。注釈の commit で、`git log -1` が指す commit が変わるためである。例: 「行の番号は、commit `b0422f2`（この案内の中身を最後に直した commit）のコードのものである。下の注釈を足した commit では、行の番号を確かめ直していない。」（F-05 の guide.md）
- commit する（`docs: F-NN の確かめる案内に、F-MM で動かなくなった所の注釈を足す`）。返答で、注釈を足した guide.md と中身を示す

main の直し（取り込みでないもの）で前の機能の guide.md が動かなくなったときも、同じく注釈を足す。項の「どの変更か」には、直しの commit を書く。

## 7. 返答を終える・その後

最後に、人に決めてもらうこと・問うことを並べる。削除・push・次の機能のセッションを始めることは、返答で頼まず、思い出させもしない（持ち主の指示）。handoff.md に頼むことと書いてあっても、`docs/progress.md` の「人を待っていること」に写すだけにする。branch と stash の削除は、progress.md にも写さない（CLAUDE.md の「削除」）。この後に来た人の問いには handoff.md を読んで答え、問いと答え・直したことを「問いと答えの記録」に足す（CLAUDE.md の main 側）。

取り込んだ機能の guide.md は、中身が変わるたびに追従させる。main で直したことで、動作の確かめ方・読む順・既存の実装からの変わりのどれかが変われば（関数や行が動いた・起動や判定のコマンドが変わった・振る舞いが変わった・試す材料が変わった）、guide.md も直し、直しと同じ commit に入れる。guide.md が今のコードと食い違うと分かったときも直す。行の番号は、直すたびに Read で確かめ直す。前の機能の guide.md は直さず、6. の注釈を足す。

モデルへ送る要求の形の文書 `docs/request-formats.md` も追従させる。main で直したことで、送る要求の形が変われば（欄・枠・文が増えた・変わった・消えた）、`tests/request_formats/` の場面と見どころを直し、`.venv/bin/python -m tests.request_formats` で生成し直して、直しと同じ commit に入れる（CLAUDE.md の「モデルへ送る要求の形」）。
