"""起動: python -m local_coding_agent --model <モデルのタグ> [--host <URL>]
[--system-prompt-file <パス>] [--show-thinking] [--permission-mode <モード>]
[--directory <パス>]
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
from local_coding_agent.loop.session import Session
from local_coding_agent.model.ollama import OllamaChat
from local_coding_agent.permissions.policy import MODES
from local_coding_agent.permissions.settings import (
    SETTINGS_PATH,
    LoadedPermissions,
    SettingsError,
    describe,
    load_permissions,
    trace_record,
)
from local_coding_agent.skills.catalog import (
    SkillCatalog,
    describe_skills,
    discover_skills,
    skills_record,
    skills_section,
)
from local_coding_agent.tools.default import DEFAULT_TOOLS
from local_coding_agent.tools.load_skill import load_skill_tool
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
        "--show-thinking",
        action="store_true",
        help="推論の文を表示する（付けなくても、走行の記録には残る）",
    )
    parser.add_argument(
        "--permission-mode",
        choices=MODES,
        help=f"許可のモード。設定ファイル（{SETTINGS_PATH}）のモードを上書きする",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        help="作業ディレクトリ（既定: 起動したディレクトリ）。設定ファイル・道具のパス・"
        "走行の記録は、ここを基にする",
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
    cwd = Path.cwd() if args.directory is None else args.directory.resolve()
    if not cwd.is_dir():
        message = f"作業ディレクトリにできない（{args.directory}）: ディレクトリが無い"
        sys.stderr.write(message + "\n")
        return 2
    skills = discover_skills(cwd)
    skill_tool = load_skill_tool(skills)
    try:
        home = Path.home()
        # load_skill の規則は、使えるスキルが無くても誤りにしない
        known = (*DEFAULT_TOOLS, skill_tool)
        loaded = load_permissions(cwd, known, home, args.permission_mode)
    except (SettingsError, RuntimeError) as error:
        # RuntimeError は、家のディレクトリが分からないとき（Path.home）
        sys.stderr.write(f"設定ファイルを読めない（{SETTINGS_PATH}）: {error}\n")
        return 2
    environment = collect_environment(cwd)
    system = build_system_prompt(
        instructions, environment_section(environment), skills_section(skills)
    )
    trace = _start_trace(args, loaded, skills)
    session = Session(
        model=OllamaChat(host=args.host, model=args.model),
        system=system,
        tools=(*DEFAULT_TOOLS, skill_tool) if skills.skills else DEFAULT_TOOLS,
        cwd=cwd,
        read_line=input,
        output=sys.stdout,
        trace=trace,
        clock=time.monotonic,
        now=local_now,
        permissions=loaded.permissions,
        show_thinking=args.show_thinking,
        skills=skills,
    )
    repl.run(session)
    return 0


def _start_trace(
    args: argparse.Namespace, loaded: LoadedPermissions, skills: SkillCatalog
) -> TraceWriter:
    """走行の記録を始め、起動のときの2件（許可とスキル）を書き、起動の行を出す。"""
    # 表示する行が短くなるよう、渡されたままのパスを基にする
    traces = (
        TRACE_DIRECTORY if args.directory is None else args.directory / TRACE_DIRECTORY
    )
    trace = TraceWriter(trace_path(traces, datetime.now()))
    trace.write(trace_record(loaded))
    trace.write(skills_record(skills))
    sys.stdout.write(f"走行の記録: {trace.path}\n")
    sys.stdout.write(f"指示: {args.system_prompt_file or '既定'}\n")
    sys.stdout.write(describe(loaded) + "\n")
    sys.stdout.write(describe_skills(skills) + "\n")
    sys.stdout.write("コマンド: /help で一覧\n")
    return trace


def local_now() -> datetime:
    """今の時刻を、この機械の時差つきで返す。"""
    return datetime.now().astimezone()


if __name__ == "__main__":
    raise SystemExit(main())
