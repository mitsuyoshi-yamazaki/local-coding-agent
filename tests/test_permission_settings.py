import json
import tempfile
import unittest
from pathlib import Path

from local_coding_agent.permissions.policy import Mode, Permissions
from local_coding_agent.permissions.settings import (
    SETTINGS_PATH,
    LoadedPermissions,
    SettingsError,
    describe,
    load_permissions,
    trace_record,
)
from local_coding_agent.tools.default import DEFAULT_TOOLS


class LoadPermissionsTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cwd = Path(directory.name).resolve()

    def write(self, value: object) -> None:
        path = self.cwd / SETTINGS_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        text = value if isinstance(value, str) else json.dumps(value)
        path.write_text(text, encoding="utf-8")

    def load(self, mode: Mode | None = None) -> LoadedPermissions:
        return load_permissions(self.cwd, DEFAULT_TOOLS, self.cwd, mode)

    def test_no_file_is_allow_all_without_rules(self) -> None:
        self.assertEqual(self.load(), LoadedPermissions(Permissions(), None))
        self.assertEqual(Permissions().mode, "allow-all")

    def test_valid_file(self) -> None:
        self.write(
            {
                "permissions": {
                    "mode": "accept-edits",
                    "allow": ["run_command(python3 -m unittest*)"],
                    "ask": ["run_command(git push *)"],
                    "deny": ["run_command(rm *)", "read_file(secret.txt)"],
                }
            }
        )
        loaded = self.load()
        self.assertEqual(loaded.source, SETTINGS_PATH)
        permissions = loaded.permissions
        self.assertEqual(permissions.mode, "accept-edits")
        self.assertEqual(
            [str(rule) for rule in permissions.deny],
            ["run_command(rm *)", "read_file(secret.txt)"],
        )
        self.assertEqual(permissions.deny[1].pattern, f"{self.cwd}/secret.txt")

    def test_every_field_may_be_left_out(self) -> None:
        values: tuple[dict[str, object], ...] = ({}, {"permissions": {}})
        for value in values:
            with self.subTest(value=value):
                self.write(value)
                self.assertEqual(self.load().permissions, Permissions())

    def test_mode_argument_overrides_file(self) -> None:
        self.write({"permissions": {"mode": "accept-edits", "deny": ["run_command"]}})
        permissions = self.load("ask").permissions
        self.assertEqual(permissions.mode, "ask")
        self.assertEqual(len(permissions.deny), 1)

    def test_mode_argument_without_file(self) -> None:
        self.assertEqual(self.load("ask"), LoadedPermissions(Permissions("ask"), None))

    def test_errors(self) -> None:
        for value, message in (
            ("{", "JSON として読めない"),
            ([], "設定ファイルの全体 は JSON のオブジェクトでなければならない"),
            ({"hooks": {}}, "設定ファイルの全体 に知らない欄がある: hooks"),
            ({"permissions": []}, "permissions は JSON のオブジェクト"),
            ({"permissions": {"defaultMode": "ask"}}, "知らない欄がある: defaultMode"),
            (
                {"permissions": {"mode": "default"}},
                'permissions.mode は ask・accept-edits・allow-all のどれか（受けた値: "default"）',
            ),
            ({"permissions": {"deny": "rm"}}, "permissions.deny は文字列の並び"),
            ({"permissions": {"allow": [1]}}, "permissions.allow は文字列の並び"),
            (
                {"permissions": {"deny": ["Bash(rm *)"]}},
                "permissions.deny: 知らない道具の名前: Bash",
            ),
            (
                {"permissions": {"ask": ["read_file()"]}},
                "permissions.ask: 型が空である",
            ),
        ):
            with self.subTest(value=value):
                self.write(value)
                with self.assertRaisesRegex(SettingsError, message):
                    self.load()

    def test_too_deep_or_too_long_json(self) -> None:
        for text in ("[" * 100_000, "1" * 5_000):
            with self.subTest(length=len(text)):
                self.write(text)
                with self.assertRaisesRegex(SettingsError, "JSON として読めない"):
                    self.load()

    def test_unreadable_file(self) -> None:
        (self.cwd / SETTINGS_PATH).mkdir(parents=True)
        with self.assertRaisesRegex(SettingsError, "読めない"):
            self.load()


class DescribeTest(unittest.TestCase):
    def test_line_and_record(self) -> None:
        rules = load_permissions(Path("/"), DEFAULT_TOOLS, Path("/"))
        self.assertEqual(describe(rules), "許可: allow-all・規則 0（設定ファイル無し）")
        self.assertEqual(
            trace_record(rules),
            {
                "type": "permissions",
                "mode": "allow-all",
                "source": None,
                "allow": [],
                "ask": [],
                "deny": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
