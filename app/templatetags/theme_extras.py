"""
Custom template helpers related to theming/custom colors.
"""

from django import template

register = template.Library()


@register.filter
def hex_to_rgb(value: str) -> str:
    """
    Convert a hex color string (e.g. ``#ff00aa``) to an ``R, G, B`` string.

    If the value is invalid or missing, fall back to black.
    """
    if not value:
        return "0, 0, 0"

    hex_value = str(value).strip().lstrip("#")
    if len(hex_value) == 3:
        hex_value = "".join(ch * 2 for ch in hex_value)

    if len(hex_value) != 6:
        return "0, 0, 0"

    try:
        r = int(hex_value[0:2], 16)
        g = int(hex_value[2:4], 16)
        b = int(hex_value[4:6], 16)
    except ValueError:
        return "0, 0, 0"

    return f"{r}, {g}, {b}"
