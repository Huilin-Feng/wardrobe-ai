import colorsys

# A garment below either threshold carries little hue information: it reads as
# black, white, grey, beige, khaki or navy, and pairs with almost anything.
NEUTRAL_SATURATION_THRESHOLD = 0.30
NEUTRAL_VALUE_THRESHOLD = 0.40


def hex_to_hsv(hex_color: str) -> tuple[float, float, float]:
    """Convert '#RRGGBB' to (hue in degrees 0-360, saturation 0-1, value 0-1)."""
    value = hex_color.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Invalid hex color: {hex_color!r}")
    try:
        r, g, b = (int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError as error:
        raise ValueError(f"Invalid hex color: {hex_color!r}") from error

    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s, v


def is_neutral(hex_color: str) -> bool:
    """True for low-saturation or very dark colors.

    An unreadable color is also treated as neutral: with no reliable hue signal,
    the safest assumption is that it does not clash.
    """
    try:
        _, s, v = hex_to_hsv(hex_color)
    except ValueError:
        return True
    return s < NEUTRAL_SATURATION_THRESHOLD or v < NEUTRAL_VALUE_THRESHOLD


def hue_distance(hex_a: str, hex_b: str) -> float:
    """Shortest distance between two hues on the color wheel, 0 to 180 degrees."""
    h_a, _, _ = hex_to_hsv(hex_a)
    h_b, _, _ = hex_to_hsv(hex_b)
    diff = abs(h_a - h_b)
    return min(diff, 360 - diff)