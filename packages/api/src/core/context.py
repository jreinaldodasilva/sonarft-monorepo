"""
SonarFT API — Request context variables.
Centralised ContextVar for request ID, importable from any module
without creating circular imports with main.py.
"""
import contextvars

# Holds the current request ID for the duration of each HTTP request.
# Set by RequestIdMiddleware in main.py; readable from any coroutine.
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)
