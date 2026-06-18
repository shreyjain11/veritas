"""Veritas MCP server (optional ``mcp`` extra).

Deliberately imports nothing here: ``veritas.mcp.tools`` (pure handlers) must be
importable without the MCP SDK, which lives only in ``veritas.mcp.server``.
"""

from __future__ import annotations
