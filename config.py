"""Server-side limits and settings for the web service.

Every value is overridable via an environment variable so the caps can be tuned per
host without code changes. Defaults are conservative; they exist so an untrusted
client cannot exhaust the server with an oversized roster or an unbounded search.
"""

import os


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


# Reject uploads larger than this before parsing (bytes). Guards against memory
# blow-ups and zip-bomb-style .xlsx files.
MAX_UPLOAD_BYTES = _int_env("MAX_UPLOAD_BYTES", 5 * 1024 * 1024)  # 5 MB

# Caps on problem size.
MAX_EMPLOYEES = _int_env("MAX_EMPLOYEES", 2000)
MAX_TASKS = _int_env("MAX_TASKS", 50)

# Caps on the search itself.
MAX_SCHEDULES = _int_env("MAX_SCHEDULES", 50)
MAX_TIME_BUDGET_S = _float_env("MAX_TIME_BUDGET_S", 30.0)


def effective_time_budget(requested: float | None) -> float:
    """Clamp a client-requested budget to a hard server ceiling; never unbounded."""
    if requested is None or requested <= 0 or requested > MAX_TIME_BUDGET_S:
        return MAX_TIME_BUDGET_S
    return requested


def effective_max_schedules(requested: int) -> int:
    """Clamp the requested schedule count to the server maximum (and at least 1)."""
    return max(1, min(requested, MAX_SCHEDULES))


# Optional shared-secret gate. When API_KEY is set, /api/* requires a matching
# X-API-Key header; when unset, the API is open (local dev / deliberately public).
API_KEY = os.environ.get("API_KEY")

# CORS allowlist (comma-separated origins). Unset => "*" for local dev; set to the
# real frontend origin(s) in production.
def allowed_origins() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS")
    if not raw:
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
