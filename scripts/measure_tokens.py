"""Compare prompt size: whole wardrobe sent to the LLM vs. the scoring-engine shortlist.

Run from the project root:  python -m scripts.measure_tokens
"""
import random

import tiktoken

from app.recommender import SYSTEM_PROMPT, _describe_garment, build_user_prompt
from app.scoring_engine import generate_outfit_candidates

# Written to be as detailed as the real SYSTEM_PROMPT, so the comparison is fair.
BASELINE_SYSTEM_PROMPT = """You are a personal stylist. From the wardrobe below, build the best outfit for the weather and occasion.

Rules:
- An outfit needs one top, one bottom and one pair of shoes; outerwear is optional.
- Consider the temperature, how well each garment's style suits the occasion, and whether the colors go together.
- Base your reasoning only on the attributes provided. Do not invent fabrics, brands, fits or any detail that is not given.
- Give one short practical tip about the weather.

Return ONLY a JSON object in this shape:
{"item_ids": [<int>, ...], "reason": "<string>", "tips": "<string>"}"""

COLORS = [
    ("white", "#FFFFFF"), ("black", "#000000"), ("navy", "#1E3A5F"),
    ("light yellow", "#F6EB61"), ("olive", "#708238"), ("burgundy", "#800020"),
    ("sky blue", "#3FA9F5"), ("beige", "#D8C3A5"), ("grey", "#808080"), ("coral", "#FF7F50"),
]
STYLES = ["casual", "business", "formal", "sporty", "streetwear"]
DESCRIPTIONS = {
    "top": ["A crew-neck T-shirt", "A button-up oxford shirt", "A cable-knit sweater", "A fitted polo shirt"],
    "bottom": ["Slim-fit jeans", "Tailored trousers", "Relaxed chinos", "Athletic joggers"],
    "shoes": ["Low-top sneakers", "Leather oxfords", "Suede loafers", "Running shoes"],
    "outerwear": ["A denim jacket", "A wool overcoat", "A quilted puffer jacket", "A trench coat"],
}
WARMTH_RANGE = {"top": (1, 4), "bottom": (2, 4), "shoes": (1, 4), "outerwear": (2, 5)}
CATEGORY_WEIGHTS = {"top": 4, "bottom": 3, "shoes": 2, "outerwear": 1}

WEATHER = {"temp_celsius": 18, "description": "clear sky"}
OCCASION = "casual"
WARDROBE_SIZES = [6, 10, 20, 30, 50, 100]


def make_garment(item_id: int, category: str, rng: random.Random) -> dict:
    color, hex_color = rng.choice(COLORS)
    low, high = WARMTH_RANGE[category]
    return {
        "id": item_id,
        "category": category,
        "color": color,
        "hex_color": hex_color,
        "style": rng.choice(STYLES),
        "warmth_level": rng.randint(low, high),
        "description": rng.choice(DESCRIPTIONS[category]),
    }


def make_wardrobe(size: int, seed: int) -> list[dict]:
    """A reproducible synthetic wardrobe that always has the required categories."""
    rng = random.Random(seed)
    categories = ["top", "bottom", "shoes"]
    categories += rng.choices(
        list(CATEGORY_WEIGHTS), weights=list(CATEGORY_WEIGHTS.values()), k=size - 3
    )
    return [make_garment(i + 1, c, rng) for i, c in enumerate(categories)]


def baseline_user_prompt(wardrobe: list[dict]) -> str:
    lines = [
        f"Weather: {WEATHER['temp_celsius']}°C, {WEATHER['description']}",
        f"Occasion: {OCCASION}",
        "",
        "Wardrobe:",
    ]
    lines += [f"[{item['id']}] {_describe_garment(item)}" for item in wardrobe]
    return "\n".join(lines)


def count_tokens(encoding, system: str, user: str) -> int:
    # Per-message chat overhead is a few tokens and identical for both approaches, so it is ignored.
    return len(encoding.encode(system)) + len(encoding.encode(user))


def main() -> None:
    encoding = tiktoken.get_encoding("o200k_base")  # tokenizer used by the GPT-4o family

    print(f"{'wardrobe':>9} | {'whole wardrobe':>15} | {'shortlist':>10} | {'change':>8}")
    print("-" * 52)

    for size in WARDROBE_SIZES:
        wardrobe = make_wardrobe(size, seed=size)
        items_by_id = {item["id"]: item for item in wardrobe}
        candidates = generate_outfit_candidates(wardrobe, WEATHER["temp_celsius"], OCCASION)

        whole = count_tokens(encoding, BASELINE_SYSTEM_PROMPT, baseline_user_prompt(wardrobe))
        shortlist = count_tokens(
            encoding, SYSTEM_PROMPT, build_user_prompt(candidates, items_by_id, WEATHER, OCCASION)
        )
        change = (shortlist - whole) / whole * 100

        print(f"{size:>9} | {whole:>15} | {shortlist:>10} | {change:>+7.0f}%")


if __name__ == "__main__":
    main()