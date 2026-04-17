import logging
import time
from collections.abc import Awaitable, Callable
from datetime import date
from pathlib import Path

from fastapi import Request
from starlette.responses import Response


def configure_logging() -> None:
    """Configure application logging for console and daily log file output.

    This creates a ``logs`` directory at the project root (if missing) and
    writes logs to ``logs/YYYY-MM-DD.log`` while preserving console logging.
    """
    project_root = Path(__file__).resolve().parents[2]
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / f"{date.today().isoformat()}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


logger = logging.getLogger("address_book")


async def log_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log each HTTP request with method, path, status code, and duration.

    Args:
        request: Incoming FastAPI request object.
        call_next: Middleware callback that forwards the request and returns
            the response.

    Returns:
        Response: The response returned by downstream middleware/route handler.
    """
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.2f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response
