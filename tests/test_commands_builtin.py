import unittest
from dataclasses import replace

from local_coding_agent.cli.conversation import Conversation
from local_coding_agent.commands.builtin import (
    BUILTINS,
    CLEARED,
    context_line,
    find_builtin,
    help_text,
    run_builtin,
)
from local_coding_agent.commands.custom import Listed
from local_coding_agent.model.messages import (
    Message,
    ToolResultBlock,
    ToolUseBlock,
    assistant_message,
    assistant_text,
    tool_results,
    user_text,
)
from local_coding_agent.permissions.policy import Permissions
from local_coding_agent.permissions.rules import Rule
from tests.fakes import ScriptedModel, fake_session

USE = ToolUseBlock("c", "read_file", {"path": "a"})
HISTORY = (
    user_text("読んで"),
    assistant_message("", [USE]),
    tool_results([ToolResultBlock("c", "中身")]),
    assistant_text("読んだ"),
    user_text("ありがとう"),
    assistant_text("どういたしまして"),
)


def conversation(
    history: tuple[Message, ...] = (), turn: int = 0, input_tokens: int | None = None
) -> Conversation:
    session = fake_session(ScriptedModel([]))
    return Conversation(session, history, turn, input_tokens)


def run(
    name: str, target: Conversation, arguments: str = ""
) -> tuple[Conversation, str]:
    builtin = find_builtin(name)
    assert builtin is not None
    return run_builtin(builtin, target, arguments)


class FindBuiltinTest(unittest.TestCase):
    def test_names(self) -> None:
        self.assertEqual(
            [builtin.name for builtin in BUILTINS],
            ["help", "clear", "context", "mode", "exit"],
        )
        self.assertIsNone(find_builtin("fix"))


class ClearTest(unittest.TestCase):
    def test_empties_history_and_tokens_and_keeps_turn(self) -> None:
        before = conversation(history=HISTORY, turn=2, input_tokens=900)
        after, output = run("clear", before)
        self.assertEqual(after, replace(before, history=(), input_tokens=None))
        self.assertEqual(output, CLEARED)
        # 受けたものは書き換えない
        self.assertEqual(before.history, HISTORY)


class ContextTest(unittest.TestCase):
    def test_counts_kinds_of_messages_and_tokens(self) -> None:
        self.assertEqual(
            context_line(HISTORY, 1234),
            "[文脈] 発言 6（依頼 2・モデル 3・道具の結果 1）・最後の要求の入力 1234 トークン",
        )

    def test_empty(self) -> None:
        _, output = run("context", conversation())
        self.assertEqual(
            output,
            "[文脈] 発言 0（依頼 0・モデル 0・道具の結果 0）・最後の要求の入力 まだ無い",
        )

    def test_result_message_with_note_counts_as_result(self) -> None:
        # 止まった回の、知らせの本文が付いた道具の結果
        noted = tool_results([ToolResultBlock("c", "中身")])
        noted = replace(noted, content=(*noted.content, *user_text("止めた").content))
        self.assertIn("依頼 0・モデル 0・道具の結果 1", context_line((noted,), None))


class ModeTest(unittest.TestCase):
    def test_shows_mode_without_arguments(self) -> None:
        before = conversation()
        after, output = run("mode", before)
        self.assertIs(after, before)
        self.assertEqual(output, "許可のモード: ask")

    def test_changes_only_mode(self) -> None:
        rules = (Rule("run_command", "rm *", "run_command(rm *)"),)
        permissions = Permissions(mode="ask", deny=rules)
        before = conversation()
        before = replace(
            before, session=replace(before.session, permissions=permissions)
        )
        after, output = run("mode", before, "accept-edits")
        self.assertEqual(
            after.session.permissions, replace(permissions, mode="accept-edits")
        )
        self.assertEqual(output, "許可のモード: ask → accept-edits")
        self.assertEqual(before.session.permissions.mode, "ask")

    def test_unknown_mode_changes_nothing(self) -> None:
        before = conversation()
        after, output = run("mode", before, "default")
        self.assertIs(after, before)
        self.assertEqual(
            output,
            "誤り: 知らないモード: default（ask・accept-edits・allow-all のどれか）",
        )


class ExitTest(unittest.TestCase):
    def test_finishes(self) -> None:
        after, output = run("exit", conversation())
        self.assertTrue(after.finished)
        self.assertEqual(output, "")


class ArgumentsTest(unittest.TestCase):
    def test_commands_without_arguments_refuse_them(self) -> None:
        before = conversation(history=HISTORY)
        for name in ("help", "clear", "context", "exit"):
            with self.subTest(name=name):
                after, output = run(name, before, "x")
                self.assertIs(after, before)
                self.assertEqual(output, f"/{name} は引数を取らない")


class HelpTextTest(unittest.TestCase):
    def test_lists_builtin_and_custom_with_aligned_names(self) -> None:
        custom = (
            Listed("/explain", "説明する"),
            Listed("Fix.md", "", "名前に使えない字があるので呼べない"),
            Listed("/clear", "消す", "組み込みと同じ名前なので呼べない"),
        )
        lines = help_text(BUILTINS, custom).splitlines()
        self.assertEqual(lines[0], "組み込みのコマンド:")
        self.assertEqual(lines[1], "  /help     コマンドの一覧を出す")
        self.assertEqual(lines[6], "自作のコマンド（.local-coding-agent/commands/）:")
        self.assertEqual(
            lines[7:10],
            [
                "  /explain  説明する",
                "  Fix.md    （名前に使えない字があるので呼べない）",
                "  /clear    消す（組み込みと同じ名前なので呼べない）",
            ],
        )

    def test_without_custom(self) -> None:
        self.assertIn("/commands/）:\n  （無し）\n", help_text(BUILTINS, ()))

    def test_lists_skills_after_custom_with_names_aligned_across_all(self) -> None:
        skills = (
            Listed("/add-conversion", "変換を足す"),
            Listed("Foo/", "", "名前に使えない字があるので使えない"),
        )
        lines = help_text(BUILTINS, (Listed("/fix", "直す"),), skills).splitlines()
        self.assertEqual(lines[1], "  /help            コマンドの一覧を出す")
        self.assertEqual(
            lines[6:],
            [
                "自作のコマンド（.local-coding-agent/commands/）:",
                "  /fix             直す",
                "スキル（.local-coding-agent/skills/。/<名前> で呼ぶか、モデルが読み込む）:",
                "  /add-conversion  変換を足す",
                "  Foo/             （名前に使えない字があるので使えない）",
            ],
        )

    def test_without_skills(self) -> None:
        self.assertTrue(help_text(BUILTINS, ()).endswith("読み込む）:\n  （無し）"))


if __name__ == "__main__":
    unittest.main()
