import requests

from app.config import settings

WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
REQUEST_TIMEOUT_SECONDS = 10


class WeatherServiceError(Exception):
    """Raised when weather data cannot be retrieved."""


class CityNotFoundError(WeatherServiceError):
    """Raised when the city name is not recognized by the provider."""


def get_weather(city: str) -> dict:
    """Fetch current weather for a city.

    Returns temperature in Celsius along with a short condition label.
    """
    if not settings.weather_api_key:
        raise WeatherServiceError("WEATHER_API_KEY is not configured")

    city = city.strip()
    if not city:
        raise WeatherServiceError("City name must not be empty")

    try:
        response = requests.get(
            WEATHER_API_URL,
            params={
                "q": city,
                "appid": settings.weather_api_key,
                "units": "metric",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise WeatherServiceError(f"Weather request failed: {error}") from error

    if response.status_code == 404:
        raise CityNotFoundError(f"City not found: {city}")
    if response.status_code == 401:
        raise WeatherServiceError("Weather API key is invalid or not yet activated")
    if not response.ok:
        raise WeatherServiceError(
            f"Weather API returned {response.status_code}"
        )

    return _parse_weather(response.json(), city)


def _parse_weather(payload: dict, city: str) -> dict:
    """Extract the fields the scoring engine needs from the provider's response."""
    main = payload.get("main") or {}
    weather_list = payload.get("weather") or [{}]

    temp = main.get("temp")
    if temp is None:
        raise WeatherServiceError("Weather response is missing temperature")

    return {
        "city": payload.get("name") or city,
        "temp_celsius": round(float(temp), 1),
        "feels_like_celsius": round(float(main.get("feels_like", temp)), 1),
        "humidity": main.get("humidity"),
        "condition": weather_list[0].get("main", "Unknown"),
        "description": weather_list[0].get("description", ""),
    }