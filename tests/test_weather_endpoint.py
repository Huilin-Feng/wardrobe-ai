"""Tests for GET /api/weather. The weather service itself is mocked."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.weather_service import CityNotFoundError, WeatherServiceError

client = TestClient(app)

SAMPLE = {
    "city": "Boston",
    "temp_celsius": 5.2,
    "feels_like_celsius": 2.0,
    "condition": "Rain",
}


@patch("app.main.get_weather", return_value=SAMPLE)
def test_weather_endpoint_returns_weather(mock_get):
    response = client.get("/api/weather", params={"city": "Boston"})

    assert response.status_code == 200
    assert response.json()["condition"] == "Rain"
    mock_get.assert_called_once_with("Boston")


@patch("app.main.get_weather", side_effect=CityNotFoundError("City not found: Atlantis"))
def test_weather_endpoint_unknown_city_is_404(mock_get):
    response = client.get("/api/weather", params={"city": "Atlantis"})

    assert response.status_code == 404
    assert "Atlantis" in response.json()["detail"]


@patch("app.main.get_weather", side_effect=WeatherServiceError("Weather API returned 500"))
def test_weather_endpoint_provider_failure_is_502(mock_get):
    response = client.get("/api/weather", params={"city": "Boston"})

    assert response.status_code == 502


def test_weather_endpoint_requires_city():
    response = client.get("/api/weather")

    assert response.status_code == 422


@patch("app.main.get_weather")
def test_weather_endpoint_rejects_blank_city(mock_get):
    response = client.get("/api/weather", params={"city": "   "})

    assert response.status_code == 400
    mock_get.assert_not_called()
