import os
import time
from typing import AsyncIterator

import anthropic

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


def _get_client() -> anthropic.AsyncAnthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
    return anthropic.AsyncAnthropic(api_key=api_key)


async def call_llm(
    messages: list[dict],
    system: str = "",
    tools: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
) -> anthropic.types.Message:
    """Send a request to Claude and return the full Message response.

    Supports tool_use blocks in the response — the caller inspects
    response.stop_reason and response.content to decide next steps.
    """
    client = _get_client()
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools

    for attempt in range(3):
        try:
            return await client.messages.create(**kwargs)
        except KeyboardInterrupt:
            raise
        except anthropic.APIConnectionError:
            if attempt == 2:
                raise
            time.sleep(0.5 * (2 ** attempt))
        except anthropic.RateLimitError:
            if attempt == 2:
                raise
            time.sleep(1.0 * (2 ** attempt))


async def call_llm_stream(
    messages: list[dict],
    system: str = "",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
) -> AsyncIterator[str]:
    """Stream text chunks from Claude. Does not support tool use."""
    client = _get_client()
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    for attempt in range(3):
        try:
            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
            return
        except KeyboardInterrupt:
            raise
        except (anthropic.APIConnectionError, anthropic.RateLimitError):
            if attempt == 2:
                raise
            time.sleep(0.5 * (2 ** attempt))
