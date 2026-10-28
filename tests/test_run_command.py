import io
import shlex
import signal
import sys
import time
import unittest
from pathlib import Path
from types import FrameType

from local_coding_agent.loop.turn import run_turn
from local_coding_agent.model.chat import Done, ToolCall
from local_coding_agent.model.messages import ToolResultBlock
from local_coding_agent.permissions.confirm import REFUSED
from local_coding_agent.tools import run_command
from local_coding_agent.tools.default import DEFAULT_TOOLS
from local_coding_agent.tools.process import DRAIN_SECONDS, run_shell
from local_coding_agent.tools.tool import ToolError
from tests.fakes import ScriptedLines, ScriptedModel, fake_session
from tests.test_tools import ToolTestCase

STOP = Done(done_reason="stop", stats={})
# コマンドが止まらずに最後まで待ったら、これより長く掛かる
WAITED_TOO_LONG = 10
# テストを走らせている Python。シェルのコマンドに埋め込む
PYTHON = shlex.quote(sys.executable)


def _interrupt(signum: int, frame: FrameType | None) -> None:
    raise KeyboardInterrupt


class RunShellTest(ToolTestCase):
    """本物の /bin/sh で、一時ディレクトリの中で走らせる。"""

    def test_exit_code_and_output(self) -> None:
        finished = run_shell("echo 一; exit 3", self.cwd, 10)
        self.assertEqual((finished.exit_code, finished.output), (3, "一\n"))

    def test_stderr_is_merged_in_order(self) -> None:
        finished = run_shell("echo a; echo b >&2; echo c", self.cwd, 10)
        self.assertEqual(finished.output, "a\nb\nc\n")

    def test_stdin_is_empty(self) -> None:
        finished = run_shell("cat; echo 終わり", self.cwd, 10)
        self.assertEqual(finished.output, "終わり\n")

    def test_runs_in_cwd(self) -> None:
        finished = run_shell("pwd", self.cwd, 10)
        self.assertEqual(Path(finished.output.strip()).resolve(), self.cwd.resolve())

    def test_undecodable_bytes_are_replaced(self) -> None:
        finished = run_shell("printf 'a\\377b'", self.cwd, 10)
        self.assertEqual(finished.output, "a�b")

    def test_timeout_keeps_output_and_stops_background_processes(self) -> None:
        # 後ろで走らせたプロセスが出力を握ったままだと、止めない限り 30 秒待つ
        started = time.monotonic()
        command = "echo 前; (sleep 30; echo 後) & sleep 30"
        finished = run_shell(command, self.cwd, 0.5)
        self.assertLess(time.monotonic() - started, WAITED_TOO_LONG)
        self.assertEqual((finished.exit_code, finished.output), (None, "前\n"))

    def test_timeout_returns_even_if_process_outside_group_holds_output(self) -> None:
        # setsid でグループの外に出たプロセスは止まらず、出力のパイプを握ったまま 5 秒走る
        escaped = f"{PYTHON} -c 'import os, time; os.setsid(); time.sleep(5)'"
        started = time.monotonic()
        finished = run_shell(f"echo 前; {escaped} & sleep 30", self.cwd, 1)
        # 時間切れの 1 秒と、出力の終わりを待つ DRAIN_SECONDS で返る
        self.assertLess(time.monotonic() - started, 1 + DRAIN_SECONDS + 1.5)
        self.assertEqual((finished.exit_code, finished.output), (None, "前\n"))

    def test_background_process_is_stopped_when_command_ends(self) -> None:
        run_shell("(sleep 0.3; touch made) > /dev/null 2>&1 &", self.cwd, 10)
        time.sleep(0.8)
        self.assertFalse((self.cwd / "made").exists())

    def test_missing_cwd_raises_os_error(self) -> None:
        with self.assertRaises(OSError):
            run_shell("true", self.cwd / "none", 10)

    def test_ctrl_c_stops_the_group_and_is_raised_again(self) -> None:
        # Ctrl-C を、0.3 秒後に届く信号で真似る
        previous = signal.signal(signal.SIGALRM, _interrupt)
        self.addCleanup(signal.signal, signal.SIGALRM, previous)
        self.addCleanup(signal.setitimer, signal.ITIMER_REAL, 0)
        signal.setitimer(signal.ITIMER_REAL, 0.3)
        started = time.monotonic()
        with self.assertRaises(KeyboardInterrupt):
            run_shell("(sleep 0.6; touch made) & sleep 30", self.cwd, 10)
        self.assertLess(time.monotonic() - started, WAITED_TOO_LONG)
        time.sleep(0.8)
        self.assertFalse((self.cwd / "made").exists())


class RunCommandTest(ToolTestCase):
    def run_tool(self, **arguments: object) -> str:
        return run_command.run(arguments, self.cwd)

    def test_exit_code_then_output(self) -> None:
        self.assertEqual(self.run_tool(command="echo 一"), "終了コード: 0\n一")

    def test_failure_is_a_normal_result(self) -> None:
        result = self.run_tool(command="echo 失敗 >&2; exit 1")
        self.assertEqual(result, "終了コード: 1\n失敗")

    def test_no_output(self) -> None:
        self.assertEqual(self.run_tool(command="true"), "終了コード: 0\n（出力なし）")

    def test_timeout(self) -> None:
        result = self.run_tool(command="echo 途中; sleep 30", timeout=1)
        self.assertEqual(result, "時間切れ: 1 秒で止めた\n途中")

    def test_long_output_keeps_head_and_tail(self) -> None:
        result = self.run_tool(command="printf 'a%.0s' $(seq 6000); seq 2000")
        head, note, *tail = result.split("\n")[1:]
        self.assertEqual(head, "a" * 5000)
        self.assertRegex(note, r"^（中略: \d+ 字。全体は \d+ 字）$")
        self.assertEqual(len("\n".join(tail)), 5000)
        self.assertEqual(tail[-1], "2000")

    def test_clip(self) -> None:
        self.assertEqual(run_command.clip("a" * 10_000), "a" * 10_000)
        self.assertEqual(
            run_command.clip("a" * 6000 + "b" * 6000),
            "a" * 5000 + "\n（中略: 2000 字。全体は 12000 字）\n" + "b" * 5000,
        )

    def test_preview_shows_the_command(self) -> None:
        preview = run_command.TOOL.preview
        assert preview is not None
        self.assertEqual(preview({"command": "make test"}, self.cwd), "$ make test")

    def test_summary_is_first_line_and_line_count(self) -> None:
        self.assertEqual(
            run_command.summary("終了コード: 1\na\nb"), "終了コード: 1・3 行"
        )

    def test_errors(self) -> None:
        preview = run_command.TOOL.preview
        assert preview is not None
        for command, message in (
            ("", "command が空である"),
            (" \n", "command が空である"),
            ("echo \0", "command に NUL の字がある"),
        ):
            for function in (run_command.run, preview):
                with (
                    self.subTest(command=command, function=function),
                    self.assertRaisesRegex(ToolError, message),
                ):
                    function({"command": command}, self.cwd)

    def test_missing_cwd(self) -> None:
        with self.assertRaisesRegex(ToolError, "走らせられない"):
            run_command.run({"command": "true"}, self.cwd / "none")


class CommandInLoopTest(ToolTestCase):
    """本物の run_command を、台本どおりに呼ぶ偽物のモデルのループに掛ける。"""

    def run_turn(self, answer: str) -> tuple[ToolResultBlock, str]:
        command = "echo 走った > ran.txt; echo 失敗; exit 1"
        call = ToolCall("c", "run_command", {"command": command})
        model = ScriptedModel([[call, STOP], [STOP]])
        output = io.StringIO()
        session = fake_session(
            model, DEFAULT_TOOLS, ScriptedLines(answer), output=output, cwd=self.cwd
        )
        run_turn(session, (), "テストを走らせよ", 1)
        result = model.sent[1][-1].content[0]
        assert isinstance(result, ToolResultBlock)
        return result, output.getvalue()

    def test_shows_command_then_runs_when_allowed(self) -> None:
        result, output = self.run_turn("y")
        self.assertIn(
            "$ echo 走った > ran.txt; echo 失敗; exit 1\n"
            "[許可] 問う: モード ask\n"
            "→ 終了コード: 1・2 行\n",
            output,
        )
        self.assertEqual(
            (result.content, result.is_error), ("終了コード: 1\n失敗", False)
        )
        self.assertTrue((self.cwd / "ran.txt").exists())

    def test_does_not_run_when_refused(self) -> None:
        result, output = self.run_turn("n")
        self.assertIn(f"→ 誤り: {REFUSED}\n", output)
        self.assertTrue(result.is_error)
        self.assertFalse((self.cwd / "ran.txt").exists())


if __name__ == "__main__":
    unittest.main()
