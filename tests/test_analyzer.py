import json
from unittest.mock import MagicMock, patch

import pytest

from app.clothing_analyzer import (
    ClothingAnalysisError,
    _normalize,
    analyze_clothing,
)


# ---------- _normalize: field coercion ----------

def test_normalize_accepts_valid_payload():
    result = _normalize({
        "category": "top",
        "color": "white",
        "hex_color": "#FFFFFF",
        "style": "casual",
        "warmth_level": 1,
        "description": "A shirt",
    })
    assert result["category"] == "top"
    assert result["warmth_level"] == 1
    assert result["hex_color"] == "#FFFFFF"


def test_normalize_rejects_unknown_category():
    result = _normalize({"category": "t-shirt"})
    assert result["category"] == "accessory"


def test_normalize_lowercases_and_strips_category():
    result = _normalize({"category": "  TOP  "})
    assert result["category"] == "top"


def test_normalize_rejects_unknown_style():
    result = _normalize({"style": "vintage"})
    assert result["style"] == "casual"


def test_normalize_clamps_warmth_level_above_range():
    assert _normalize({"warmth_level": 99})["warmth_level"] == 5


def test_normalize_clamps_warmth_level_below_range():
    assert _normalize({"warmth_level": 0})["warmth_level"] == 1


def test_normalize_accepts_numeric_string_warmth_level():
    assert _normalize({"warmth_level": "3"})["warmth_level"] == 3


def test_normalize_falls_back_on_non_numeric_warmth_level():
    assert _normalize({"warmth_level": "medium"})["warmth_level"] == 3


def test_normalize_falls_back_on_null_warmth_level():
    assert _normalize({"warmth_level": None})["warmth_level"] == 3


def test_normalize_rejects_hex_without_hash():
    assert _normalize({"hex_color": "FFFFFF"})["hex_color"] == "#000000"


def test_normalize_rejects_hex_with_wrong_length():
    assert _normalize({"hex_color": "#FFF"})["hex_color"] == "#000000"


def test_normalize_uppercases_hex():
    assert _normalize({"hex_color": "#f6eb61"})["hex_color"] == "#F6EB61"


def test_normalize_handles_empty_payload():
    result = _normalize({})
    assert result["category"] == "accessory"
    assert result["style"] == "casual"
    assert result["warmth_level"] == 3
    assert result["hex_color"] == "#000000"
    assert result["color"] == "unknown"


def test_normalize_returns_all_expected_keys():
    keys = set(_normalize({}).keys())
    assert keys == {
        "category", "color", "hex_color", "style", "warmth_level", "description",
    }


# ---------- analyze_clothing: file handling ----------

def test_analyze_rejects_missing_file():
    with pytest.raises(ClothingAnalysisError, match="Image not found"):
        analyze_clothing("does/not/exist.jpg")


def test_analyze_rejects_unsupported_format(tmp_path):
    bad_file = tmp_path / "notes.txt"
    bad_file.write_text("not an image")

    with pytest.raises(ClothingAnalysisError, match="Unsupported image format"):
        analyze_clothing(str(bad_file))


# ---------- analyze_clothing: mocked API behaviour ----------

@pytest.fixture
def fake_image(tmp_path):
    """A file with a valid image extension. Content does not matter when mocked."""
    path = tmp_path / "shirt.jpg"
    path.write_bytes(b"fake-image-bytes")
    return str(path)


def _mock_response(content: str) -> MagicMock:
    """Build an object shaped like the OpenAI SDK's response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    return response


@patch("app.clothing_analyzer._get_client")
def test_analyze_parses_successful_response(mock_get_client, fake_image):
    payload = {
        "category": "top",
        "color": "yellow",
        "hex_color": "#F6EB61",
        "style": "casual",
        "warmth_level": 2,
        "description": "A yellow polo shirt",
    }
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_response(json.dumps(payload))
    mock_get_client.return_value = client

    result = analyze_clothing(fake_image)

    assert result["category"] == "top"
    assert result["hex_color"] == "#F6EB61"
    assert result["warmth_level"] == 2
    assert client.chat.completions.create.call_count == 1


@patch("app.clothing_analyzer._get_client")
def test_analyze_normalizes_bad_values_from_model(mock_get_client, fake_image):
    """The model may ignore the prompt; the result must still be storable."""
    payload = {
        "category": "hoodie",
        "color": "grey",
        "hex_color": "808080",
        "style": "athleisure",
        "warmth_level": 12,
        "description": "A hoodie",
    }
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_response(json.dumps(payload))
    mock_get_client.return_value = client

    result = analyze_clothing(fake_image)

    assert result["category"] == "accessory"
    assert result["style"] == "casual"
    assert result["warmth_level"] == 5
    assert result["hex_color"] == "#000000"


@patch("app.clothing_analyzer.time.sleep")
@patch("app.clothing_analyzer._get_client")
def test_analyze_retries_on_invalid_json(mock_get_client, mock_sleep, fake_image):
    valid = json.dumps({"category": "top", "warmth_level": 1})
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _mock_response("this is not json"),
        _mock_response(valid),
    ]
    mock_get_client.return_value = client

    result = analyze_clothing(fake_image)

    assert result["category"] == "top"
    assert client.chat.completions.create.call_count == 2


@patch("app.clothing_analyzer.time.sleep")
@patch("app.clothing_analyzer._get_client")
def test_analyze_raises_after_exhausting_retries(mock_get_client, mock_sleep, fake_image):
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("API unavailable")
    mock_get_client.return_value = client

    with pytest.raises(ClothingAnalysisError, match="Analysis failed after retries"):
        analyze_clothing(fake_image)

    assert client.chat.completions.create.call_count == 3