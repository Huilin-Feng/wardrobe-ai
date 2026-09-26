import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from typing import get_args
from unittest.mock import patch

from app.models import Occasion
from app.scoring_engine import VALID_OCCASIONS
from app.weather_service import CityNotFoundError, WeatherServiceError


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

# ---------- Recommend ----------

FAKE_WEATHER = {
    "city": "San Jose",
    "temp_celsius": 21.0,
    "feels_like_celsius": 21.0,
    "humidity": 50,
    "condition": "Clouds",
    "description": "few clouds",
}


def _add_wardrobe(client, sample_payload, include_shoes=True):
    client.post("/api/clothing", json={**sample_payload, "category": "top"})
    client.post("/api/clothing", json={
        **sample_payload, "category": "bottom", "color": "navy", "hex_color": "#1E3A5F",
    })
    if include_shoes:
        client.post("/api/clothing", json={
            **sample_payload, "category": "shoes", "color": "black", "hex_color": "#000000",
        })


@patch("app.recommender._get_client", return_value=None)
@patch("app.main.get_weather", return_value=FAKE_WEATHER)
def test_recommend_returns_outfits(_weather, _llm, client, sample_payload):
    _add_wardrobe(client, sample_payload)

    response = client.post("/api/recommend", json={"city": "San Jose", "occasion": "casual"})

    assert response.status_code == 200
    body = response.json()
    assert body["weather"]["temp_celsius"] == 21.0
    assert body["recommended_index"] == 0
    assert body["source"] == "fallback"
    assert len(body["outfits"]) == 1


@patch("app.main.get_weather", return_value=FAKE_WEATHER)
def test_recommend_reports_missing_category(_weather, client, sample_payload):
    _add_wardrobe(client, sample_payload, include_shoes=False)

    response = client.post("/api/recommend", json={"city": "San Jose", "occasion": "casual"})

    assert response.status_code == 422
    assert response.json()["detail"]["missing"] == ["shoes"]


@patch("app.main.get_weather", side_effect=CityNotFoundError("City not found: Atlantis"))
def test_recommend_unknown_city_returns_404(_weather, client):
    response = client.post("/api/recommend", json={"city": "Atlantis", "occasion": "casual"})
    assert response.status_code == 404


@patch("app.main.get_weather", side_effect=WeatherServiceError("provider down"))
def test_recommend_weather_outage_returns_502(_weather, client):
    response = client.post("/api/recommend", json={"city": "San Jose", "occasion": "casual"})
    assert response.status_code == 502


def test_recommend_rejects_unknown_occasion(client):
    response = client.post("/api/recommend", json={"city": "San Jose", "occasion": "wedding"})
    assert response.status_code == 422


def test_api_occasions_match_scoring_engine():
    """The same list lives in models.py and scoring_engine.py; they must never drift."""
    assert set(get_args(Occasion)) == VALID_OCCASIONS