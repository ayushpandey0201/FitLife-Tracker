"""HTTP API layer (FastAPI).

The outermost adapter: it translates HTTP requests into service calls and maps
service/domain exceptions to status codes. Routes stay thin — all business logic
lives in :mod:`app.services`. Nothing here is imported by inner layers.
"""
