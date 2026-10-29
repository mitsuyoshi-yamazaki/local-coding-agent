---
description: 長さの単位の変換を足す手順（引数: 足す変換。例: inch → cm）
---

長さの単位の変換を足すときは、次の順に行う。

1. convert.py の RATES に、`("<元>", "<先>"): <元の 1 が、先のいくつか>` の行を足す。逆向きの変換は RATES から求めるので、足さない。単位の名前は英小文字の略号（km・m・mile・inch・cm など）にする
2. test_convert.py の CASES に、足した向きと逆向きの2行を足す
3. CHANGELOG.md の「## 未リリース」の見出しの下に、`- 変換 <元> → <先> を足した` の行を足す
4. `python3 -m unittest` を走らせ、全て通ることを確かめる

足す変換: $ARGUMENTS
