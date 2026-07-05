"""Recommendation endpoint: personalised, actionable guidance for the user.

A thin adapter over :class:`~app.services.recommendation_service.Recommendation
Service`. Requires a current profile (404 otherwise). The response is identical
whether guidance came from the default rule-based recommender or a future AI one
— that choice lives behind the service's injected :class:`Recommender` seam.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.services import RecommendationServiceDep
from app.schemas.recommendation import RecommendationOut

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get(
    "",
    response_model=list[RecommendationOut],
    summary="Personalised recommendations",
)
def get_recommendations(
    user: CurrentUser, recommendations: RecommendationServiceDep
) -> list[RecommendationOut]:
    """Return ordered recommendations from the user's profile, plan, and logs."""
    return recommendations.for_user(user.id)
