import json
import logging
import time

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"

# Fewer retries than image analysis: the user is waiting in real time, and a
# fallback answer already exists, so a slow retry is worse than degrading.
MAX_RETRIES = 1
REQUEST_TIMEOUT_SECONDS = 15

SYSTEM_PROMPT = """You are a personal stylist choosing between outfits that a scoring engine has already shortlisted.

Rules:
- Choose exactly one outfit from the candidates by its index.
- Write one short reason for every candidate, including the ones you did not choose.
- The scores are for your judgement only. Never mention scores, numbers or rankings in a reason; explain in terms of the garments, their colors, the weather and the occasion.
- Base every reason only on the attributes provided: category, color, style, warmth level and description. Do not invent fabrics, brands, fits or any detail that is not given.
- Give one short practical tip about the weather that does not require clothing the user may not own.

Return ONLY a JSON object in this shape:
{"recommended_index": <int>, "outfits": [{"index": <int>, "reason": "<string>"}], "tips": "<string>"}"""

def _get_client() -> OpenAI | None:
    """Return a client, or None if no key is configured (which triggers the fallback)."""
    if not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def _describe_garment(item: dict) -> str:
    text = f"{item['category']}: {item['color']} ({item['style']}, warmth {item['warmth_level']}/5)"
    if item.get("description"):
        text += f" - {item['description']}"
    return text


def build_user_prompt(candidates: list[dict], items_by_id: dict, weather: dict, occasion: str) -> str:
    """Describe the weather, occasion and each shortlisted outfit in plain text."""
    condition = weather.get("description") or weather.get("condition", "")
    lines = [
        f"Weather: {weather['temp_celsius']}°C, {condition}",
        f"Occasion: {occasion}",
        "",
        "Candidates (scores are 0 to 1):",
    ]
    for index, outfit in enumerate(candidates):
        lines.append(
            f"[{index}] total {outfit['total']:.2f} | temperature {outfit['temperature']:.2f} | "
            f"occasion {outfit['occasion']:.2f} | color {outfit['color']:.2f}"
        )
        for item_id in outfit["item_ids"]:
            lines.append(f"    - {_describe_garment(items_by_id[item_id])}")
    return "\n".join(lines)


def _parse_response(content: str, candidate_count: int) -> dict:
    """Validate the model's JSON. Raises ValueError if the choice itself is unusable.

    A missing or malformed reason for one outfit is tolerated: that outfit just gets
    no reason, rather than throwing away the whole answer.
    """
    data = json.loads(content)

    index = data.get("recommended_index")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < candidate_count:
        raise ValueError(f"recommended_index is not a valid choice: {index!r}")

    reasons: dict[int, str] = {}
    for entry in data.get("outfits") or []:
        if not isinstance(entry, dict):
            continue
        i, reason = entry.get("index"), entry.get("reason")
        if isinstance(i, int) and 0 <= i < candidate_count and isinstance(reason, str) and reason.strip():
            reasons[i] = reason.strip()

    tips = data.get("tips")
    tips = tips.strip() if isinstance(tips, str) and tips.strip() else None

    return {"recommended_index": index, "reasons": reasons, "tips": tips}


SCORE_FIELDS = ("total", "temperature", "occasion", "color")


def _present(outfit: dict) -> dict:
    """Round scores for display. Ranking already happened at full precision."""
    return {
        key: round(value, 2) if key in SCORE_FIELDS else value
        for key, value in outfit.items()
    }

def _assemble(
    candidates: list[dict],
    items_by_id: dict,
    recommended_index: int,
    reasons: dict[int, str],
    tips: str | None,
    source: str,
) -> dict:
    """Build the final response: every candidate with its garments and (maybe) a reason."""
    return {
        "recommended_index": recommended_index,
        "source": source,
        "tips": tips,
        "outfits": [
            {
                **_present(outfit),
                "items": [items_by_id[item_id] for item_id in outfit["item_ids"]],
                "reason": reasons.get(index),
            }
            for index, outfit in enumerate(candidates)
        ],
    }


def recommend_outfit(candidates: list[dict], items_by_id: dict, weather: dict, occasion: str) -> dict:
    """Ask the LLM to pick one of the shortlisted outfits and explain every option.

    Never fails because of the LLM: on any problem it falls back to the scoring
    engine's own ranking, with source set to "fallback" and no reasons.
    """
    if not candidates:
        raise ValueError("No candidates to choose from")

    fallback = _assemble(candidates, items_by_id, 0, {}, None, "fallback")

    client = _get_client()
    if client is None:
        logger.warning("OPENAI_API_KEY not configured; returning scoring-engine ranking only")
        return fallback

    prompt = build_user_prompt(candidates, items_by_id, weather, occasion)

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=500,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            parsed = _parse_response(response.choices[0].message.content or "", len(candidates))
            return _assemble(
                candidates, items_by_id,
                parsed["recommended_index"], parsed["reasons"], parsed["tips"], "llm",
            )
        except Exception as error:
            logger.warning("Recommendation attempt %d failed: %s", attempt + 1, error)
            if attempt < MAX_RETRIES:
                time.sleep(1)

    return fallback