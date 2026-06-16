"""Helpers for styling transactional emails."""

DEFAULT_PRIMARY_COLOR = '#2563eb'


def _lighten_hex_color(hex_color: str, factor: float = 0.35) -> str:
    """
    Return a lighter shade of the provided hex color.

    Factor should be between 0 and 1 where higher == lighter.
    """
    color = (hex_color or '').strip()
    if not color.startswith('#'):
        return color or DEFAULT_PRIMARY_COLOR

    hex_value = color[1:]
    if len(hex_value) == 3:
        hex_value = ''.join(ch * 2 for ch in hex_value)

    if len(hex_value) != 6:
        return color or DEFAULT_PRIMARY_COLOR

    try:
        r = int(hex_value[0:2], 16)
        g = int(hex_value[2:4], 16)
        b = int(hex_value[4:6], 16)
    except ValueError:
        return color or DEFAULT_PRIMARY_COLOR

    def lighten(component: int) -> int:
        return min(255, int(component + (255 - component) * factor))

    return '#{0:02x}{1:02x}{2:02x}'.format(lighten(r), lighten(g), lighten(b))


def get_branding_colors(system_settings) -> tuple[str, str]:
    """
    Return a tuple with primary color and a lighter companion tone.
    """
    primary = getattr(system_settings, 'primary_color', None) or DEFAULT_PRIMARY_COLOR
    return primary, _lighten_hex_color(primary, 0.35)
