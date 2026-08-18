"""Domain errors raised by primer_core services and adapters."""

from __future__ import annotations


class KnowledgeBaseUnavailable(RuntimeError):
    """Knowledge-base retrieval could not produce a usable response."""
