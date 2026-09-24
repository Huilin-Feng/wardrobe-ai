import pytest

from app.clothing_analyzer import VALID_STYLES
from app.scoring_engine import (
    HUE_GAP_TO_SCORE,
    NEUTRAL_PAIR_SCORE,
    OCCASION_MATRIX,
    TEMPERATURE_TO_IDEAL_WARMTH,
    UNKNOWN_STYLE_SCORE,
    VALID_OCCASIONS,
    WARMTH_GAP_TO_SCORE,
    _interpolate,
    color_harmony_score,
    occasion_score,
    temperature_score,
)


# ---------- _interpolate ----------

def test_interpolate_returns_exact_value_at_known_point():
    assert _interpolate(15, TEMPERATURE_TO_IDEAL_WARMTH) == 3


def test_interpolate_midpoint_between_two_points():
    assert _interpolate(20, TEMPERATURE_TO_IDEAL_WARMTH) == pytest.approx(2.5)


def test_interpolate_clamps_below_range():
    assert _interpolate(-40, TEMPERATURE_TO_IDEAL_WARMTH) == 5


def test_interpolate_clamps_above_range():
    assert _interpolate(50, TEMPERATURE_TO_IDEAL_WARMTH) == 1


# ---------- temperature_score: design decisions ----------

@pytest.mark.parametrize("temp, ideal_warmth", [(35, 1), (25, 2), (15, 3), (10, 4), (5, 5)])
def test_temperature_score_perfect_at_anchor_points(temp, ideal_warmth):
    assert temperature_score(ideal_warmth, temp) == 1.0


def test_temperature_score_one_level_off():
    assert temperature_score(2, 15) == pytest.approx(0.75)
    assert temperature_score(4, 15) == pytest.approx(0.75)


def test_temperature_score_two_levels_off():
    assert temperature_score(1, 15) == pytest.approx(0.35)


def test_temperature_score_maximum_mismatch_is_zero():
    assert temperature_score(5, 35) == 0.0
    assert temperature_score(1, 0) == 0.0


def test_temperature_score_extreme_cold_treated_as_coldest():
    assert temperature_score(5, -30) == 1.0


def test_temperature_score_extreme_heat_treated_as_hottest():
    assert temperature_score(1, 45) == 1.0


def test_temperature_score_between_anchor_points():
    # 20.9°C -> ideal 2.41; warmth 2 is 0.41 off -> about 0.90
    assert temperature_score(2, 20.9) == pytest.approx(0.8975)


# ---------- temperature_score: properties that must always hold ----------

@pytest.mark.parametrize("temp", [-20, 0, 5, 12.5, 20, 30, 45])
@pytest.mark.parametrize("warmth", [1, 2, 3, 4, 5])
def test_temperature_score_always_between_zero_and_one(temp, warmth):
    assert 0.0 <= temperature_score(warmth, temp) <= 1.0


def test_temperature_score_decreases_as_gap_grows():
    too_thin = [temperature_score(w, 15) for w in [3, 2, 1]]
    too_thick = [temperature_score(w, 15) for w in [3, 4, 5]]
    assert too_thin[0] > too_thin[1] > too_thin[2]
    assert too_thick[0] > too_thick[1] > too_thick[2]


def test_gap_penalty_table_is_strictly_decreasing():
    scores = [score for _, score in WARMTH_GAP_TO_SCORE]
    assert all(a > b for a, b in zip(scores, scores[1:]))


def test_temperature_table_is_sorted_by_temperature():
    """_interpolate assumes ascending x; an unsorted table would silently misbehave."""
    temps = [t for t, _ in TEMPERATURE_TO_IDEAL_WARMTH]
    assert temps == sorted(temps)


# ---------- occasion_score ----------

def test_occasion_score_known_pairs():
    assert occasion_score("sporty", "workout") == 1.0
    assert occasion_score("sporty", "date") == 0.1
    assert occasion_score("formal", "workout") == 0.0


def test_occasion_score_ignores_case_and_whitespace():
    assert occasion_score(" Business ", "WORK") == 1.0


def test_occasion_score_unknown_style_returns_default():
    assert occasion_score("unknown", "date") == UNKNOWN_STYLE_SCORE


def test_occasion_score_unknown_occasion_raises():
    with pytest.raises(ValueError, match="Unknown occasion"):
        occasion_score("casual", "wedding")


def test_unknown_style_ranks_below_any_acceptable_match():
    """Anything rated 'acceptable' (0.4) or better must beat an unclassified item."""
    assert UNKNOWN_STYLE_SCORE < 0.4


# ---------- matrix invariants ----------

def test_every_style_row_covers_every_occasion():
    for style, row in OCCASION_MATRIX.items():
        assert set(row) == VALID_OCCASIONS, style


def test_every_occasion_column_has_a_perfect_match():
    for occasion in VALID_OCCASIONS:
        best = max(row[occasion] for row in OCCASION_MATRIX.values())
        assert best == 1.0, occasion


def test_all_matrix_values_between_zero_and_one():
    for row in OCCASION_MATRIX.values():
        for value in row.values():
            assert 0.0 <= value <= 1.0


def test_matrix_covers_every_style_the_analyzer_can_produce():
    """If the Vision layer adds a style, the scoring matrix must be updated too."""
    assert set(OCCASION_MATRIX) == VALID_STYLES

# ---------- color_harmony_score ----------

YELLOW_POLO = "#F6EB61"


def test_color_same_hue_is_perfect():
    assert color_harmony_score(YELLOW_POLO, YELLOW_POLO) == 1.0


def test_color_neutral_pair_gets_fixed_score():
    assert color_harmony_score(YELLOW_POLO, "#1E3A5F") == NEUTRAL_PAIR_SCORE


def test_color_two_neutrals_get_fixed_score():
    assert color_harmony_score("#000000", "#FFFFFF") == NEUTRAL_PAIR_SCORE


def test_color_unreadable_hex_is_treated_as_neutral():
    assert color_harmony_score(YELLOW_POLO, "#ZZZZZZ") == NEUTRAL_PAIR_SCORE


@pytest.mark.parametrize("other, name", [
    ("#9B30FF", "bright purple"),
    ("#3FA9F5", "sky blue"),
    ("#1E60FF", "bright blue"),
])
def test_color_vivid_clashes_with_yellow_score_low(other, name):
    """Found by testing real pairs: all three looked bad next to the yellow polo."""
    assert color_harmony_score(YELLOW_POLO, other) < 0.4, name


def test_color_navy_beats_orange_with_yellow():
    """Design decision: a neutral pairing should outrank an adjacent-hue pairing."""
    navy = color_harmony_score(YELLOW_POLO, "#1E3A5F")
    orange = color_harmony_score(YELLOW_POLO, "#FFA500")
    assert navy > orange


def test_neutral_score_beats_every_clash_but_not_a_perfect_match():
    worst = min(score for _, score in HUE_GAP_TO_SCORE)
    assert worst < NEUTRAL_PAIR_SCORE < 1.0


def test_hue_table_covers_full_range_in_order():
    gaps = [g for g, _ in HUE_GAP_TO_SCORE]
    assert gaps == sorted(gaps)
    assert gaps[0] == 0 and gaps[-1] == 180