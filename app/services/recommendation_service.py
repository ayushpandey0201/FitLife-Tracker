"""Recommendation service: assemble context and delegate to a recommender.

This is where the recommendation *seam* is wired. The service gathers everything
a recommender needs — the user's current profile, their (recomputed) plan
targets, today's tracking, and their weight trend — into a pure
:class:`RecommendationContext`, then hands it to an injected
:class:`~app.domain.recommendations.Recommender`. The default is the deterministic
:class:`RuleBasedRecommender`; swapping in an AI recommender is a one-line change
at construction (or via the API dependency) and touches nothing else.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain.nutrition import build_nutrition_plan
from app.domain.recommendations import (
    Recommendation,
    RecommendationContext,
    Recommender,
    RuleBasedRecommender,
)
from app.logging_config import get_logger
from app.repositories.profile_repository import SqlAlchemyProfileRepository
from app.services.exceptions import ProfileNotFoundError
from app.services.tracking_service import TrackingService

logger = get_logger(__name__)


class RecommendationService:
    """Use case: produce personalised recommendations for a user."""

    def __init__(self, session: Session, recommender: Recommender | None = None) -> None:
        self._profiles = SqlAlchemyProfileRepository(session)
        self._tracking = TrackingService(session)
        # Default to the transparent rule-based engine; an AI recommender can be
        # injected here (or overridden via the API dependency) with no other change.
        self._recommender: Recommender = recommender or RuleBasedRecommender()

    def for_user(self, user_id: int) -> list[Recommendation]:
        """Build the context for ``user_id`` and return ordered recommendations.

        Requires a current profile (the basis for plan targets); raises
        :class:`ProfileNotFoundError` if none exists.
        """
        current = self._profiles.get_current(user_id)
        if current is None:
            raise ProfileNotFoundError("a profile is required before recommendations can be made")

        today = datetime.now(UTC).date()
        context = RecommendationContext(
            profile=current.profile,
            plan=build_nutrition_plan(current.profile),
            today=self._tracking.daily_summary(user_id, today),
            weight_trend=self._tracking.weight_trend(user_id),
        )
        recs = self._recommender.recommend(context)
        logger.info("recommendations_built user_id=%d count=%d", user_id, len(recs))
        return recs
