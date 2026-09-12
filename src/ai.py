"""AI client for MiniMax M3 via the OpenAI SDK.

MiniMax exposes an OpenAI-compatible host at
`https://api.minimax.io/v1`. We use the official `openai` Python SDK
with `base_url` override; the model id is `MiniMax-M3`. Verified
2026-09-12 against https://platform.minimax.io/docs/api-reference/text-openai-api.

Errors are surfaced as `AIError` with a one-line message; raw SDK
exceptions never leak to the caller.
"""

from __future__ import annotations

import os
from typing import Optional

from openai import OpenAI

from .models import Task


BASE_URL = "https://api.minimax.io/v1"
DEFAULT_MODEL = "MiniMax-M3"


class AIError(RuntimeError):
    """Raised when the AI provider cannot fulfil a `plan` request."""


def _client(api_key: Optional[str]) -> OpenAI:
    key = api_key or os.environ.get("PDESK_MINIMAX_API_KEY") or os.environ.get("MINIMAX_API_KEY")
    if not key:
        raise AIError(
            "MiniMax API key missing. Set PDESK_MINIMAX_API_KEY in env "
            "or ~/.config/pdesk/pdesk.toml (MINIMAX_API_KEY=...)."
        )
    return OpenAI(base_url=BASE_URL, api_key=key)


SYSTEM_PROMPT = (
    "You are a planning assistant. Given a task title and description "
    "(which may contain URLs the user has gathered), produce a short, "
    "actionable plan: 3-7 concrete next steps. Reply in the same "
    "language as the task."
)


def plan(
    task: Task,
    *,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    timeout: float = 60.0,
) -> str:
    """Return a plan for `task` from MiniMax M3.

    Raises `AIError` on missing key, network failure, or non-2xx
    response. The caller is responsible for surfacing this to the UI.
    """
    client = _client(api_key)
    user_msg = f"Title: {task.title}\n\nDescription:\n{task.description}".strip()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=1.0,
            timeout=timeout,
        )
    except Exception as exc:
        raise AIError(f"MiniMax request failed: {exc}") from exc

    try:
        content = resp.choices[0].message.content
    except (AttributeError, IndexError, KeyError) as exc:
        raise AIError(f"MiniMax returned no content: {exc}") from exc

    if not content or not content.strip():
        raise AIError("MiniMax returned empty content")

    return content.strip()
