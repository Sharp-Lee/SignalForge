from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
from typing import Protocol


class LlmProviderError(RuntimeError):
    """Raised when Claude provider output cannot be trusted."""


class Completion(Protocol):
    def __call__(
        self,
        *,
        system: str,
        user: str,
        schema: dict,
        max_tokens: int,
        thinking: dict | None,
    ) -> dict:
        ...


@dataclass
class UsageRecord:
    model: str
    role: str
    stop_reason: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int


class AnthropicCompletion:
    def __init__(self, model: str = "claude-opus-4-8", client=None, base_url: str | None = None):
        self.model = model
        self._client = client
        self.base_url = base_url
        self.usage: list[UsageRecord] = []

    def __call__(
        self,
        *,
        system: str,
        user: str,
        schema: dict,
        max_tokens: int,
        thinking: dict | None,
    ) -> dict:
        started = time.monotonic()
        role = schema.get("title", "unknown")
        try:
            response = self._messages_create(system, user, schema, max_tokens, thinking)
        except Exception as exc:
            raise LlmProviderError(f"anthropic request failed: {exc}") from exc

        stop_reason = getattr(response, "stop_reason", None)
        latency_ms = int((time.monotonic() - started) * 1000)
        self.usage.append(
            UsageRecord(
                model=self.model,
                role=role,
                stop_reason=stop_reason,
                input_tokens=getattr(getattr(response, "usage", None), "input_tokens", None),
                output_tokens=getattr(getattr(response, "usage", None), "output_tokens", None),
                latency_ms=latency_ms,
            )
        )
        if stop_reason in {"refusal", "max_tokens"}:
            raise LlmProviderError(f"anthropic stopped with {stop_reason}")

        text = _first_text_block(response)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LlmProviderError(f"anthropic returned invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LlmProviderError("anthropic JSON output must be an object")
        return parsed

    def _messages_create(self, system: str, user: str, schema: dict, max_tokens: int, thinking: dict | None):
        client = self._get_client()
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "output_config": {"format": {"type": "json_schema", "schema": schema}},
        }
        if thinking is not None:
            kwargs["thinking"] = thinking
        return client.messages.create(**kwargs)

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"), base_url=self.base_url)
        return self._client


class OpenAICompatibleCompletion:
    def __init__(
        self,
        model: str,
        base_url: str,
        api_key_env: str = "OPENAI_API_KEY",
        json_mode: str = "schema",
        client=None,
    ):
        if json_mode not in {"schema", "object"}:
            raise ValueError("json_mode must be schema or object")
        self.model = model
        self.base_url = base_url
        self.api_key_env = api_key_env
        self.json_mode = json_mode
        self._client = client
        self.usage: list[UsageRecord] = []

    def __call__(
        self,
        *,
        system: str,
        user: str,
        schema: dict,
        max_tokens: int,
        thinking: dict | None,
    ) -> dict:
        started = time.monotonic()
        role = schema.get("title", "unknown")
        try:
            response = self._chat_completion(system, user, schema, max_tokens)
        except Exception as exc:
            raise LlmProviderError(f"openai-compat request failed: {exc}") from exc

        choice = _first_openai_choice(response)
        finish_reason = getattr(choice, "finish_reason", None)
        latency_ms = int((time.monotonic() - started) * 1000)
        usage = getattr(response, "usage", None)
        self.usage.append(
            UsageRecord(
                model=self.model,
                role=role,
                stop_reason=finish_reason,
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
                latency_ms=latency_ms,
            )
        )
        if finish_reason == "length":
            raise LlmProviderError("openai-compat stopped with length")
        if finish_reason == "content_filter":
            raise LlmProviderError("openai-compat stopped with content_filter")

        content = getattr(getattr(choice, "message", None), "content", None)
        if not isinstance(content, str):
            raise LlmProviderError("openai-compat response did not contain message content")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LlmProviderError(f"openai-compat returned invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LlmProviderError("openai-compat JSON output must be an object")
        return parsed

    def _chat_completion(self, system: str, user: str, schema: dict, max_tokens: int):
        client = self._get_client()
        request_user = user
        if self.json_mode == "schema":
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.get("title", "output"),
                    "schema": schema,
                    "strict": True,
                },
            }
        else:
            request_user = (
                f"{user}\n\nYou MUST respond with a JSON object conforming to this schema:\n"
                f"{json.dumps(schema, indent=2)}"
            )
            response_format = {"type": "json_object"}
        return client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": request_user},
            ],
            max_tokens=max_tokens,
            response_format=response_format,
        )

    def _get_client(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI(base_url=self.base_url, api_key=os.environ.get(self.api_key_env))
        return self._client


def _first_text_block(response) -> str:
    for block in getattr(response, "content", []) or []:
        block_type = getattr(block, "type", None)
        text = getattr(block, "text", None)
        if block_type == "text" and isinstance(text, str):
            return text
    raise LlmProviderError("anthropic response did not contain a text block")


def _first_openai_choice(response):
    choices = getattr(response, "choices", None)
    if not choices:
        raise LlmProviderError("openai-compat response did not contain choices")
    return choices[0]
