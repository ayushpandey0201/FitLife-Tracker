"""Domain-level exception hierarchy.

Keeping domain errors distinct from framework errors (``pydantic.ValidationError``,
HTTP errors, DB errors) lets the outer layers translate them into the right
representation (HTTP 4xx, CLI message, ...) without leaking implementation
details.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all recoverable domain-rule violations."""


class InfeasibleGoalError(DomainError):
    """Raised when a weight goal cannot be met safely in the requested time.

    Example: losing 10 kg in 1 week would require a calorie deficit far below
    any safe intake floor.
    """


class NoEligibleFoodError(DomainError):
    """Raised when the food catalogue has no item matching the constraints."""
