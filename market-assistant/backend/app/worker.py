from collections.abc import Callable
from typing import Any

from app.ingest.backfill import backfill_gaps


class WorkerSettings:
    """Minimal arq task registration. Full arq worker wiring is deferred to deployment."""

    functions: list[Callable[..., Any]] = [backfill_gaps]
