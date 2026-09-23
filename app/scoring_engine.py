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

def temperature_score(warmth_level: int, temp_celsius: float) -> float:
    """Score how well a garment's warmth suits the current temperature (0 to 1)."""
    ideal = _interpolate(temp_celsius, TEMPERATURE_TO_IDEAL_WARMTH)
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


def occasion_score(style: str, occasion: str) -> float:
    """Score how well a garment's style suits the occasion (0 to 1).

    An unknown occasion is a bad request and raises ValueError.
    An unknown style is bad data on one item and returns a low default instead,
    so a single malformed garment cannot break a whole recommendation.
    """
    occasion = occasion.strip().lower()
    if occasion not in VALID_OCCASIONS:
        raise ValueError(
            f"Unknown occasion: {occasion!r}. Expected one of {sorted(VALID_OCCASIONS)}"
        )

    row = OCCASION_MATRIX.get(style.strip().lower())
    if row is None:
        return UNKNOWN_STYLE_SCORE
    return row[occasion]