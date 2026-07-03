"""Catalogue loading (infrastructure).

Reading the bundled food/exercise data is I/O, so it lives outside the pure
``app.domain`` package. The domain functions receive already-loaded ``Food``
objects via dependency injection, keeping them testable without the filesystem.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.domain.meals import Food

# Repo-root/data — resolved relative to this file so it works from any CWD.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_FOODS_ADAPTER = TypeAdapter(list[Food])


class Exercise(BaseModel):
    """An exercise and its MET (metabolic equivalent) for energy estimates."""

    model_config = ConfigDict(frozen=True)

    name: str
    met: float = Field(gt=0)


_EXERCISES_ADAPTER = TypeAdapter(list[Exercise])


@lru_cache(maxsize=1)
def load_foods(path: Path | None = None) -> tuple[Food, ...]:
    """Load and validate the food catalogue. Cached after first read."""
    source = path or (DATA_DIR / "foods.json")
    return tuple(_FOODS_ADAPTER.validate_json(source.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def load_exercises(path: Path | None = None) -> tuple[Exercise, ...]:
    """Load and validate the exercise catalogue. Cached after first read."""
    source = path or (DATA_DIR / "exercises.json")
    return tuple(_EXERCISES_ADAPTER.validate_json(source.read_text(encoding="utf-8")))
