from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings
from app.core.logging import configure_logging, log_requests
from app.db.base import Base
from app.db.session import engine
from app.models.address import Address  # noqa: F401

configure_logging()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Minimal FastAPI address book API with SQLite, validation, and nearby search.",
)

app.middleware("http")(log_requests)
app.include_router(router)


@app.get("/", tags=["health"])
def healthcheck() -> dict[str, str]:
    """Return a basic liveness response for service health checks."""
    return {"message": "Address Book API is running"}
