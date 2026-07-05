"""Service-provider dependencies.

Construct the application services per request from the request-scoped session
(and settings, for auth). Keeping the wiring here means routers depend on a
service instance, not on how it is assembled — and tests can override a single
provider to swap in a fake.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.dependencies.auth import SessionDep, SettingsDep
from app.services.auth_service import AuthService
from app.services.plan_service import PlanService
from app.services.profile_service import ProfileService
from app.services.recommendation_service import RecommendationService
from app.services.tracking_service import TrackingService


def provide_auth_service(session: SessionDep, settings: SettingsDep) -> AuthService:
    """Build the :class:`AuthService` for this request."""
    return AuthService(session, settings)


def provide_profile_service(session: SessionDep) -> ProfileService:
    """Build the :class:`ProfileService` for this request."""
    return ProfileService(session)


def provide_plan_service(session: SessionDep) -> PlanService:
    """Build the :class:`PlanService` for this request."""
    return PlanService(session)


def provide_tracking_service(session: SessionDep) -> TrackingService:
    """Build the :class:`TrackingService` for this request."""
    return TrackingService(session)


def provide_recommendation_service(session: SessionDep) -> RecommendationService:
    """Build the :class:`RecommendationService` for this request.

    Uses the default rule-based recommender. To ship an AI recommender, override
    this provider in the app's ``dependency_overrides`` (or pass one here) — no
    router or service code changes.
    """
    return RecommendationService(session)


AuthServiceDep = Annotated[AuthService, Depends(provide_auth_service)]
ProfileServiceDep = Annotated[ProfileService, Depends(provide_profile_service)]
PlanServiceDep = Annotated[PlanService, Depends(provide_plan_service)]
TrackingServiceDep = Annotated[TrackingService, Depends(provide_tracking_service)]
RecommendationServiceDep = Annotated[RecommendationService, Depends(provide_recommendation_service)]
