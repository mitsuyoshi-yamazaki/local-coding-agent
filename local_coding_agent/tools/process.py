"""コマンドを子のプロセスで走らせ、終了コードと出力を集める（道具 run_command が使う）。

子のプロセスは、新しいセッション（プロセスのグループ）で始める。シェルが起こした孫の
プロセスまで、グループごと止められるようにするためである。止めるのは、時間切れのとき・
Ctrl-C のとき・コマンドが終わったとき（シェルが後ろで走らせたものが残っていれば）である。
子のプロセスは端末の Ctrl-C を受けない（端末が送るのは、エージェントのグループだけ）。
"""

import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path

SHELL = "/bin/sh"
# 止めた後に、出力の終わりを待つ秒数
DRAIN_SECONDS = 1.0


@dataclass(frozen=True)
class Finished:
    """走らせ終えたコマンド。"""

    # 終了コード。時間切れで止めたら None
    exit_code: int | None
    # 標準出力と標準エラーを合わせた出力。UTF-8 として読めない字は置き換えてある
    output: str


def run_shell(command: str, cwd: Path, timeout: float) -> Finished:
    """command を /bin/sh -c で走らせ、終わるか、timeout 秒が過ぎるまで待つ。

    標準入力は空にする。走らせられない（作業ディレクトリが無い、など）ときは OSError を
    投げる。Ctrl-C（KeyboardInterrupt）を受けたら、プロセスのグループを止めてから投げ直す。
    """
    with subprocess.Popen(
        [SHELL, "-c", command],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    ) as process:
        try:
            output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _stop_group(process)
            return Finished(None, _decoded(_drain(process)))
        except KeyboardInterrupt:
            _stop_group(process)
            process.wait()
            raise
        _stop_group(process)
        return Finished(process.returncode, _decoded(output))


def _drain(process: subprocess.Popen[bytes]) -> bytes:
    """止めた後に、それまでの出力を読み切る（communicate を呼び直しても、出力は失われない）。

    グループの外に出たプロセス（setsid を呼んだものなど）は止まらないので、それが出力の
    パイプを握っていると、出力の終わりが来ない。DRAIN_SECONDS 待って来なければ、そこまでの
    出力を返す（パイプは、Popen の with を出るときに閉じる）。
    """
    try:
        output, _ = process.communicate(timeout=DRAIN_SECONDS)
    except subprocess.TimeoutExpired as error:
        # POSIX では、それまでに読んだ出力の全てが error.output に入っている
        return bytes(error.output or b"")
    return bytes(output)


def _stop_group(process: subprocess.Popen[bytes]) -> None:
    """プロセスのグループに SIGKILL を送る。グループの番号は、シェルのプロセスの番号と同じ。"""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError, PermissionError:
        # グループに、もうプロセスが無い・止められるプロセスが無い
        pass


def _decoded(output: bytes) -> str:
    return output.decode("utf-8", errors="replace")
