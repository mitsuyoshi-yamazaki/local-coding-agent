"""会話の形（model/messages.py）と道具の定義を、送る直前に Ollama の /api/chat の形へ変える層。

| このリポジトリの形 | /api/chat の形 |
|---|---|
| system prompt | 先頭の、role が system の発言 |
| 道具の定義 | 要求の tools の1つ |
| モデルの発言の thinking の塊 | その発言の thinking |
| モデルの発言の tool_use の塊 | その発言の tool_calls の1つ |
| 利用者の発言の tool_result の塊 | role が tool の発言1つ |
| 発言のメタデータ（sent_at・command） | content の先頭の文 |
"""

from collections.abc import Sequence

from local_coding_agent.model.chat import ToolDefinition
from local_coding_agent.model.messages import (
    Message,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    metadata_text,
    text_of,
)

# 誤りの結果の content の先頭に付ける印。tool の発言には、Messages API の is_error にあたる欄が無い
ERROR_PREFIX = "誤り: "

type OllamaMessage = dict[str, object]


def chat_request_body(
    model: str,
    system: str,
    messages: Sequence[Message],
    tools: Sequence[ToolDefinition],
) -> dict[str, object]:
    """/api/chat へ送る JSON の全体を作る。道具の定義が無ければ tools を入れない。"""
    body: dict[str, object] = {
        "model": model,
        "messages": to_ollama_messages(system, messages),
        "stream": True,
    }
    return {**body, "tools": to_ollama_tools(tools)} if tools else body


def to_ollama_tools(tools: Sequence[ToolDefinition]) -> list[dict[str, object]]:
    """道具の定義を、/api/chat の tools に変える。input_schema は parameters になる。"""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": dict(tool.input_schema),
            },
        }
        for tool in tools
    ]


def to_ollama_messages(system: str, messages: Sequence[Message]) -> list[OllamaMessage]:
    """system prompt と会話を、/api/chat の messages に変える。

    /api/chat には system prompt の欄が無いので、先頭の system の発言にする（空なら入れない）。
    tool の発言は道具の名前を持つが、Messages API の結果の塊は持たないので、会話の中の
    呼び出しの塊から、id で名前を引く。
    """
    names = _tool_names(messages)
    head: list[OllamaMessage] = (
        [{"role": "system", "content": system}] if system else []
    )
    converted = (item for message in messages for item in _convert(message, names))
    return [*head, *converted]


def _tool_names(messages: Sequence[Message]) -> dict[str, str]:
    """呼び出しの id から、道具の名前を引く表。"""
    return {
        block.id: block.name
        for message in messages
        for block in message.content
        if isinstance(block, ToolUseBlock)
    }


def _convert(message: Message, names: dict[str, str]) -> list[OllamaMessage]:
    """1つの発言を、/api/chat の発言に変える。利用者の発言は、2つ以上になることがある。"""
    if message.role == "assistant":
        return [_assistant(message)]
    return _user(message, names)


def _assistant(message: Message) -> OllamaMessage:
    """モデルの発言。本文の塊は content に、推論の塊は thinking に、呼び出しの塊は tool_calls に入れる。

    推論は、Ollama の道具の呼び出しの文書の例と同じく、次の要求でモデルに戻す。
    """
    thinking = "".join(
        block.thinking for block in message.content if isinstance(block, ThinkingBlock)
    )
    uses = [block for block in message.content if isinstance(block, ToolUseBlock)]
    calls = [_tool_call(index, use) for index, use in enumerate(uses)]
    converted: OllamaMessage = {"role": "assistant", "content": _content(message)}
    with_thinking = {**converted, "thinking": thinking} if thinking else converted
    return {**with_thinking, "tool_calls": calls} if calls else with_thinking


def _tool_call(index: int, use: ToolUseBlock) -> dict[str, object]:
    function = {"index": index, "name": use.name, "arguments": dict(use.input)}
    return {"id": use.id, "function": function}


def _user(message: Message, names: dict[str, str]) -> list[OllamaMessage]:
    """利用者の発言。結果の塊は1つずつ tool の発言にし、本文があれば user の発言を後に置く。"""
    results = [
        _tool_message(block, names)
        for block in message.content
        if isinstance(block, ToolResultBlock)
    ]
    has_text = any(isinstance(block, TextBlock) for block in message.content)
    if results and not has_text:
        return results
    return [*results, {"role": "user", "content": _content(message)}]


def _tool_message(block: ToolResultBlock, names: dict[str, str]) -> OllamaMessage:
    mark = ERROR_PREFIX if block.is_error else ""
    return {
        "role": "tool",
        "tool_name": names.get(block.tool_use_id, ""),
        "tool_call_id": block.tool_use_id,
        "content": mark + block.content,
    }


def _content(message: Message) -> str:
    """メタデータの文と、本文の塊をつないだもの。"""
    return metadata_text(message) + text_of(message)
