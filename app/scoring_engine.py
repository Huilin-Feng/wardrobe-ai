from itertools import combinations, product

from app.color_utils import hue_distance, is_neutral


def _interpolate(x: float, points: list[tuple[float, float]]) -> float:
    """Piecewise linear interpolation over points sorted by x ascending.

    Values outside the range are clamped to the nearest endpoint.
    """
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]

    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            ratio = (x - x0) / (x1 - x0)
            return y0 + ratio * (y1 - y0)

    return points[-1][1]


# ---------- Temperature score ----------

MAX_WARMTH = 5

# Temperature (°C) -> ideal warmth level.
# Non-linear on purpose: people are more sensitive to change on the cold end,
# so the cold side moves one level every 5°C while the warm side moves every 10°C.
TEMPERATURE_TO_IDEAL_WARMTH = [
    (5, 5),
    (10, 4),
    (15, 3),
    (25, 2),
    (35, 1),
]

# Distance from ideal warmth -> score.
# The penalty accelerates: being two levels off is much worse than twice one level off.
WARMTH_GAP_TO_SCORE = [
    (0, 1.0),
    (1, 0.75),
    (2, 0.35),
    (3, 0.15),
    (4, 0.0),
]


def temperature_score(
    warmth_level: int, temp_celsius: float, max_ideal: float = MAX_WARMTH
) -> float:
    """Score how well a garment's warmth suits the current temperature (0 to 1).

    max_ideal caps how warm the garment is expected to be. Trousers and shoes rarely
    go beyond boot-level warmth, so they are judged against a lower ceiling.
    """
    ideal = min(_interpolate(temp_celsius, TEMPERATURE_TO_IDEAL_WARMTH), max_ideal)
    gap = abs(warmth_level - ideal)
    return _interpolate(gap, WARMTH_GAP_TO_SCORE)


# ---------- Occasion score ----------

VALID_OCCASIONS = frozenset({"casual", "work", "date", "formal", "workout"})

# Style x occasion compatibility. Rows are garment styles, columns are occasions.
# Every column has at least one 1.0 so the best match for any occasion can reach full marks.
OCCASION_MATRIX = {
    "casual":     {"casual": 1.0, "work": 0.4, "date": 1.0, "formal": 0.0, "workout": 0.7},
    "business":   {"casual": 0.4, "work": 1.0, "date": 0.1, "formal": 0.7, "workout": 0.0},
    "formal":     {"casual": 0.0, "work": 0.7, "date": 0.7, "formal": 1.0, "workout": 0.0},
    "sporty":     {"casual": 0.7, "work": 0.4, "date": 0.1, "formal": 0.0, "workout": 1.0},
    "streetwear": {"casual": 1.0, "work": 0.0, "date": 0.1, "formal": 0.0, "workout": 0.4},
}

# Score for a garment whose style is not in the matrix (e.g. legacy "unknown" rows).
# Low enough that any known-acceptable item outranks it, but not zero, because the
# item is unclassified rather than known to be wrong.
UNKNOWN_STYLE_SCORE = 0.1


def _normalize_occasion(occasion: str) -> str:
    """Lowercase and validate an occasion. Raises ValueError if it is not supported."""
    normalized = occasion.strip().lower()
    if normalized not in VALID_OCCASIONS:
        raise ValueError(
            f"Unknown occasion: {occasion!r}. Expected one of {sorted(VALID_OCCASIONS)}"
        )
    return normalized


def occasion_score(style: str, occasion: str) -> float:
    """Score how well a garment's style suits the occasion (0 to 1).

    An unknown occasion is a bad request and raises ValueError.
    An unknown style is bad data on one item and returns a low default instead,
    so a single malformed garment cannot break a whole recommendation.
    """
    occasion = _normalize_occasion(occasion)
    row = OCCASION_MATRIX.get(style.strip().lower())
    if row is None:
        return UNKNOWN_STYLE_SCORE
    return row[occasion]


# ---------- Color harmony ----------

# Hue gap in degrees -> score. Deliberately non-monotonic: some angles on the
# wheel pair better than their neighbours.
HUE_GAP_TO_SCORE = [
    (0, 1.0),
    (30, 0.7),
    (60, 0.7),
    (90, 0.8),
    (120, 0.6),
    (150, 0.3),
    (180, 0.2),
]

# A neutral paired with anything is a safe choice: it beats adjacent-hue pairs and
# every clash, but a same-hue match can still rank above it.
NEUTRAL_PAIR_SCORE = 0.85


def color_harmony_score(hex_a: str, hex_b: str) -> float:
    """Score how well two garment colors go together (0 to 1).

    If either garment is neutral (black, white, grey, beige, navy...), hue is not
    meaningful and the pair gets a fixed safe score. Otherwise the score comes from
    how far apart the two hues sit on the color wheel.
    """
    if is_neutral(hex_a) or is_neutral(hex_b):
        return NEUTRAL_PAIR_SCORE
    gap = hue_distance(hex_a, hex_b)
    return _interpolate(gap, HUE_GAP_TO_SCORE)


# ---------- Outfit generation ----------

REQUIRED_CATEGORIES = ("top", "bottom", "shoes")

# Above this temperature outerwear is never suggested.
OUTERWEAR_MAX_TEMPERATURE = 30

# Trousers and shoes are not expected to be warmer than boot level.
LOWER_BODY_MAX_IDEAL_WARMTH = 4

# Occasion and temperature are hard constraints, color is a soft preference,
# so occasion leads and color counts least.
WEIGHTS = {"occasion": 0.5, "temperature": 0.3, "color": 0.2}

# How many items per category survive the shortlist before combining.
# Keeps the search at most 8 x 8 x 8 x 9 combinations no matter how large the wardrobe is.
CANDIDATES_PER_CATEGORY = 8

TOP_N = 3


class IncompleteWardrobeError(ValueError):
    """Raised when the wardrobe lacks a category that every outfit needs."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Wardrobe is missing required categories: {', '.join(missing)}")


def _upper_body_warmth(top: dict, outerwear: dict | None) -> int:
    """Layers add up: a top under outerwear is warmer than either alone, capped at 5."""
    if outerwear is None:
        return top["warmth_level"]
    return min(MAX_WARMTH, top["warmth_level"] + outerwear["warmth_level"])


def score_outfit(
    top: dict,
    bottom: dict,
    shoes: dict,
    outerwear: dict | None,
    temp_celsius: float,
    occasion: str,
) -> dict:
    """Score one outfit on all three dimensions and combine them into a total."""
    garments = [g for g in (top, bottom, shoes, outerwear) if g is not None]

    # Hard constraint: the least suitable part decides.
    temperature = min(
        temperature_score(_upper_body_warmth(top, outerwear), temp_celsius),
        temperature_score(bottom["warmth_level"], temp_celsius, LOWER_BODY_MAX_IDEAL_WARMTH),
        temperature_score(shoes["warmth_level"], temp_celsius, LOWER_BODY_MAX_IDEAL_WARMTH),
    )

    # Hard constraint: one garment that is wrong for the occasion ruins the outfit.
    occasion_fit = min(occasion_score(g["style"], occasion) for g in garments)

    # Soft preference: average over every pair of garments.
    pairs = list(combinations(garments, 2))
    color = sum(color_harmony_score(a["hex_color"], b["hex_color"]) for a, b in pairs) / len(pairs)

    total = (
        WEIGHTS["temperature"] * temperature
        + WEIGHTS["occasion"] * occasion_fit
        + WEIGHTS["color"] * color
    )

    return {
        "item_ids": [g["id"] for g in garments],
        "total": total,
        "temperature": temperature,
        "occasion": occasion_fit,
        "color": color,
    }


def _shortlist_score(item: dict, temp_celsius: float, occasion: str) -> float:
    """Score a single item for the shortlist.

    Must stay consistent with score_outfit: a garment whose warmth only makes sense
    in combination (a top that may be layered, or outerwear itself) is ranked on
    occasion alone, otherwise the shortlist would drop items that make good outfits.
    """
    fit = occasion_score(item["style"], occasion)
    category = item["category"]

    if category in ("bottom", "shoes"):
        warmth = temperature_score(item["warmth_level"], temp_celsius, LOWER_BODY_MAX_IDEAL_WARMTH)
        return min(fit, warmth)

    if category == "top" and temp_celsius > OUTERWEAR_MAX_TEMPERATURE:
        return min(fit, temperature_score(item["warmth_level"], temp_celsius))

    return fit


def _shortlist(items: list[dict], temp_celsius: float, occasion: str) -> list[dict]:
    """Keep only the most promising items in one category."""
    ranked = sorted(
        items,
        key=lambda item: _shortlist_score(item, temp_celsius, occasion),
        reverse=True,
    )
    return ranked[:CANDIDATES_PER_CATEGORY]


def generate_outfit_candidates(
    wardrobe: list[dict], temp_celsius: float, occasion: str, top_n: int = TOP_N
) -> list[dict]:
    """Build outfits from the wardrobe and return the highest-scoring ones.

    Raises ValueError for an unknown occasion, and IncompleteWardrobeError if the
    wardrobe has no tops, bottoms or shoes. Accessories are not used.
    """
    occasion = _normalize_occasion(occasion)

    by_category: dict[str, list[dict]] = {"top": [], "bottom": [], "shoes": [], "outerwear": []}
    for item in wardrobe:
        if item["category"] in by_category:
            by_category[item["category"]].append(item)

    missing = [c for c in REQUIRED_CATEGORIES if not by_category[c]]
    if missing:
        raise IncompleteWardrobeError(missing)

    tops = _shortlist(by_category["top"], temp_celsius, occasion)
    bottoms = _shortlist(by_category["bottom"], temp_celsius, occasion)
    shoes = _shortlist(by_category["shoes"], temp_celsius, occasion)

    outerwear_options: list[dict | None] = [None]
    if temp_celsius <= OUTERWEAR_MAX_TEMPERATURE:
        outerwear_options += _shortlist(by_category["outerwear"], temp_celsius, occasion)

    outfits = [
        score_outfit(top, bottom, shoe, outer, temp_celsius, occasion)
        for top, bottom, shoe, outer in product(tops, bottoms, shoes, outerwear_options)
    ]
    outfits.sort(key=lambda outfit: outfit["total"], reverse=True)
    return outfits[:top_n]