from unittest.mock import MagicMock, patch

import pytest
import requests

from app.weather_service import (
    CityNotFoundError,
    WeatherServiceError,
    _parse_weather,
    get_weather,
)


# ---------- _parse_weather ----------

def test_parse_weather_extracts_expected_fields():
    payload = {
        "name": "San Jose",
        "main": {"temp": 20.94, "feels_like": 20.61, "humidity": 57},
        "weather": [{"main": "Clouds", "description": "few clouds"}],
    }
    result = _parse_weather(payload, "San Jose")

    assert result["city"] == "San Jose"
    assert result["temp_celsius"] == 20.9
    assert result["humidity"] == 57
    assert result["condition"] == "Clouds"


def test_parse_weather_rounds_temperature():
    payload = {"main": {"temp": 18.666}, "weather": [{}]}
    assert _parse_weather(payload, "X")["temp_celsius"] == 18.7


def test_parse_weather_defaults_feels_like_to_temp():
    payload = {"main": {"temp": 15.0}, "weather": [{}]}
    assert _parse_weather(payload, "X")["feels_like_celsius"] == 15.0


def test_parse_weather_handles_missing_weather_list():
    payload = {"main": {"temp": 15.0}}
    assert _parse_weather(payload, "X")["condition"] == "Unknown"


def test_parse_weather_raises_when_temperature_missing():
    with pytest.raises(WeatherServiceError, match="missing temperature"):
        _parse_weather({"main": {}, "weather": [{}]}, "X")


# ---------- get_weather: input validation ----------

def test_get_weather_rejects_empty_city():
    with pytest.raises(WeatherServiceError, match="must not be empty"):
        get_weather("   ")


# ---------- get_weather: mocked HTTP ----------

def _mock_http(status_code: int, json_body: dict | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.json.return_value = json_body or {}
    return response


@patch("app.weather_service.requests.get")
def test_get_weather_returns_parsed_data(mock_get):
    mock_get.return_value = _mock_http(200, {
        "name": "Boston",
        "main": {"temp": 5.2, "feels_like": 2.0, "humidity": 80},
        "weather": [{"main": "Rain", "description": "light rain"}],
    })

    result = get_weather("Boston")

    assert result["city"] == "Boston"
    assert result["temp_celsius"] == 5.2
    assert result["condition"] == "Rain"


@patch("app.weather_service.requests.get")
def test_get_weather_requests_metric_units(mock_get):
    """Without units=metric the API returns Kelvin, which would break scoring."""
    mock_get.return_value = _mock_http(200, {
        "main": {"temp": 10.0}, "weather": [{}],
    })

    get_weather("Boston")

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["units"] == "metric"
    assert kwargs["params"]["q"] == "Boston"
    assert "timeout" in kwargs


@patch("app.weather_service.requests.get")
def test_get_weather_raises_city_not_found_on_404(mock_get):
    mock_get.return_value = _mock_http(404)

    with pytest.raises(CityNotFoundError):
        get_weather("Nonexistentville")


@patch("app.weather_service.requests.get")
def test_get_weather_raises_on_invalid_key(mock_get):
    mock_get.return_value = _mock_http(401)

    with pytest.raises(WeatherServiceError, match="invalid or not yet activated"):
        get_weather("Boston")


@patch("app.weather_service.requests.get")
def test_get_weather_raises_on_server_error(mock_get):
    mock_get.return_value = _mock_http(500)

    with pytest.raises(WeatherServiceError, match="500"):
        get_weather("Boston")


@patch("app.weather_service.requests.get")
def test_get_weather_wraps_network_failure(mock_get):
    mock_get.side_effect = requests.ConnectionError("network down")

    with pytest.raises(WeatherServiceError, match="Weather request failed"):
        get_weather("Boston")