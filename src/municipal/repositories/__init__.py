"""Repository pattern layer for Munici-Pal.

Provides abstract protocol interfaces and a resolve() helper that
transparently handles both sync (in-memory) and async (Postgres)
store returns.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Awaitable, TypeVar

T = TypeVar("T")


async def resolve(value: T | Awaitable[T]) -> T:
    """Await a value if it is a coroutine, otherwise return it directly.

    This allows route handlers to call store methods uniformly:
        result = await resolve(store.some_method(args))

    In-memory stores return plain values; Postgres repos return coroutines.
    """
    if inspect.isawaitable(value):
        return await value  # type: ignore[return-value]
    return value  # type: ignore[return-value]
