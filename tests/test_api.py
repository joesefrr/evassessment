from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import haversine_km
from app.db.base import Base
from app.db.session import get_db
from app.main import app


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_addresses.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base.metadata.create_all(bind=engine)


def override_get_db():
    """Provide an isolated test database session for dependency override."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


ADDRESS_PAYLOAD = {
    "label": "Home",
    "address_line_1": "123 Example St",
    "address_line_2": "Unit 4",
    "city": "Quezon City",
    "state": "Metro Manila",
    "postal_code": "1100",
    "country": "Philippines",
    "latitude": 14.651,
    "longitude": 121.049,
}


class FailingSession:
    """Test double that raises SQLAlchemy errors for selected operations."""

    def __init__(self, operation: str):
        self.operation = operation

    def add(self, _instance) -> None:
        return None

    def commit(self) -> None:
        if self.operation in {"create_commit", "update_commit", "delete_commit"}:
            raise SQLAlchemyError("database failure")

    def refresh(self, _instance) -> None:
        return None

    def rollback(self) -> None:
        return None

    def query(self, _model):
        if self.operation in {"list", "nearby"}:
            raise SQLAlchemyError("database failure")
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        return []

    def get(self, _model, _address_id):
        if self.operation == "get":
            raise SQLAlchemyError("database failure")
        return type("AddressObj", (), {})()

    def delete(self, _instance) -> None:
        return None

    def close(self) -> None:
        return None


def failing_db_override(operation: str):
    """Return a dependency override that yields a failing DB session."""

    def _override():
        db = FailingSession(operation)
        try:
            yield db
        finally:
            db.close()

    return _override


def test_create_and_get_address():
    """Verify that an address can be created and retrieved by ID."""
    create_response = client.post("/addresses", json=ADDRESS_PAYLOAD)
    assert create_response.status_code == 201
    address_id = create_response.json()["id"]

    get_response = client.get(f"/addresses/{address_id}")
    assert get_response.status_code == 200
    assert get_response.json()["label"] == "Home"


def test_nearby_search():
    """Verify nearby search returns addresses within the requested radius."""
    payload = {
        "label": "Office",
        "address_line_1": "456 Sample Ave",
        "address_line_2": None,
        "city": "Makati",
        "state": "Metro Manila",
        "postal_code": "1200",
        "country": "Philippines",
        "latitude": 14.5547,
        "longitude": 121.0244,
    }
    client.post("/addresses", json=payload)

    response = client.get(
        "/addresses/search/nearby",
        params={"latitude": 14.5547, "longitude": 121.0244, "distance_km": 1},
    )

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_create_address_failure_returns_500():
    """Verify create endpoint returns 500 when commit fails."""
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = failing_db_override("create_commit")

    try:
        response = client.post("/addresses", json=ADDRESS_PAYLOAD)
    finally:
        app.dependency_overrides[get_db] = previous_override

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to create address"


def test_list_addresses_failure_returns_500():
    """Verify list endpoint returns 500 when query fails."""
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = failing_db_override("list")

    try:
        response = client.get("/addresses")
    finally:
        app.dependency_overrides[get_db] = previous_override

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to list addresses"


def test_get_address_failure_returns_500():
    """Verify get endpoint returns 500 when DB read fails."""
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = failing_db_override("get")

    try:
        response = client.get("/addresses/1")
    finally:
        app.dependency_overrides[get_db] = previous_override

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to fetch address"


def test_update_address_failure_returns_500():
    """Verify update endpoint returns 500 when commit fails."""
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = failing_db_override("update_commit")

    try:
        response = client.put("/addresses/1", json=ADDRESS_PAYLOAD)
    finally:
        app.dependency_overrides[get_db] = previous_override

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to update address"


def test_delete_address_failure_returns_500():
    """Verify delete endpoint returns 500 when commit fails."""
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = failing_db_override("delete_commit")

    try:
        response = client.delete("/addresses/1")
    finally:
        app.dependency_overrides[get_db] = previous_override

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to delete address"


def test_nearby_search_failure_returns_500():
    """Verify nearby endpoint returns 500 when query fails."""
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = failing_db_override("nearby")

    try:
        response = client.get(
            "/addresses/search/nearby",
            params={"latitude": 14.5547, "longitude": 121.0244, "distance_km": 1},
        )
    finally:
        app.dependency_overrides[get_db] = previous_override

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to search nearby addresses"


def test_haversine_km_returns_expected_distance():
    """Verify Haversine distance for known coordinates is within tolerance."""
    distance = haversine_km(14.651, 121.049, 14.5547, 121.0244)

    assert distance == pytest.approx(11.03, abs=0.01)
