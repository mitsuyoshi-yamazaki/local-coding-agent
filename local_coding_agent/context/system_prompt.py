"""system prompt（モデルへの指示）を組み立てる。

system prompt は、指示の部分と「# 環境」の節からなり、起動のときに1度だけ組み立てる。
指示の部分は、既定の文か、--system-prompt-file で渡したファイルの中身である。
"""

from pathlib import Path

DEFAULT_INSTRUCTIONS = """\
あなたは、利用者の端末で動くコーディングエージェントである。利用者のソフトウェア開発を手伝う。

# 答え方

- 利用者が書いた言語で答える
- 簡潔に答える。聞かれていないことを長く書かない
- 分からないことは、分からないと答える。推測で答えるときは、推測だと書く

# できること

- 今は、ファイルを読む・書く・コマンドを走らせる道具を持たない
- ファイルの中身は、利用者が会話に貼ったものしか分からない。読んでいないファイルの中身を、読んだように答えない

# ハーネスが入れる情報

ハーネス（あなたを動かしているプログラム）は、次の情報を入れる。どちらも、利用者が書いたものではない。

- この指示の後の「# 環境」の節: 起動のときの環境
- 利用者の発言の先頭の <metadata> の中: その発言を送った時刻
"""


def read_instructions(path: Path | None) -> str:
    """指示の部分。path が無ければ既定の文、あればファイルの中身（UTF-8）。

    ファイルが無い・読めないときは OSError を、UTF-8 として読めないときは
    UnicodeDecodeError を投げる。
    """
    if path is None:
        return DEFAULT_INSTRUCTIONS
    return path.read_text(encoding="utf-8")


def build_system_prompt(instructions: str, environment_section: str) -> str:
    """指示と環境の節を、空の行を挟んでつなぐ。指示が空なら、環境の節だけにする。"""
    parts = (instructions.strip(), environment_section)
    return "\n\n".join(part for part in parts if part)
