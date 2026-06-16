"""
Compatibility shim for the deprecated stdlib `cgi` module removed in Python 3.13.

Only the `parse_header` helper is required by third-party dependencies (e.g., httpx).
"""

from typing import Dict, Tuple


def parse_header(line: str) -> Tuple[str, Dict[str, str]]:
    """
    Basic implementation of cgi.parse_header retained for compatibility.

    Args:
        line: Header line such as "text/html; charset=utf-8".

    Returns:
        Tuple of (main_value, params_dict).
    """
    if not line:
        return "", {}

    parts = [part.strip() for part in line.split(";")]
    main_value = parts[0].lower()
    params: Dict[str, str] = {}

    for param in parts[1:]:
        if not param or "=" not in param:
            continue
        name, value = param.split("=", 1)
        params[name.strip().lower()] = value.strip().strip('"')

    return main_value, params
