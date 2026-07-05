"""Tests for the tracking domain and the TrackingService (Phase 5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.tracking import (
    ExerciseEntry,
    FoodEntry,
    LoggedExercise,
    LoggedFood,
    LoggedWater,
    LoggedWeight,
    WaterEntry,
    WeightEntry,
    build_weight_trend,
    calories_burned,
    summarise_day,
)
from app.services.auth_service import AuthService
from app.services.exceptions import (
    LogNotFoundError,
    ProfileNotFoundError,
    UnknownExerciseError,
)
from app.services.profile_service import ProfileService
from app.services.tracking_service import TrackingService
from sqlalchemy.orm import Session

from tests.test_nutrition import make_profile
from tests.test_services import _settings


def _dt(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=UTC)


# --- pure domain -----------------------------------------------------------
def test_calories_burned_met_formula() -> None:
    # Running (MET 9.8) for 30 min at 80 kg: 9.8 * 80 * 0.5 = 392.0
    assert calories_burned(met=9.8, weight_kg=80, duration_min=30) == 392.0


def test_summarise_day_sums_and_nets() -> None:
    foods = [
        LoggedFood(
            id=1,
            logged_at=_dt(4),
            name="Oats",
            calories_kcal=300,
            protein_g=10,
            carbs_g=50,
            fat_g=5,
        ),
        LoggedFood(
            id=2,
            logged_at=_dt(4),
            name="Chicken",
            calories_kcal=200,
            protein_g=40,
            carbs_g=0,
            fat_g=4,
        ),
    ]
    exercises = [
        LoggedExercise(
            id=1,
            logged_at=_dt(4),
            exercise="Running",
            duration_min=30,
            met=9.8,
            calories_burned_kcal=392.0,
        )
    ]
    waters = [LoggedWater(id=1, logged_at=_dt(4), volume_ml=500)]

    summary = summarise_day(_dt(4).date(), foods=foods, exercises=exercises, waters=waters)
    assert summary.calories_consumed_kcal == 500.0
    assert summary.calories_burned_kcal == 392.0
    assert summary.net_calories_kcal == 108.0
    assert summary.protein_g == 50.0
    assert summary.water_ml == 500.0
    assert summary.food_count == 2
    assert summary.exercise_count == 1


def test_summarise_empty_day_is_zeroed() -> None:
    summary = summarise_day(_dt(4).date(), foods=[], exercises=[], waters=[])
    assert summary.net_calories_kcal == 0.0
    assert summary.food_count == 0


def test_build_weight_trend_orders_and_diffs() -> None:
    # Deliberately out of order; trend must sort oldest -> newest.
    entries = [
        LoggedWeight(id=2, logged_at=_dt(3), weight_kg=79.0),
        LoggedWeight(id=1, logged_at=_dt(1), weight_kg=81.0),
        LoggedWeight(id=3, logged_at=_dt(5), weight_kg=78.0),
    ]
    trend = build_weight_trend(entries)
    assert [e.id for e in trend.entries] == [1, 2, 3]
    assert trend.start_kg == 81.0
    assert trend.latest_kg == 78.0
    assert trend.change_kg == -3.0


def test_build_weight_trend_empty() -> None:
    trend = build_weight_trend([])
    assert trend.entries == []
    assert trend.change_kg is None


# --- service ---------------------------------------------------------------
def _user_with_profile(
    session: Session, *, email: str = "t@example.com", weight_kg: float = 80.0
) -> int:
    """Register a user and give them a current profile; return the user id."""
    user = AuthService(session, _settings()).register(email=email, password="password123")
    ProfileService(session).create(user.id, make_profile(weight_kg=weight_kg))
    return user.id


def test_log_and_list_weight(db_session: Session) -> None:
    user_id = _user_with_profile(db_session)
    tracking = TrackingService(db_session)
    tracking.log_weight(user_id, WeightEntry(weight_kg=79.5, logged_at=_dt(1)))
    tracking.log_weight(user_id, WeightEntry(weight_kg=79.0, logged_at=_dt(2)))

    weights = tracking.list_weights(user_id)
    assert [w.weight_kg for w in weights] == [79.0, 79.5]  # newest first


def test_log_exercise_derives_calories_from_profile_weight(db_session: Session) -> None:
    user_id = _user_with_profile(db_session, weight_kg=80.0)
    tracking = TrackingService(db_session)
    logged = tracking.log_exercise(
        user_id,
        ExerciseEntry(exercise="running", duration_min=30),  # case-insensitive
    )
    assert logged.met == 9.8
    assert logged.calories_burned_kcal == 392.0


def test_log_exercise_requires_profile(db_session: Session) -> None:
    user = AuthService(db_session, _settings()).register(
        email="np@example.com", password="password123"
    )
    with pytest.raises(ProfileNotFoundError):
        TrackingService(db_session).log_exercise(
            user.id, ExerciseEntry(exercise="Running", duration_min=30)
        )


def test_log_exercise_unknown_name_rejected(db_session: Session) -> None:
    user_id = _user_with_profile(db_session)
    with pytest.raises(UnknownExerciseError):
        TrackingService(db_session).log_exercise(
            user_id, ExerciseEntry(exercise="Quidditch", duration_min=30)
        )


def test_delete_log_scoped_and_missing_raises(db_session: Session) -> None:
    user_id = _user_with_profile(db_session)
    tracking = TrackingService(db_session)
    logged = tracking.log_water(user_id, WaterEntry(volume_ml=500))
    tracking.delete_water(user_id, logged.id)  # succeeds
    with pytest.raises(LogNotFoundError):
        tracking.delete_water(user_id, logged.id)  # already gone


def test_daily_summary_buckets_by_utc_date(db_session: Session) -> None:
    user_id = _user_with_profile(db_session)
    tracking = TrackingService(db_session)
    # Two foods today, one yesterday — only today's should count.
    tracking.log_food(user_id, FoodEntry(name="A", calories_kcal=300, logged_at=_dt(4)))
    tracking.log_food(user_id, FoodEntry(name="B", calories_kcal=200, logged_at=_dt(4, 20)))
    tracking.log_food(user_id, FoodEntry(name="C", calories_kcal=999, logged_at=_dt(3)))
    tracking.log_water(user_id, WaterEntry(volume_ml=750, logged_at=_dt(4)))

    summary = tracking.daily_summary(user_id, _dt(4).date())
    assert summary.calories_consumed_kcal == 500.0
    assert summary.food_count == 2
    assert summary.water_ml == 750.0


def test_weight_trend_respects_date_range(db_session: Session) -> None:
    user_id = _user_with_profile(db_session)
    tracking = TrackingService(db_session)
    for day, kg in [(1, 82.0), (3, 80.0), (5, 78.0)]:
        tracking.log_weight(user_id, WeightEntry(weight_kg=kg, logged_at=_dt(day)))

    # Inclusive range [2, 4] captures only the day-3 entry.
    trend = tracking.weight_trend(user_id, start=_dt(2).date(), end=_dt(4).date())
    assert [e.weight_kg for e in trend.entries] == [80.0]
    assert trend.change_kg == 0.0

    # Full range spans the whole loss.
    full = tracking.weight_trend(user_id)
    assert full.start_kg == 82.0 and full.latest_kg == 78.0
    assert full.change_kg == -4.0


def test_logs_are_user_isolated(db_session: Session) -> None:
    a = _user_with_profile(db_session, email="a@example.com")
    b = _user_with_profile(db_session, email="b@example.com")
    tracking = TrackingService(db_session)
    tracking.log_water(a, WaterEntry(volume_ml=500))
    assert len(tracking.list_waters(a)) == 1
    assert tracking.list_waters(b) == []


def test_backdating_uses_supplied_timestamp(db_session: Session) -> None:
    user_id = _user_with_profile(db_session)
    past = datetime.now(UTC) - timedelta(days=10)
    logged = TrackingService(db_session).log_weight(
        user_id, WeightEntry(weight_kg=80, logged_at=past)
    )
    assert logged.logged_at == past
