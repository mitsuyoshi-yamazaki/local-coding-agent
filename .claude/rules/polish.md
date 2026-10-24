# polish 側の進め方

polish 側（branch `polish`）のセッションへの指示である。この rule は polish の branch にだけあり、main へは取り込まない。CLAUDE.md の「polish 側」の項と併せて守る。

## 目的

- 本アプリケーションを、ソフトウェアとして使うときの使いやすさを上げる
- 学習と実装が済んだ後に、このソフトウェアを（学習に使ったものとは別のリポジトリで）改善していく。polish は、その元になるものを作る
- main は学習用の簡素な実装に保つ。polish は main と目的が違うので、CLAUDE.md・rule・開発の運用を独自に変えることがある。`git merge main` で衝突したら、polish の変更を活かして解く。変えたら、polish-progress.md の「main との差異」に書く

## ファイル

| ファイル | 中身 | git |
|---|---|---|
| `docs/polish/issues-human.md` | 人が起票する問題と改善の内容 | 入れない |
| `docs/polish/issues-claude.md` | Claude Code が見つけた問題と改善の提案 | 入れない |
| `docs/polish/specs/yyyy-MM-dd_<変更内容>.md` | 要件や仕様が素直に決まらない変更の、要件定義と仕様 | 入れる |
| `docs/polish/polish-progress.md` | 現在の状況・main との差異・main 側に頼むこと・経過 | 入れる |

- `docs/polish/handoff.md` は作らない。セッションの間の引き継ぎは、polish-progress.md と specs/ に書く
- `docs/polish/` の下には `.claude/rules/docs.md` を当てない（`paths` にも足さない）。経過を書いてよい
- commit するファイルは公開される。個人の情報・秘匿情報・手元の絶対パスを書かない

## issues の書き方

- 1件を、`## H-NN 題`（issues-human.md）・`## C-NN 題`（issues-claude.md）の見出しで書く。番号は使い回さない。次の番号は、2つの issues と polish-progress.md の経過に出てくる番号の、最も大きいものの次にする
- 人が番号を付けずに書いた項目には、Claude Code が着手するときに番号を振る
- Claude Code が issues-human.md に書くのは、番号・着手した印（見出しのすぐ下に `作業中・specs/…` の1行）・解決した項目の削除だけである。人が書いた本文は書き換えない。分けたほうがよいと思ったら、人に提案する
- issues-claude.md には、作業中や `git merge main` のときに気づいた問題と改善の提案を書く。1件に、問題・提案・根拠（ファイル）を書く。コード全体を点検して提案を出すのは、人が頼んだときだけである

## 進め方

1. **取り出す**: issues-human.md の上から順に1件取り出す。issues-human.md に残りが無いときは、issues-claude.md のうち、人が見出しのすぐ下に「承認」と書いた項目を上から取り出す。承認されていない Claude Code の提案には着手しない
2. **要件と仕様**: 要件や仕様が素直に決まらないときは、人に言ってから specs/ に書き始め、人と相談して決める（人が指定してもよい）
   - ファイル名の日付は書き始めた日、`<変更内容>` は英小文字とハイフンにする（例: `2026-10-24_streaming-display.md`）
   - 人が承認した後は直さずに残す。実装で変わった点は、polish-progress.md の経過に書く
3. **実装**: テストを書いて実装し、テスト・lint・型の検査を通す。通ったら commit してよい
4. **解決の確かめ**: 人に「解決した」と報告する。実物のモデルで試すのは人である。人が了承したら、issues から項目を消し、polish-progress.md に書いて commit する。一部だけ解決したときは、残りが分かるように項目を書き直して残す

## polish-progress.md の書き方

- **現在の状況**: 作業中の issue と、人を待っていること。変わるたびに書き直す
- **main との差異**: 目的・運用・設定と文書・コードで、main と違うところ。経過ではなく、今の状態として書き直す。`git merge main` で差異が変わったときも直す
- **main 側に頼むこと**: main 側や上流に上げたいこと。polish 側は inbox・outbox を扱わないので、人が main 側に伝える。伝わったら、経過に移す
- **経過**: 日付ごとに、issue の番号・変更の概要・commit を足していく。書いたものは直さない
