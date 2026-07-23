"""Token counting via the Anthropic count_tokens API."""

from __future__ import annotations

import anthropic

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # Resolves ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, or an
        # `ant auth login` profile from the environment.
        _client = anthropic.Anthropic()
    return _client


def count_tokens(text: str, model: str) -> int:
    """Count tokens for `text` against `model` using the count_tokens endpoint."""
    if not text.strip():
        return 0
    resp = get_client().messages.count_tokens(
        model=model,
        messages=[{"role": "user", "content": text}],
    )
    return resp.input_tokens


def count_tokens_or_estimate(text: str, model: str) -> int:
    """count_tokens, falling back to a chars/4 estimate if the API is unreachable.

    Used on the hook path so a billing/network problem never loses a chat.
    """
    import anthropic

    try:
        return count_tokens(text, model)
    except anthropic.APIError:
        return max(1, len(text) // 4)
