"""起動: python -m local_coding_agent --model <モデルのタグ> [--host <URL>]"""

import argparse
import sys
import time
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from local_coding_agent.cli import repl
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    trace = TraceWriter(trace_path(TRACE_DIRECTORY, datetime.now()))
    sys.stdout.write(f"走行の記録: {trace.path}\n")
    session = repl.Session(
        model=OllamaChat(host=args.host, model=args.model),
        read_line=input,
        output=sys.stdout,
        trace=trace,
        clock=time.monotonic,
    )
    repl.run(session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
