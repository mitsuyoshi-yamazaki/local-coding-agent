import unittest
from datetime import datetime, timedelta, timezone

from local_coding_agent.model.messages import assistant_text, metadata_text, user_text

JST = timezone(timedelta(hours=9))


class MetadataTextTest(unittest.TestCase):
    def test_sent_at_with_offset(self) -> None:
        sent_at = datetime(2026, 10, 24, 15, 30, 59, tzinfo=JST)
        self.assertEqual(
            metadata_text(user_text("今何時？", sent_at)),
            "<metadata>\n送った時刻: 2026-10-24 15:30 (+09:00)\n</metadata>\n",
        )

    def test_negative_offset(self) -> None:
        sent_at = datetime(2026, 10, 24, 1, 5, tzinfo=timezone(timedelta(hours=-3.5)))
        self.assertIn(
            "送った時刻: 2026-10-24 01:05 (-03:30)\n",
            metadata_text(user_text("a", sent_at)),
        )

    def test_command_comes_after_sent_at(self) -> None:
        sent_at = datetime(2026, 10, 24, 15, 30, tzinfo=JST)
        self.assertEqual(
            metadata_text(user_text("直せ: a.py", sent_at, command="/fix a.py")),
            "<metadata>\n送った時刻: 2026-10-24 15:30 (+09:00)\n"
            "コマンド: /fix a.py\n</metadata>\n",
        )

    def test_command_without_sent_at(self) -> None:
        self.assertEqual(
            metadata_text(user_text("a", command="/a")),
            "<metadata>\nコマンド: /a\n</metadata>\n",
        )

    def test_message_without_metadata_is_empty(self) -> None:
        self.assertEqual(metadata_text(user_text("a")), "")
        self.assertEqual(metadata_text(assistant_text("a")), "")

    def test_time_without_offset(self) -> None:
        sent_at = datetime(2026, 10, 24, 15, 30)
        self.assertIn(
            "送った時刻: 2026-10-24 15:30\n", metadata_text(user_text("a", sent_at))
        )


if __name__ == "__main__":
    unittest.main()
