"""Gemini adapter. Imported lazily so tests and evals run without the SDK or a key."""

from __future__ import annotations

import os
import re
import time
from typing import Any

from .agent import SYSTEM_PROMPT, Reply, ToolCall, Turn
from .tools import Toolbox

DEFAULT_MODEL = "gemini-2.5-flash"
MAX_RETRIES = 6


def _retry_delay(exc: Exception, attempt: int) -> float | None:
    """Seconds to wait before retrying a rate-limited or overloaded call, or None to give up."""
    code = getattr(exc, "code", None)
    if code not in (429, 500, 503):
        return None
    if code == 429 and "PerDay" in str(exc):
        return None  # daily quota: waiting a minute will not help
    match = re.search(r"retry in ([0-9.]+)s|'retryDelay': '([0-9.]+)s'", str(exc))
    if match:
        return float(match.group(1) or match.group(2)) + 1.0
    return min(60.0, 5.0 * 2**attempt)


_TYPE_MAP = {
    "object": "OBJECT",
    "string": "STRING",
    "array": "ARRAY",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
}


def _schema(types: Any, spec: dict[str, Any]) -> Any:
    kwargs: dict[str, Any] = {"type": getattr(types.Type, _TYPE_MAP[spec["type"]])}
    if "description" in spec:
        kwargs["description"] = spec["description"]
    if "properties" in spec:
        kwargs["properties"] = {k: _schema(types, v) for k, v in spec["properties"].items()}
    if "items" in spec:
        kwargs["items"] = _schema(types, spec["items"])
    if "required" in spec:
        kwargs["required"] = list(spec["required"])
    return types.Schema(**kwargs)


def tool_declarations(types: Any) -> Any:
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(name=s["name"], description=s["description"], parameters=_schema(types, s["parameters"]))
            for s in Toolbox.SPECS
        ]
    )


def to_contents(types: Any, transcript: list[Turn]) -> list[Any]:
    contents = []
    for turn in transcript:
        if turn.role == "user":
            contents.append(types.Content(role="user", parts=[types.Part(text=turn.text)]))
        elif turn.role == "model":
            parts = [types.Part(text=turn.text)] if turn.text else []
            parts += [
                types.Part(function_call=types.FunctionCall(name=c.name, args=c.args), thought_signature=c.signature)
                for c in turn.tool_calls
            ]
            contents.append(types.Content(role="model", parts=parts))
        else:
            parts = [
                types.Part(function_response=types.FunctionResponse(name=r.name, response={"result": r.output}))
                for r in turn.results
            ]
            contents.append(types.Content(role="user", parts=parts))
    return contents


def _tool_calls(response: Any) -> list[ToolCall]:
    """Function calls from the first candidate, keeping each part's thought signature.

    Gemini 3 models reject a follow-up request whose function-call parts lack the
    signature they were sent with, so it has to round-trip through the transcript.
    """
    candidates = getattr(response, "candidates", None) or []
    content = getattr(candidates[0], "content", None) if candidates else None
    calls = []
    for part in getattr(content, "parts", None) or []:
        fc = getattr(part, "function_call", None)
        if fc is None:
            continue
        calls.append(
            ToolCall(
                name=fc.name,
                args=dict(fc.args or {}),
                id=getattr(fc, "id", None),
                signature=getattr(part, "thought_signature", None),
            )
        )
    return calls


class GeminiModel:
    def __init__(self, model: str | None = None, api_key: str | None = None):
        from google import genai
        from google.genai import types

        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.types = types
        self.client = genai.Client(api_key=key)
        self.model = model or os.environ.get("FIXER_MODEL", DEFAULT_MODEL)
        # Free-tier keys allow a handful of requests per minute; space calls out.
        self.min_interval = float(os.environ.get("FIXER_MIN_INTERVAL_S", "0"))
        self._last_call = 0.0
        self.config = types.GenerateContentConfig(
            tools=[tool_declarations(types)],
            system_instruction=SYSTEM_PROMPT,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    def step(self, transcript: list[Turn]) -> Reply:
        response = self._generate(to_contents(self.types, transcript))
        calls = _tool_calls(response)
        text = ""
        if not calls:
            text = response.text or ""
        meta = response.usage_metadata
        usage = {}
        if meta is not None:
            usage = {"prompt_tokens": meta.prompt_token_count or 0, "output_tokens": meta.candidates_token_count or 0}
        return Reply(text=text, tool_calls=calls, usage=usage)

    def _generate(self, contents: list[Any]) -> Any:
        for attempt in range(MAX_RETRIES + 1):
            wait = self.min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
            try:
                return self.client.models.generate_content(model=self.model, contents=contents, config=self.config)
            except Exception as exc:  # google.genai.errors.APIError
                delay = _retry_delay(exc, attempt)
                if delay is None or attempt == MAX_RETRIES:
                    raise
                time.sleep(delay)
        raise AssertionError("unreachable")
