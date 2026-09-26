import json
from unittest.mock import MagicMock, patch

import pytest

from app.recommender import build_user_prompt, recommend_outfit

WEATHER = {"temp_celsius": 21, "description": "few clouds"}

ITEMS = {
    1: {"id": 1, "category": "top", "color": "white", "style": "business",
        "warmth_level": 2, "description": "A plain button-up shirt"},
    2: {"id": 2, "category": "bottom", "color": "charcoal", "style": "business",
        "warmth_level": 3, "description": "Tailored trousers"},
    3: {"id": 3, "category": "shoes", "color": "black", "style": "business",
        "warmth_level": 3, "description": "Leather oxfords"},
    4: {"id": 4, "category": "shoes", "color": "white", "style": "sporty",
        "warmth_level": 2, "description": "Low-top sneakers"},
}

CANDIDATES = [
    {"item_ids": [1, 2, 3], "total": 0.92575, "temperature": 0.8525, "occasion": 1.0, "color": 0.85},
    {"item_ids": [1, 2, 4], "total": 0.62575, "temperature": 0.8525, "occasion": 0.4, "color": 0.85},
]

VALID_ANSWER = json.dumps({
    "recommended_index": 1,
    "outfits": [
        {"index": 0, "reason": "Sharp and office-ready."},
        {"index": 1, "reason": "Relaxed thanks to the sneakers."},
    ],
    "tips": "A mild day.",
})


def _mock_response(content: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    return response


def _client_returning(*contents: str) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.side_effect = [_mock_response(c) for c in contents]
    return client


# ---------- prompt ----------

def test_prompt_describes_weather_occasion_and_every_garment():
    prompt = build_user_prompt(CANDIDATES, ITEMS, WEATHER, "work")
    assert "21°C" in prompt and "few clouds" in prompt
    assert "Occasion: work" in prompt
    assert "[0]" in prompt and "[1]" in prompt
    assert "Leather oxfords" in prompt and "Low-top sneakers" in prompt


# ---------- successful answers ----------

@patch("app.recommender._get_client")
def test_valid_llm_answer_is_used(mock_get_client):
    mock_get_client.return_value = _client_returning(VALID_ANSWER)
    result = recommend_outfit(CANDIDATES, ITEMS, WEATHER, "work")

    assert result["source"] == "llm"
    assert result["recommended_index"] == 1
    assert result["tips"] == "A mild day."
    assert [o["reason"] for o in result["outfits"]] == [
        "Sharp and office-ready.",
        "Relaxed thanks to the sneakers.",
    ]


@patch("app.recommender._get_client")
def test_every_outfit_carries_its_garments(mock_get_client):
    mock_get_client.return_value = _client_returning(VALID_ANSWER)
    result = recommend_outfit(CANDIDATES, ITEMS, WEATHER, "work")
    assert [item["id"] for item in result["outfits"][0]["items"]] == [1, 2, 3]


@patch("app.recommender._get_client")
def test_missing_reason_for_one_outfit_is_tolerated(mock_get_client):
    partial = json.dumps({
        "recommended_index": 0,
        "outfits": [{"index": 0, "reason": "Good."}],
        "tips": "Mild.",
    })
    mock_get_client.return_value = _client_returning(partial)
    result = recommend_outfit(CANDIDATES, ITEMS, WEATHER, "work")

    assert result["source"] == "llm"
    assert result["outfits"][0]["reason"] == "Good."
    assert result["outfits"][1]["reason"] is None


@patch("app.recommender.time.sleep")
@patch("app.recommender._get_client")
def test_invalid_json_then_valid_answer_recovers(mock_get_client, _sleep):
    client = _client_returning("this is not json", VALID_ANSWER)
    mock_get_client.return_value = client

    result = recommend_outfit(CANDIDATES, ITEMS, WEATHER, "work")

    assert result["source"] == "llm"
    assert client.chat.completions.create.call_count == 2


# ---------- fallback ----------

@patch("app.recommender.time.sleep")
@patch("app.recommender._get_client")
def test_out_of_range_choice_falls_back(mock_get_client, _sleep):
    bad = json.dumps({"recommended_index": 5, "outfits": [], "tips": ""})
    client = _client_returning(bad, bad)
    mock_get_client.return_value = client

    result = recommend_outfit(CANDIDATES, ITEMS, WEATHER, "work")

    assert result["source"] == "fallback"
    assert result["recommended_index"] == 0
    assert all(o["reason"] is None for o in result["outfits"])
    assert client.chat.completions.create.call_count == 2


@patch("app.recommender.time.sleep")
@patch("app.recommender._get_client")
def test_boolean_choice_is_rejected(mock_get_client, _sleep):
    """In Python True == 1, so an unchecked bool would silently pick outfit 1."""
    bad = json.dumps({"recommended_index": True, "outfits": [], "tips": ""})
    mock_get_client.return_value = _client_returning(bad, bad)
    assert recommend_outfit(CANDIDATES, ITEMS, WEATHER, "work")["source"] == "fallback"


@patch("app.recommender.time.sleep")
@patch("app.recommender._get_client")
def test_api_error_falls_back(mock_get_client, _sleep):
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("OpenAI is down")
    mock_get_client.return_value = client

    result = recommend_outfit(CANDIDATES, ITEMS, WEATHER, "work")

    assert result["source"] == "fallback"
    assert client.chat.completions.create.call_count == 2


@patch("app.recommender._get_client", return_value=None)
def test_missing_api_key_falls_back(_):
    assert recommend_outfit(CANDIDATES, ITEMS, WEATHER, "work")["source"] == "fallback"


def test_empty_candidates_raises():
    with pytest.raises(ValueError):
        recommend_outfit([], ITEMS, WEATHER, "work")


# ---------- presentation ----------

@patch("app.recommender._get_client", return_value=None)
def test_scores_are_rounded_for_presentation(_):
    result = recommend_outfit(CANDIDATES, ITEMS, WEATHER, "work")
    assert result["outfits"][0]["temperature"] == 0.85