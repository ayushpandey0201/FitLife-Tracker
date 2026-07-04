"""Password hashing using Argon2id.

Argon2id is the current OWASP-recommended password hashing algorithm (memory-hard,
resistant to GPU/ASIC attacks). We use ``argon2-cffi`` with its secure defaults.
A single module-level :class:`PasswordHasher` is reused (it is stateless and
thread-safe); its parameters are embedded in every hash, so they can be tuned
later without breaking existing hashes.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    """Return an Argon2id hash (including salt and parameters) for a password."""
    return _hasher.hash(plain_password)


def verify_password(hashed_password: str, plain_password: str) -> bool:
    """Return whether ``plain_password`` matches ``hashed_password``.

    Never raises for an ordinary mismatch or a malformed stored hash — callers
    get a plain ``False`` so authentication logic stays a simple boolean check.
    """
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Return True if the stored hash was made with outdated parameters.

    Lets callers transparently upgrade a user's hash (with the current cost
    parameters) on their next successful login.
    """
    return _hasher.check_needs_rehash(hashed_password)
