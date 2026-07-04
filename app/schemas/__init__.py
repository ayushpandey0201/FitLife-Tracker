"""API data-transfer schemas (request/response models).

Pydantic models that define the HTTP contract. They are separate from the ORM
models (persistence) and, where a suitable domain value object already exists
(e.g. :class:`app.domain.models.UserProfile`), it is reused directly rather than
duplicated. Response models never expose secrets (password hashes, token hashes).
"""
