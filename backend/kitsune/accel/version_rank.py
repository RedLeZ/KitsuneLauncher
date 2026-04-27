from __future__ import annotations

from functools import lru_cache

try:
    from numba import njit
except Exception:
    njit = None


@lru_cache(maxsize=1)
def _compiler_available() -> bool:
    return njit is not None


def _score_fallback(major: int, minor: int, patch: int) -> int:
    return major * 1_000_000 + minor * 1_000 + patch


if njit is not None:

    @njit(cache=True)
    def _score_numba(major: int, minor: int, patch: int) -> int:
        return major * 1_000_000 + minor * 1_000 + patch

else:
    _score_numba = None


def semantic_score(major: int, minor: int, patch: int) -> int:
    if _compiler_available() and _score_numba is not None:
        return int(_score_numba(major, minor, patch))
    return _score_fallback(major, minor, patch)
