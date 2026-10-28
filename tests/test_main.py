import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from local_coding_agent.__main__ import main, parse_args
from local_coding_agent.permissions.settings import SETTINGS_PATH
from local_coding_agent.tools.default import DEFAULT_TOOLS


class MainTestCase(unittest.TestCase):
    """走行の記録を、一時ディレクトリに書かせる（main は起動のときに1件を書く）。"""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.traces = Path(directory.name)
        patcher = mock.patch("local_coding_agent.__main__.TRACE_DIRECTORY", self.traces)
        patcher.start()
        self.addCleanup(patcher.stop)


class ArgsTest(MainTestCase):
    def test_system_prompt_file_is_optional(self) -> None:
        self.assertIsNone(parse_args(["--model", "m"]).system_prompt_file)

    def test_system_prompt_file_is_path(self) -> None:
        args = parse_args(["--model", "m", "--system-prompt-file", "tasks/x.md"])
        self.assertEqual(args.system_prompt_file, Path("tasks/x.md"))

    def test_show_thinking_is_off_by_default(self) -> None:
        self.assertFalse(parse_args(["--model", "m"]).show_thinking)

    def test_show_thinking_reaches_session(self) -> None:
        with (
            mock.patch("local_coding_agent.cli.repl.run") as run,
            redirect_stdout(io.StringIO()),
        ):
            main(["--model", "m", "--show-thinking"])
        self.assertTrue(run.call_args.args[0].show_thinking)


class MainTest(MainTestCase):
    def test_instructions_file_and_environment_reach_session(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "long.md"
            path.write_text("長い指示\n", encoding="utf-8")
            # REPL を走らせず、渡された Session だけを受け取る
            with (
                mock.patch("local_coding_agent.cli.repl.run") as run,
                redirect_stdout(io.StringIO()) as output,
            ):
                code = main(["--model", "m", "--system-prompt-file", str(path)])
        self.assertEqual(code, 0)
        session = run.call_args.args[0]
        self.assertTrue(session.system.startswith("長い指示\n\n# 環境\n"))
        self.assertIn(f"指示: {path}", output.getvalue())
        self.assertEqual(session.tools, DEFAULT_TOOLS)
        self.assertEqual(session.cwd, Path.cwd())

    def test_missing_instructions_file_stops_before_start(self) -> None:
        with (
            mock.patch("local_coding_agent.cli.repl.run") as run,
            redirect_stdout(io.StringIO()) as output,
            redirect_stderr(io.StringIO()) as errors,
        ):
            code = main(["--model", "m", "--system-prompt-file", "no/such.md"])
        self.assertEqual(code, 2)
        self.assertIn("指示のファイルを読めない（no/such.md）", errors.getvalue())
        self.assertEqual(output.getvalue(), "")
        run.assert_not_called()


class PermissionsAtStartTest(MainTestCase):
    def setUp(self) -> None:
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cwd = Path(directory.name).resolve()
        patcher = mock.patch(
            "local_coding_agent.__main__.Path.cwd", return_value=self.cwd
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_settings(self, text: str) -> None:
        path = self.cwd / SETTINGS_PATH
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")

    def start(self, *argv: str) -> tuple[int, mock.MagicMock, str, str]:
        with (
            mock.patch("local_coding_agent.cli.repl.run") as run,
            redirect_stdout(io.StringIO()) as output,
            redirect_stderr(io.StringIO()) as errors,
        ):
            code = main(["--model", "m", *argv])
        return code, run, output.getvalue(), errors.getvalue()

    def test_settings_file_reaches_session(self) -> None:
        self.write_settings(
            '{"permissions": {"mode": "ask", "deny": ["run_command(rm *)"]}}'
        )
        code, run, output, _ = self.start()
        self.assertEqual(code, 0)
        permissions = run.call_args.args[0].permissions
        self.assertEqual(permissions.mode, "ask")
        self.assertEqual(
            [str(rule) for rule in permissions.deny], ["run_command(rm *)"]
        )
        self.assertIn(f"許可: ask・規則 1（{SETTINGS_PATH}）\n", output)

    def test_without_settings_file_allows_all(self) -> None:
        _, run, output, _ = self.start()
        self.assertEqual(run.call_args.args[0].permissions.mode, "allow-all")
        self.assertIn("許可: allow-all・規則 0（設定ファイル無し）\n", output)

    def test_permission_mode_overrides(self) -> None:
        self.write_settings('{"permissions": {"mode": "ask"}}')
        _, run, _, _ = self.start("--permission-mode", "accept-edits")
        self.assertEqual(run.call_args.args[0].permissions.mode, "accept-edits")

    def test_first_trace_record_is_permissions(self) -> None:
        self.start("--permission-mode", "ask")
        (path,) = self.traces.iterdir()
        first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(
            {key: first[key] for key in ("type", "mode", "source", "deny")},
            {"type": "permissions", "mode": "ask", "source": None, "deny": []},
        )

    def test_bad_settings_file_stops_before_start(self) -> None:
        self.write_settings('{"permissions": {"mode": "default"}}')
        code, run, output, errors = self.start()
        self.assertEqual(code, 2)
        self.assertIn(
            f"設定ファイルを読めない（{SETTINGS_PATH}）: permissions.mode", errors
        )
        self.assertEqual(output, "")
        run.assert_not_called()
        self.assertEqual(list(self.traces.iterdir()), [])


class DirectoryTest(MainTestCase):
    def setUp(self) -> None:
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name).resolve()

    def start(self, directory: Path) -> tuple[int, mock.MagicMock, str, str]:
        with (
            mock.patch("local_coding_agent.cli.repl.run") as run,
            redirect_stdout(io.StringIO()) as output,
            redirect_stderr(io.StringIO()) as errors,
        ):
            code = main(["--model", "m", "--directory", str(directory)])
        return code, run, output.getvalue(), errors.getvalue()

    def test_directory_is_the_working_directory(self) -> None:
        settings = self.directory / SETTINGS_PATH
        settings.parent.mkdir()
        settings.write_text('{"permissions": {"mode": "ask"}}', encoding="utf-8")
        # 走行の記録の置き場を、既定の相対パスに戻す
        with mock.patch("local_coding_agent.__main__.TRACE_DIRECTORY", Path("traces")):
            code, run, output, _ = self.start(self.directory)
        self.assertEqual(code, 0)
        session = run.call_args.args[0]
        self.assertEqual(session.cwd, self.directory)
        self.assertEqual(session.permissions.mode, "ask")
        self.assertIn(f"作業ディレクトリ: {self.directory}", session.system)
        (trace,) = (self.directory / "traces").iterdir()
        self.assertIn(f"走行の記録: {trace}\n", output)

    def test_not_a_directory_stops_before_start(self) -> None:
        missing = self.directory / "no-such"
        code, run, output, errors = self.start(missing)
        self.assertEqual(code, 2)
        self.assertIn(f"作業ディレクトリにできない（{missing}）", errors)
        self.assertEqual(output, "")
        run.assert_not_called()
        self.assertEqual(list(self.traces.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
