"""Security primitives: password hashing and JWT token handling.

Isolated, dependency-light helpers with no knowledge of HTTP, the database, or
the domain. Services compose them; routes never call them directly. Keeping them
here makes the crypto choices (Argon2, JWT) swappable in one place.
"""
