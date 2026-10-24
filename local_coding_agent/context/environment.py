"""環境の知らせ。作業ディレクトリ・git のリポジトリの中か・OS を集め、system prompt の節にする。

セッション（起動から終わりまで）の間に変わらないものだけを扱う。変わるもの（時刻）は、
発言ごとのメタデータに入れる（model/messages.py）。
"""

import platform
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Environment:
    """起動のときに集めた環境。"""

    working_directory: Path
    in_git_repository: bool
    os: str


def collect_environment(working_directory: Path) -> Environment:
    """この機械の環境を集める。"""
    return Environment(
        working_directory=working_directory,
        in_git_repository=in_git_repository(working_directory),
        os=os_description(platform.system(), platform.release(), platform.mac_ver()[0]),
    )


def in_git_repository(directory: Path) -> bool:
    """ディレクトリか、その上のどれかに .git があれば、git のリポジトリの中である。

    git worktree では .git がディレクトリではなくファイルなので、在るかだけを見る。
    """
    start = directory.absolute()
    return any((path / ".git").exists() for path in (start, *start.parents))


def os_description(system: str, release: str, mac_version: str) -> str:
    """OS の名前と版。例: macOS 15.6（Darwin 24.6.0）"""
    if system == "Darwin" and mac_version:
        return f"macOS {mac_version}（Darwin {release}）"
    return f"{system} {release}".strip()


def environment_section(environment: Environment) -> str:
    """system prompt の「# 環境」の節。"""
    in_git = "はい" if environment.in_git_repository else "いいえ"
    return (
        "# 環境\n"
        "\n"
        f"- 作業ディレクトリ: {environment.working_directory}\n"
        f"- 作業ディレクトリは git のリポジトリの中か: {in_git}\n"
        f"- OS: {environment.os}"
    )
