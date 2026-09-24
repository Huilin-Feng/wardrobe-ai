import pytest

from app.color_utils import hex_to_hsv, hue_distance, is_neutral


# ---------- hex_to_hsv ----------

def test_hex_to_hsv_pure_red():
    h, s, v = hex_to_hsv("#FF0000")
    assert h == pytest.approx(0)
    assert s == pytest.approx(1)
    assert v == pytest.approx(1)


def test_hex_to_hsv_white_has_no_saturation():
    _, s, v = hex_to_hsv("#FFFFFF")
    assert s == pytest.approx(0)
    assert v == pytest.approx(1)


def test_hex_to_hsv_black_has_no_value():
    _, _, v = hex_to_hsv("#000000")
    assert v == pytest.approx(0)


def test_hex_to_hsv_accepts_missing_hash_and_lowercase():
    assert hex_to_hsv("ff0000") == hex_to_hsv("#FF0000")


def test_hex_to_hsv_rejects_wrong_length():
    with pytest.raises(ValueError):
        hex_to_hsv("#FFF")


def test_hex_to_hsv_rejects_non_hex_characters():
    with pytest.raises(ValueError):
        hex_to_hsv("#ZZZZZZ")


# ---------- is_neutral ----------

@pytest.mark.parametrize("hex_color, name", [
    ("#000000", "black"),
    ("#FFFFFF", "white"),
    ("#808080", "grey"),
    ("#1E3A5F", "navy"),
    ("#D8C3A5", "beige"),
    ("#C3B091", "khaki"),
])
def test_is_neutral_recognizes_wardrobe_neutrals(hex_color, name):
    assert is_neutral(hex_color), name


@pytest.mark.parametrize("hex_color, name", [
    ("#F6EB61", "yellow polo"),
    ("#9B30FF", "bright purple"),
    ("#FFA500", "orange"),
])
def test_is_neutral_rejects_vivid_colors(hex_color, name):
    assert not is_neutral(hex_color), name


def test_is_neutral_treats_unreadable_color_as_neutral():
    assert is_neutral("#ZZZZZZ")


# ---------- hue_distance ----------

def test_hue_distance_wraps_around_the_wheel():
    """0° red and 340° pink are 20° apart, not 340°."""
    assert hue_distance("#FF0000", "#FF0055") == pytest.approx(20, abs=1)


def test_hue_distance_maximum_is_180():
    assert hue_distance("#FF0000", "#00FFFF") == pytest.approx(180)


def test_hue_distance_is_symmetric():
    assert hue_distance("#F6EB61", "#9B30FF") == hue_distance("#9B30FF", "#F6EB61")