"""Canonical numeric formatting shared by every renderer (no per-format drift).

``format_number`` is the single source of a value's textual form; using it in all
renderers guarantees the same computed value renders byte-identically everywhere
(and identically to JSON's own float encoding, since both use the shortest repr).
"""

from __future__ import annotations

from veritas.contracts import ResultStatus, TracedValue

_STATUS_TEXT = {
    ResultStatus.INSUFFICIENT_CLEAN_DATA: "insufficient clean data",
    ResultStatus.UNDEFINED_METRIC: "undefined metric",
}


def format_number(value: float) -> str:
    """Shortest round-tripping decimal string (matches json's float encoding)."""
    return repr(float(value))


def render_value(traced: TracedValue) -> str:
    """A traced value's display: the canonical number, or its status spelled out."""
    if traced.value is not None:
        return format_number(traced.value)
    return _STATUS_TEXT[traced.status]


def md_escape(value: object) -> str:
    """Neutralize Markdown structure-breakers in interpolated text.

    The Markdown renderer is not auto-escaped (unlike HTML), so a benchmark name,
    detector name, or provenance ref containing ``|``, a backtick, or a newline could
    corrupt a table or heading. Escape pipes/backticks/backslashes and fold newlines
    to spaces; numbers and clean strings pass through unchanged.
    """
    text = str(value).replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")
    return text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
