import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from local_coding_agent.__main__ import main, parse_args
from local_coding_agent.tools.default import DEFAULT_TOOLS


class ArgsTest(unittest.TestCase):
    def test_system_prompt_file_is_optional(self) -> None:
        self.assertIsNone(parse_args(["--model", "m"]).system_prompt_file)

    def test_system_prompt_file_is_path(self) -> None:
        args = parse_args(["--model", "m", "--system-prompt-file", "tasks/x.md"])
        self.assertEqual(args.system_prompt_file, Path("tasks/x.md"))


class MainTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
