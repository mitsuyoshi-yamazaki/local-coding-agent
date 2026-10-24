"""起動: python -m local_coding_agent --model <モデルのタグ> [--host <URL>]
[--system-prompt-file <パス>] [--debug [raw]]
"""

import argparse
import sys
import time
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from local_coding_agent.cli import repl
from local_coding_agent.context.environment import (
    collect_environment,
    environment_section,
)
from local_coding_agent.context.system_prompt import (
    build_system_prompt,
    read_instructions,
)
from local_coding_agent.model.ollama import OllamaChat
from local_coding_agent.trace.writer import TraceWriter, trace_path

DEFAULT_HOST = "http://localhost:11434"
TRACE_DIRECTORY = Path("traces")


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="local_coding_agent",
        description="ローカル LLM で動くコーディングエージェント",
    )
    parser.add_argument(
        "--model", required=True, help="Ollama のモデルの名前（例: qwen3.5:9b）"
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help=f"Ollama の URL（既定: {DEFAULT_HOST}）"
    )
    parser.add_argument(
        "--system-prompt-file",
        type=Path,
        help="指示の部分を、このファイルの中身に差し替える（環境の節は残る）",
    )
    parser.add_argument(
        "--debug",
        nargs="?",
        const="readable",
        choices=("readable", "raw"),
        help="Ollama の応答を全て表示する。値なし: 推論の文と、本文のほかの欄も出す。"
        "raw: 届いた行をそのまま出す",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        instructions = read_instructions(args.system_prompt_file)
    except (OSError, UnicodeDecodeError) as error:
        path = args.system_prompt_file
        sys.stderr.write(f"指示のファイルを読めない（{path}）: {error}\n")
        return 2
    environment = collect_environment(Path.cwd())
    system = build_system_prompt(instructions, environment_section(environment))
    trace = TraceWriter(trace_path(TRACE_DIRECTORY, datetime.now()))
    sys.stdout.write(f"走行の記録: {trace.path}\n")
    sys.stdout.write(f"指示: {args.system_prompt_file or '既定'}\n")
    session = repl.Session(
        model=OllamaChat(host=args.host, model=args.model),
        system=system,
        read_line=input,
        output=sys.stdout,
        trace=trace,
        clock=time.monotonic,
        now=local_now,
        display=repl.Display(color=sys.stdout.isatty(), debug=args.debug or "off"),
    )
    repl.run(session)
    return 0


def local_now() -> datetime:
    """今の時刻を、この機械の時差つきで返す。"""
    return datetime.now().astimezone()


if __name__ == "__main__":
    raise SystemExit(main())
