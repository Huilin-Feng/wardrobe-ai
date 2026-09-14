import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    """Provide a TestClient backed by a fresh in-memory database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_payload():
    """Valid request body for creating a clothing item."""
    return {
        "image_url": "uploads/white_tshirt.jpg",
        "category": "top",
        "color": "white",
        "style": "casual",
        "warmth_level": 1,
        "hex_color": "#FFFFFF",
        "description": "Plain white cotton T-shirt",
    }


# ---------- Health check ----------

def test_root_returns_ok(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ---------- Create ----------

def test_create_clothing_returns_201(client, sample_payload):
    response = client.post("/api/clothing", json=sample_payload)
    assert response.status_code == 201

    body = response.json()
    assert body["id"] is not None
    assert body["category"] == "top"
    assert body["color"] == "white"


def test_create_clothing_rejects_warmth_level_above_range(client, sample_payload):
    response = client.post(
        "/api/clothing", json={**sample_payload, "warmth_level": 99}
    )
    assert response.status_code == 422


def test_create_clothing_rejects_warmth_level_below_range(client, sample_payload):
    response = client.post(
        "/api/clothing", json={**sample_payload, "warmth_level": 0}
    )
    assert response.status_code == 422


def test_create_clothing_rejects_missing_required_field(client, sample_payload):
    payload = {k: v for k, v in sample_payload.items() if k != "category"}
    response = client.post("/api/clothing", json=payload)
    assert response.status_code == 422


def test_create_clothing_rejects_wrong_type(client, sample_payload):
    response = client.post(
        "/api/clothing", json={**sample_payload, "warmth_level": "hot"}
    )
    assert response.status_code == 422


# ---------- Read ----------

def test_list_clothing_empty_wardrobe(client):
    response = client.get("/api/clothing")
    assert response.status_code == 200
    assert response.json() == []


def test_list_clothing_returns_created_items(client, sample_payload):
    client.post("/api/clothing", json=sample_payload)
    client.post("/api/clothing", json=sample_payload)

    response = client.get("/api/clothing")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_clothing_filters_by_category(client, sample_payload):
    client.post("/api/clothing", json=sample_payload)
    client.post("/api/clothing", json={**sample_payload, "category": "bottom"})

    response = client.get("/api/clothing", params={"category": "bottom"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["category"] == "bottom"


def test_list_clothing_unknown_category_returns_empty(client, sample_payload):
    client.post("/api/clothing", json=sample_payload)

    response = client.get("/api/clothing", params={"category": "hat"})
    assert response.status_code == 200
    assert response.json() == []


def test_get_clothing_by_id(client, sample_payload):
    created = client.post("/api/clothing", json=sample_payload).json()

    response = client.get(f"/api/clothing/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_clothing_not_found_returns_404(client):
    response = client.get("/api/clothing/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Clothing item not found"


def test_count_endpoint(client, sample_payload):
    assert client.get("/api/clothing/count").json()["count"] == 0

    client.post("/api/clothing", json=sample_payload)
    client.post("/api/clothing", json=sample_payload)

    assert client.get("/api/clothing/count").json()["count"] == 2


# ---------- Delete ----------

def test_delete_clothing_returns_204(client, sample_payload):
    created = client.post("/api/clothing", json=sample_payload).json()

    response = client.delete(f"/api/clothing/{created['id']}")
    assert response.status_code == 204

    assert client.get(f"/api/clothing/{created['id']}").status_code == 404


def test_delete_nonexistent_returns_404(client):
    response = client.delete("/api/clothing/9999")
    assert response.status_code == 404


# ---------- Upload ----------

def test_upload_rejects_unsupported_extension(client):
    response = client.post(
        "/api/clothing/upload",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400