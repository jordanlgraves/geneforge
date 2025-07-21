from __future__ import annotations

"""Model client abstraction.

This module harmonises the *OpenAI* SDK with `art.TrainableModel` so the rest
of the codebase can interact with *either* backend via the same API surface
(i.e. ``client.chat.completions.create``).

The goal is **zero** changes in calling code – anything written for the
OpenAI SDK will work unchanged with a local *art* model once wrapped by the
appropriate adapter.
"""

from typing import Any, Callable, Optional

# Try importing art – we only need it when running locally
try:
    import art  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – CI environment may not have art
    art = None  # type: ignore

from openai import OpenAI  # type: ignore

__all__ = [
    "BaseModelClient",
    "OpenAIModelClient",
    "ArtModelClient",
]


class _CompletionWrapper:
    """Drop-in replacement for ``openai.chat.completions`` sub-object."""

    def __init__(self, create_fn: Callable[..., Any]):
        self._create_fn = create_fn

    def create(self, *args, **kwargs):  # noqa: D401 – mimic SDK signature
        """Proxy to the backend ``create`` implementation."""
        return self._create_fn(*args, **kwargs)


class _ChatWrapper:
    """Mimics the ``openai.chat`` namespace."""

    def __init__(self, create_fn: Callable[..., Any]):
        self.completions = _CompletionWrapper(create_fn)


class BaseModelClient:
    """Common interface exposing ``client.chat.completions.create``."""

    def __init__(self, model_name: str):
        self._model_name = model_name

    @property
    def model_name(self) -> str:  # noqa: D401
        return self._model_name

    # The ``chat`` property must be provided by subclasses


class OpenAIModelClient(BaseModelClient):
    """Adapter around the official OpenAI SDK client."""

    def __init__(self, openai_client: OpenAI, model_name: str):
        super().__init__(model_name)
        self._openai = openai_client
        # Direct passthrough so we *exactly* mimic the SDK structure
        self.chat = self._openai.chat  # type: ignore[attr-defined]

    def __getattr__(self, item):
        """Delegate to underlying OpenAI client for convenience."""
        return getattr(self._openai, item)


class ArtModelClient(BaseModelClient):
    """Adapter for `art.TrainableModel`.

    The art library exposes ``model.openai_client()`` which already returns an
    OpenAI-compatible client.  We just need to wrap it so callers have easy
    access to the *original* model for training / checkpointing purposes.
    """

    def __init__(self, art_model: "art.TrainableModel"):
        if art is None:
            raise RuntimeError("'art' package not available in environment")

        self._art_model = art_model
        openai_like_client: OpenAI = art_model.openai_client()
        super().__init__(art_model.name)
        # Build wrappers so we expose the canonical ``chat.completions.create``
        self.chat = _ChatWrapper(openai_like_client.chat.completions.create)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Additional convenience
    # ------------------------------------------------------------------

    @property
    def art_model(self) -> "art.TrainableModel":  # noqa: D401
        """Access to the underlying *art* model (for training, etc.)."""
        return self._art_model 