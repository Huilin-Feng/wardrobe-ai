import pytest

from app.scoring_engine import (
    CANDIDATES_PER_CATEGORY,
    LOWER_BODY_MAX_IDEAL_WARMTH,
    NEUTRAL_PAIR_SCORE,
    WEIGHTS,
    IncompleteWardrobeError,
    _shortlist,
    _shortlist_score,
    _upper_body_warmth,
    generate_outfit_candidates,
    temperature_score,
)


def garment(id, category, warmth=3, style="casual", hex_color="#808080"):
    return {
        "id": id,
        "category": category,
        "warmth_level": warmth,
        "style": style,
        "hex_color": hex_color,
    }


def basic_wardrobe():
    return [
        garment(1, "top", 2, "casual", "#F6EB61"),
        garment(2, "bottom", 3, "casual", "#1E3A5F"),
        garment(3, "shoes", 2, "sporty", "#FFFFFF"),
    ]


# ---------- input validation ----------

def test_missing_shoes_is_reported():
    wardrobe = [garment(1, "top"), garment(2, "bottom")]
    with pytest.raises(IncompleteWardrobeError) as error:
        generate_outfit_candidates(wardrobe, 20, "casual")
    assert error.value.missing == ["shoes"]


def test_empty_wardrobe_reports_every_missing_category():
    with pytest.raises(IncompleteWardrobeError) as error:
        generate_outfit_candidates([], 20, "casual")
    assert error.value.missing == ["top", "bottom", "shoes"]


def test_unknown_occasion_raises():
    with pytest.raises(ValueError, match="Unknown occasion"):
        generate_outfit_candidates(basic_wardrobe(), 20, "wedding")


def test_occasion_is_case_insensitive():
    assert generate_outfit_candidates(basic_wardrobe(), 20, "CASUAL")


# ---------- outfit structure ----------

def test_accessories_are_never_used():
    wardrobe = basic_wardrobe() + [garment(9, "accessory")]
    for outfit in generate_outfit_candidates(wardrobe, 20, "casual"):
        assert 9 not in outfit["item_ids"]


def test_no_outerwear_above_30_degrees():
    wardrobe = basic_wardrobe() + [garment(4, "outerwear", 1)]
    for outfit in generate_outfit_candidates(wardrobe, 35, "casual"):
        assert 4 not in outfit["item_ids"]


def test_returns_at_most_top_n():
    wardrobe = basic_wardrobe() + [
        garment(4, "top", 2, "casual", "#FFFFFF"),
        garment(5, "bottom", 3, "casual", "#000000"),
    ]
    assert len(generate_outfit_candidates(wardrobe, 20, "casual")) == 3
    assert len(generate_outfit_candidates(wardrobe, 20, "casual", top_n=1)) == 1


def test_results_are_sorted_best_first():
    wardrobe = basic_wardrobe() + [
        garment(4, "top", 5, "formal", "#9B30FF"),
        garment(5, "shoes", 4, "business", "#000000"),
    ]
    totals = [o["total"] for o in generate_outfit_candidates(wardrobe, 20, "casual")]
    assert totals == sorted(totals, reverse=True)


# ---------- temperature rules ----------

def test_layers_add_up_and_cap_at_five():
    assert _upper_body_warmth(garment(1, "top", 3), None) == 3
    assert _upper_body_warmth(garment(1, "top", 3), garment(2, "outerwear", 2)) == 5
    assert _upper_body_warmth(garment(1, "top", 3), garment(2, "outerwear", 4)) == 5


def test_tee_under_parka_is_warm_enough_in_winter():
    """A thin top alone scores 0 at 0°C, but layered under a parka it is fine."""
    wardrobe = [
        garment(1, "top", 1, "casual", "#F6EB61"),
        garment(2, "bottom", 3, "casual", "#1E3A5F"),
        garment(3, "shoes", 4, "casual", "#000000"),
        garment(4, "outerwear", 5, "casual", "#000000"),
    ]
    best = generate_outfit_candidates(wardrobe, 0, "casual")[0]
    assert 4 in best["item_ids"]
    assert best["temperature"] == pytest.approx(0.75)


def test_lower_body_is_judged_against_boot_level_warmth():
    """Jeans at 0°C should not be treated like a missing winter coat."""
    assert temperature_score(3, 0, LOWER_BODY_MAX_IDEAL_WARMTH) == pytest.approx(0.75)
    assert temperature_score(3, 0) == pytest.approx(0.35)


# ---------- occasion rule ----------

def test_one_wrong_garment_ruins_occasion_fit():
    wardrobe = [
        garment(1, "top", 2, "business", "#FFFFFF"),
        garment(2, "bottom", 3, "business", "#333333"),
        garment(3, "shoes", 3, "business", "#000000"),
        garment(4, "shoes", 2, "streetwear", "#FFFFFF"),
    ]
    outfits = generate_outfit_candidates(wardrobe, 20, "work")
    assert 3 in outfits[0]["item_ids"]
    for outfit in outfits:
        if 4 in outfit["item_ids"]:
            assert outfit["occasion"] == 0.0


# ---------- color rule ----------

def test_all_neutral_outfit_gets_neutral_color_score():
    wardrobe = [
        garment(1, "top", 2, "casual", "#FFFFFF"),
        garment(2, "bottom", 3, "casual", "#000000"),
        garment(3, "shoes", 2, "casual", "#808080"),
    ]
    best = generate_outfit_candidates(wardrobe, 20, "casual")[0]
    assert best["color"] == pytest.approx(NEUTRAL_PAIR_SCORE)


# ---------- weights ----------

def test_weights_sum_to_one():
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_total_is_the_weighted_sum_of_dimensions():
    for outfit in generate_outfit_candidates(basic_wardrobe(), 20, "casual"):
        expected = (
            WEIGHTS["temperature"] * outfit["temperature"]
            + WEIGHTS["occasion"] * outfit["occasion"]
            + WEIGHTS["color"] * outfit["color"]
        )
        assert outfit["total"] == pytest.approx(expected)


# ---------- shortlist ----------

def test_shortlist_caps_each_category():
    tops = [garment(i, "top") for i in range(20)]
    assert len(_shortlist(tops, 20, "casual")) == CANDIDATES_PER_CATEGORY


def test_shortlist_does_not_penalize_thin_top_when_layering_is_possible():
    """If warmth were counted here, the tee would be dropped before it could meet a coat."""
    tee = garment(1, "top", 1, "casual")
    assert _shortlist_score(tee, 0, "casual") == 1.0


def test_shortlist_does_judge_top_warmth_when_no_outerwear_is_allowed():
    sweater = garment(1, "top", 5, "casual")
    assert _shortlist_score(sweater, 35, "casual") < 1.0