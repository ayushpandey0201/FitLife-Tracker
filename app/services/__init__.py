"""Application services — business logic and orchestration.

Services coordinate repositories, the domain engine, and security primitives to
fulfil a use case (register a user, generate and persist a plan, ...). They own
transactions conceptually but receive an already-scoped session, contain no HTTP
concerns, and raise typed :mod:`app.services.exceptions` that the API layer maps
to status codes. Routes call services; services call repositories.
"""
