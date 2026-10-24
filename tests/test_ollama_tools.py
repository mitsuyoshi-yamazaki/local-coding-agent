import io
import unittest

from local_coding_agent.model.chat import (
    Done,
    ModelError,
    TextDelta,
    ToolCall,
    ToolDefinition,
)
from local_coding_agent.model.messages import (
    Message,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    assistant_message,
    tool_results,
    user_text,
)
from local_coding_agent.model.ollama import read_stream
from local_coding_agent.model.ollama_messages import (
    chat_request_body,
    to_ollama_messages,
    to_ollama_tools,
)

READ = ToolDefinition(
    "read_file",
    "ファイルを読む",
    {"type": "object", "properties": {"path": {"type": "string"}}},
)
USE = ToolUseBlock(id="call_1", name="read_file", input={"path": "a.txt"})


def ndjson(*lines: str) -> io.BytesIO:
    return io.BytesIO("".join(line + "\n" for line in lines).encode())


class ToolDefinitionTest(unittest.TestCase):
    def test_input_schema_becomes_parameters(self) -> None:
        self.assertEqual(
            to_ollama_tools([READ]),
            [
                {
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "description": "ファイルを読む",
                        "parameters": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}},
                        },
                    },
                }
            ],
        )

    def test_request_body_has_tools(self) -> None:
        body = chat_request_body("m", "", [user_text("a")], [READ])
        self.assertEqual(body["tools"], to_ollama_tools([READ]))

    def test_request_body_without_tools_has_no_tools(self) -> None:
        self.assertNotIn("tools", chat_request_body("m", "", [user_text("a")], []))


class ToolBlocksTest(unittest.TestCase):
    def test_tool_use_becomes_tool_calls(self) -> None:
        second = ToolUseBlock(id="call_2", name="list_directory", input={})
        message = assistant_message("見る。", [USE, second])
        self.assertEqual(
            to_ollama_messages("", [message]),
            [
                {
                    "role": "assistant",
                    "content": "見る。",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "index": 0,
                                "name": "read_file",
                                "arguments": {"path": "a.txt"},
                            },
                        },
                        {
                            "id": "call_2",
                            "function": {
                                "index": 1,
                                "name": "list_directory",
                                "arguments": {},
                            },
                        },
                    ],
                }
            ],
        )

    def test_tool_use_without_text_has_empty_content(self) -> None:
        message = assistant_message("", [USE])
        self.assertEqual(message.content, (USE,))
        converted = to_ollama_messages("", [message])
        self.assertEqual(converted[0]["content"], "")

    def test_each_tool_result_becomes_tool_message_with_name(self) -> None:
        other = ToolUseBlock(id="call_2", name="list_directory", input={})
        messages = (
            assistant_message("", [USE, other]),
            tool_results(
                [
                    ToolResultBlock("call_1", "     1\tこんにちは"),
                    ToolResultBlock("call_2", "ディレクトリが無い: x", is_error=True),
                ]
            ),
        )
        self.assertEqual(
            to_ollama_messages("", messages)[1:],
            [
                {
                    "role": "tool",
                    "tool_name": "read_file",
                    "tool_call_id": "call_1",
                    "content": "     1\tこんにちは",
                },
                {
                    "role": "tool",
                    "tool_name": "list_directory",
                    "tool_call_id": "call_2",
                    "content": "誤り: ディレクトリが無い: x",
                },
            ],
        )

    def test_text_after_tool_results_becomes_user_message(self) -> None:
        message = Message(
            role="user",
            content=(ToolResultBlock("call_1", "結果"), TextBlock("続けて")),
        )
        converted = to_ollama_messages("", [assistant_message("", [USE]), message])
        self.assertEqual(
            [item["role"] for item in converted], ["assistant", "tool", "user"]
        )
        self.assertEqual(converted[2]["content"], "続けて")


class ReadToolCallsTest(unittest.TestCase):
    def test_reads_tool_calls_with_id(self) -> None:
        body = ndjson(
            '{"message": {"role": "assistant", "content": "",'
            ' "tool_calls": [{"id": "call_x", "function": {"index": 0,'
            ' "name": "read_file", "arguments": {"path": "a.txt"}}}]}, "done": false}',
            '{"message": {"content": ""}, "done": true, "done_reason": "stop"}',
        )
        self.assertEqual(
            list(read_stream(body)),
            [
                ToolCall(id="call_x", name="read_file", input={"path": "a.txt"}),
                Done(done_reason="stop"),
            ],
        )

    def test_tool_call_without_id(self) -> None:
        body = ndjson(
            '{"message": {"tool_calls": [{"function": {"name": "list_directory",'
            ' "arguments": {}}}]}, "done": true}',
        )
        self.assertEqual(
            next(read_stream(body)),
            ToolCall(id=None, name="list_directory", input={}),
        )

    def test_collects_text_and_calls_from_every_line(self) -> None:
        body = ndjson(
            '{"message": {"content": "見る。"}, "done": false}',
            '{"message": {"tool_calls": [{"function": {"name": "a",'
            ' "arguments": {}}}]}, "done": false}',
            '{"message": {"tool_calls": [{"function": {"name": "b",'
            ' "arguments": {}}}]}, "done": true}',
        )
        self.assertEqual(
            list(read_stream(body)),
            [
                TextDelta("見る。"),
                ToolCall(None, "a", {}),
                ToolCall(None, "b", {}),
                Done(done_reason=None),
            ],
        )

    def test_tool_calls_on_done_line(self) -> None:
        body = ndjson(
            '{"message": {"tool_calls": [{"function": {"name": "a",'
            ' "arguments": {}}}]}, "done": true, "done_reason": "stop"}',
        )
        self.assertEqual(
            list(read_stream(body)),
            [ToolCall(None, "a", {}), Done(done_reason="stop")],
        )

    def test_unreadable_tool_call_raises(self) -> None:
        for calls in (
            '"x"',
            '["x"]',
            '[{"function": {"arguments": {}}}]',
            '[{"function": {"name": "a", "arguments": "[1]"}}]',
        ):
            with self.subTest(calls=calls):
                body = ndjson(f'{{"message": {{"tool_calls": {calls}}}, "done": true}}')
                with self.assertRaises(ModelError):
                    list(read_stream(body))


if __name__ == "__main__":
    unittest.main()
