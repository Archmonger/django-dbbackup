"""Cross-platform console symbol selection for live test scripts.

Detects whether the active stdout encoding can represent a small set of
Unicode emoji used for nicer test status output. Falls back to plain ASCII
strings when running in limited code pages (e.g. Windows cp1252 on some
GitHub Actions runners) to avoid UnicodeEncodeError crashes.

Usage:
    from scripts._symbols import get_symbols
    SYMS = get_symbols()
    print(SYMS['PASS'], 'Test passed')

Provided symbol keys:
    PASS, FAIL, SUMMARY, TEST, PG

The ``PG`` key is only used by the PostgreSQL live test; others are shared.
"""

from __future__ import annotations

import sys
from typing import Dict

_EMOJI_SYMBOLS = {
    "PASS": "✅",
    "FAIL": "❌",
    "SUMMARY": "📊",
    "TEST": "📋",
    "PG": "🐘",
}

_ASCII_SYMBOLS = {
    "PASS": "PASS:",
    "FAIL": "FAIL:",
    "SUMMARY": "SUMMARY:",
    "TEST": "TEST:",
    "PG": ">>",
}


def _can_encode(sample: str) -> bool:
    """Return True if current stdout encoding can represent ``sample``."""
    encoding = getattr(sys.stdout, "encoding", None) or ""
    if not encoding:
        return False
    try:
        sample.encode(encoding)
        return True
    except Exception:  # pragma: no cover - defensive
        return False


def get_symbols() -> Dict[str, str]:  # noqa: D401 - short descriptive name
    """Return mapping of symbol names to appropriate (emoji or ASCII) strings."""
    if all(_can_encode(sym) for sym in _EMOJI_SYMBOLS.values()):
        return _EMOJI_SYMBOLS
    return _ASCII_SYMBOLS


__all__ = ["get_symbols"]
