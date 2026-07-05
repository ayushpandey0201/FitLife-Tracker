"""Recommendation response schema.

Reuses the domain :class:`~app.domain.recommendations.Recommendation` directly as
the HTTP contract (no duplication); aliased for an intent-revealing import.
"""

from __future__ import annotations

from app.domain.recommendations import Recommendation

RecommendationOut = Recommendation

__all__ = ["RecommendationOut"]
