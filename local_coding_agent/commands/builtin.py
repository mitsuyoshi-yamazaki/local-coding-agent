"""組み込みのコマンド。ハーネスの中で処理し、モデルは呼ばない。会話の履歴にも入らない。

どのコマンドも、REPL が持つもの（Conversation）と引数を受け、新しい Conversation と、
画面に出す文を返す。受けた Conversation は書き換えない。
"""

from collections.abc import Callable
from dataclasses import dataclass, replace

from local_coding_agent.cli.conversation import Conversation
from local_coding_agent.commands.custom import COMMANDS_PATH, Listed, list_custom
from local_coding_agent.model.messages import Message, ToolResultBlock
from local_coding_agent.permissions.policy import MODES, is_mode

CLEARED = "（会話を消した。次の依頼から新しい会話になる）"

type Handler = Callable[[Conversation, str], tuple[Conversation, str]]


@dataclass(frozen=True)
class Builtin:
    """組み込みのコマンド1つ。"""

    name: str
    # /help に出す説明
    description: str
    run: Handler
    # 引数を取るか。取らないコマンドに引数を付けたら、run を呼ばない
    takes_arguments: bool = False


def find_builtin(name: str) -> Builtin | None:
    return next((builtin for builtin in BUILTINS if builtin.name == name), None)


def run_builtin(
    builtin: Builtin, conversation: Conversation, arguments: str
) -> tuple[Conversation, str]:
    """組み込みのコマンドを行い、新しい Conversation と、画面に出す文を返す。"""
    if arguments and not builtin.takes_arguments:
        return conversation, f"/{builtin.name} は引数を取らない"
    return builtin.run(conversation, arguments)


def _help(conversation: Conversation, arguments: str) -> tuple[Conversation, str]:
    names = tuple(builtin.name for builtin in BUILTINS)
    custom = list_custom(conversation.session.cwd, names)
    return conversation, help_text(BUILTINS, custom)


def _clear(conversation: Conversation, arguments: str) -> tuple[Conversation, str]:
    return replace(conversation, history=(), input_tokens=None), CLEARED


def _context(conversation: Conversation, arguments: str) -> tuple[Conversation, str]:
    return conversation, context_line(conversation.history, conversation.input_tokens)


def _mode(conversation: Conversation, arguments: str) -> tuple[Conversation, str]:
    """引数が無ければ今のモードを出し、あればモードを替える。規則は変えない。"""
    session = conversation.session
    current = session.permissions.mode
    if not arguments:
        return conversation, f"許可のモード: {current}"
    if not is_mode(arguments):
        choices = "・".join(MODES)
        return conversation, f"誤り: 知らないモード: {arguments}（{choices} のどれか）"
    permissions = replace(session.permissions, mode=arguments)
    changed = replace(conversation, session=replace(session, permissions=permissions))
    return changed, f"許可のモード: {current} → {arguments}"


def _exit(conversation: Conversation, arguments: str) -> tuple[Conversation, str]:
    return replace(conversation, finished=True), ""


BUILTINS: tuple[Builtin, ...] = (
    Builtin("help", "コマンドの一覧を出す", _help),
    Builtin("clear", "会話の履歴を消し、新しい会話にする", _clear),
    Builtin(
        "context",
        "今の履歴の発言の数と、最後の要求の入力トークン数を出す",
        _context,
    ),
    Builtin(
        "mode",
        f"許可のモードを見る。/mode <モード> で変える（{'・'.join(MODES)}）",
        _mode,
        takes_arguments=True,
    ),
    Builtin("exit", "終える", _exit),
)


def help_text(builtins: tuple[Builtin, ...], custom: tuple[Listed, ...]) -> str:
    """/help の一覧。名前の列を揃える。"""
    labels = (*(f"/{builtin.name}" for builtin in builtins), *(c.label for c in custom))
    width = max(len(label) for label in labels)
    lines = (
        "組み込みのコマンド:",
        *(_row(f"/{b.name}", b.description, width) for b in builtins),
        f"自作のコマンド（{COMMANDS_PATH}/）:",
        *(_row(c.label, _with_problem(c), width) for c in custom),
        *(("  （無し）",) if not custom else ()),
    )
    return "\n".join(lines)


def _row(label: str, description: str, width: int) -> str:
    return f"  {label.ljust(width)}  {description}".rstrip()


def _with_problem(listed: Listed) -> str:
    if listed.problem is None:
        return listed.description
    return f"{listed.description}（{listed.problem}）"


def context_line(history: tuple[Message, ...], input_tokens: int | None) -> str:
    """/context の1行。依頼と道具の結果は、どちらも利用者の発言で、道具の結果を持つかで分ける。"""
    results = sum(1 for message in history if _has_results(message))
    replies = sum(1 for message in history if message.role == "assistant")
    requests = len(history) - results - replies
    tokens = "まだ無い" if input_tokens is None else f"{input_tokens} トークン"
    return (
        f"[文脈] 発言 {len(history)}"
        f"（依頼 {requests}・モデル {replies}・道具の結果 {results}）"
        f"・最後の要求の入力 {tokens}"
    )


def _has_results(message: Message) -> bool:
    return any(isinstance(block, ToolResultBlock) for block in message.content)
