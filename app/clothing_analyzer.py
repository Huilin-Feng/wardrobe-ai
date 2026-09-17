import base64
import json
import time
from pathlib import Path

from openai import OpenAI

from app.config import settings

# Constrained vocabularies — the scoring engine groups items by these exact values,
# so a free-form label from the model would break it downstream.
VALID_CATEGORIES = {"top", "bottom", "outerwear", "shoes", "accessory"}
VALID_STYLES = {"casual", "business", "formal", "sporty", "streetwear"}

MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

ANALYSIS_PROMPT = """Analyze this clothing item and return ONLY a JSON object.

Required fields:
- category: exactly one of ["top", "bottom", "outerwear", "shoes", "accessory"]
- color: the dominant color as a short human-readable name (e.g. "navy blue")
- hex_color: the dominant color as a 7-character hex code (e.g. "#1E3A5F")
- style: exactly one of ["casual", "business", "formal", "sporty", "streetwear"]
- warmth_level: integer 1-5, where 1 is a thin summer garment and 5 is a heavy winter coat
- description: one short sentence describing the item

Return only the JSON object, no markdown fences and no commentary."""


class ClothingAnalysisError(Exception):
    """Raised when the image cannot be analyzed after retries."""


def _get_client() -> OpenAI:
    """Create an OpenAI client. Fails loudly if the key is missing."""
    if not settings.openai_api_key:
        raise ClothingAnalysisError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=settings.openai_api_key)


def _encode_image(image_path: str) -> tuple[str, str]:
    """Read an image from disk and return (base64_string, mime_type)."""
    path = Path(image_path)
    if not path.is_file():
        raise ClothingAnalysisError(f"Image not found: {image_path}")

    mime_type = MIME_TYPES.get(path.suffix.lower())
    if mime_type is None:
        raise ClothingAnalysisError(f"Unsupported image format: {path.suffix}")

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return encoded, mime_type


def _normalize(raw: dict) -> dict:
    """Coerce the model's output into values the database can safely store.

    The model usually obeys the prompt, but 'usually' is not 'always' — so every
    field gets checked and falls back to a safe default rather than propagating
    garbage into the database.
    """
    category = str(raw.get("category", "")).strip().lower()
    if category not in VALID_CATEGORIES:
        category = "accessory"

    style = str(raw.get("style", "")).strip().lower()
    if style not in VALID_STYLES:
        style = "casual"

    try:
        warmth_level = int(raw.get("warmth_level", 3))
    except (TypeError, ValueError):
        warmth_level = 3
    warmth_level = max(1, min(5, warmth_level))

    hex_color = str(raw.get("hex_color", "")).strip().upper()
    if not (len(hex_color) == 7 and hex_color.startswith("#")):
        hex_color = "#000000"

    return {
        "category": category,
        "color": str(raw.get("color", "unknown")).strip() or "unknown",
        "hex_color": hex_color,
        "style": style,
        "warmth_level": warmth_level,
        "description": str(raw.get("description", "")).strip(),
    }


def analyze_clothing(image_path: str, max_retries: int = 2) -> dict:
    """Send an image to the Vision API and return normalized clothing attributes.

    Raises ClothingAnalysisError if every attempt fails.
    """
    encoded, mime_type = _encode_image(image_path)
    client = _get_client()

    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": ANALYSIS_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{encoded}",
                                    "detail": "low",
                                },
                            },
                        ],
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=300,
            )

            content = response.choices[0].message.content or ""
            return _normalize(json.loads(content))

        except (json.JSONDecodeError, KeyError, IndexError, AttributeError) as error:
            last_error = error
        except Exception as error:
            last_error = error

        if attempt < max_retries:
            time.sleep(2 ** attempt)  # 1s, then 2s

    raise ClothingAnalysisError(f"Analysis failed after retries: {last_error}")