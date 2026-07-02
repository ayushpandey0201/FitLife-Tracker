"""FitLife Tracker application package.

The package follows Clean Architecture: ``app.domain`` holds the pure,
framework-agnostic business logic (no I/O, no database, no web framework).
Later phases add ``app.services``, ``app.db`` and ``app.api`` layers around it
without the domain ever depending on them.
"""

__version__ = "0.1.0"
