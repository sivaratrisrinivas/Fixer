"""Gemini adapter. Imported lazily so tests and evals run without the SDK or a key."""

from __future__ import annotations

import os
from typing import Any

from .agent import SYSTEM_PROMPT, Reply, ToolCall, Turn
from .tools import Toolbox

DEFAULT_MODEL = "gemini-2.5-flash"

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
            parts += [types.Part(function_call=types.FunctionCall(name=c.name, args=c.args)) for c in turn.tool_calls]
            contents.append(types.Content(role="model", parts=parts))
        else:
            parts = [
                types.Part(function_response=types.FunctionResponse(name=r.name, response={"result": r.output}))
                for r in turn.results
            ]
            contents.append(types.Content(role="user", parts=parts))
    return contents


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
        self.config = types.GenerateContentConfig(
            tools=[tool_declarations(types)],
            system_instruction=SYSTEM_PROMPT,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    def step(self, transcript: list[Turn]) -> Reply:
        response = self.client.models.generate_content(
            model=self.model, contents=to_contents(self.types, transcript), config=self.config
        )
        calls = [
            ToolCall(name=fc.name, args=dict(fc.args or {}), id=getattr(fc, "id", None)) for fc in (response.function_calls or [])
        ]
        text = ""
        if not calls:
            text = response.text or ""
        meta = response.usage_metadata
        usage = {}
        if meta is not None:
            usage = {"prompt_tokens": meta.prompt_token_count or 0, "output_tokens": meta.candidates_token_count or 0}
        return Reply(text=text, tool_calls=calls, usage=usage)
