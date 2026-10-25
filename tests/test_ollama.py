import io
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from email.message import Message as Headers

from local_coding_agent.model.chat import Done, ModelError, TextDelta
from local_coding_agent.model.messages import (
    Message,
    TextBlock,
    assistant_text,
    user_text,
)
from local_coding_agent.model.ollama import (
    OllamaChat,
    http_error_message,
    read_stream,
)
from local_coding_agent.model.ollama_messages import (
    chat_request_body,
    to_ollama_messages,
)


def ndjson(*lines: str) -> io.BytesIO:
    """Ollama の応答の本体を真似た、NDJSON のバイト列。"""
    return io.BytesIO("".join(line + "\n" for line in lines).encode())


class ToOllamaMessagesTest(unittest.TestCase):
    def test_keeps_roles_and_order(self) -> None:
        messages = (
            user_text("こんにちは"),
            assistant_text("はい"),
            user_text("名前は？"),
        )
        self.assertEqual(
            to_ollama_messages("", messages),
            [
                {"role": "user", "content": "こんにちは"},
                {"role": "assistant", "content": "はい"},
                {"role": "user", "content": "名前は？"},
            ],
        )

    def test_joins_text_blocks(self) -> None:
        message = Message(
            role="user", content=(TextBlock("前半。"), TextBlock("後半。"))
        )
        self.assertEqual(
            to_ollama_messages("", [message]),
            [{"role": "user", "content": "前半。後半。"}],
        )

    def test_system_prompt_comes_first(self) -> None:
        self.assertEqual(
            to_ollama_messages("指示", [user_text("a")]),
            [
                {"role": "system", "content": "指示"},
                {"role": "user", "content": "a"},
            ],
        )

    def test_empty_system_prompt_is_not_sent(self) -> None:
        self.assertEqual(
            to_ollama_messages("", [user_text("a")]),
            [{"role": "user", "content": "a"}],
        )

    def test_metadata_comes_before_text(self) -> None:
        sent_at = datetime(2026, 10, 24, 15, 30, tzinfo=timezone(timedelta(hours=9)))
        messages = (user_text("今何時？", sent_at), assistant_text("15時半です"))
        self.assertEqual(
            to_ollama_messages("", messages),
            [
                {
                    "role": "user",
                    "content": "<metadata>\n送った時刻: 2026-10-24 15:30 (+09:00)\n"
                    "</metadata>\n今何時？",
                },
                {"role": "assistant", "content": "15時半です"},
            ],
        )

    def test_request_body_streams_whole_history(self) -> None:
        body = chat_request_body("qwen3.5:9b", "指示", [user_text("a")], [])
        self.assertEqual(
            body,
            {
                "model": "qwen3.5:9b",
                "messages": [
                    {"role": "system", "content": "指示"},
                    {"role": "user", "content": "a"},
                ],
                "stream": True,
            },
        )


class ReadStreamTest(unittest.TestCase):
    def test_text_deltas_then_done_with_stats(self) -> None:
        body = ndjson(
            '{"message": {"role": "assistant", "content": "こん"}, "done": false}',
            "",
            '{"message": {"role": "assistant", "content": "にちは"}, "done": false}',
            '{"message": {"role": "assistant", "content": ""}, "done": true,'
            ' "done_reason": "stop", "prompt_eval_count": 12, "eval_count": 3,'
            ' "total_duration": 4500000000}',
        )
        self.assertEqual(
            list(read_stream(body)),
            [
                TextDelta("こん"),
                TextDelta("にちは"),
                Done(
                    done_reason="stop",
                    stats={
                        "prompt_eval_count": 12,
                        "eval_count": 3,
                        "total_duration": 4500000000,
                    },
                ),
            ],
        )

    def test_done_without_stats(self) -> None:
        body = ndjson('{"message": {"content": "x"}, "done": true}')
        self.assertEqual(
            list(read_stream(body)), [TextDelta("x"), Done(done_reason=None, stats={})]
        )

    def test_error_line_raises(self) -> None:
        body = ndjson(
            '{"message": {"content": "途中"}, "done": false}',
            '{"error": "the model failed to generate a response"}',
        )
        events = read_stream(body)
        self.assertEqual(next(events), TextDelta("途中"))
        with self.assertRaisesRegex(ModelError, "failed to generate"):
            next(events)

    def test_non_object_line_raises(self) -> None:
        with self.assertRaises(ModelError):
            list(read_stream(ndjson("[1, 2]")))

    def test_broken_json_line_raises_model_error(self) -> None:
        body = ndjson(
            '{"message": {"content": "途中"}, "done": false}',
            '{"message": {"content": "切れ',
        )
        events = read_stream(body)
        self.assertEqual(next(events), TextDelta("途中"))
        with self.assertRaisesRegex(ModelError, "JSON として読めない"):
            next(events)


class HttpErrorMessageTest(unittest.TestCase):
    def test_reads_error_field(self) -> None:
        error = urllib.error.HTTPError(
            "http://localhost:11434/api/chat",
            404,
            "Not Found",
            Headers(),
            io.BytesIO(b'{"error": "model \\"x\\" not found"}'),
        )
        self.assertEqual(
            http_error_message(error),
            'Ollama が誤りを返した（404）: model "x" not found',
        )

    def test_falls_back_to_body_text(self) -> None:
        error = urllib.error.HTTPError(
            "http://localhost:11434/api/chat",
            500,
            "Internal Server Error",
            Headers(),
            io.BytesIO(b"oops"),
        )
        self.assertEqual(
            http_error_message(error), "Ollama が誤りを返した（500）: oops"
        )


class OllamaChatTest(unittest.TestCase):
    def test_builds_request_to_api_chat(self) -> None:
        chat = OllamaChat(host="http://localhost:11434/", model="gpt-oss:20b")
        request = chat.build_request("", [user_text("a")], [])
        self.assertEqual(request.url, "http://localhost:11434/api/chat")
        self.assertEqual(request.body["model"], "gpt-oss:20b")


if __name__ == "__main__":
    unittest.main()
