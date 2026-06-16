"""
Custom validators for identification documents and phone.
"""

import re

def clean_phone(value):
    """Clean phone removing non-digits"""
    return re.sub(r'\D', '', value) if value else ''


def clean_identification_document(value):
    """Basic cleanup for international identification documents"""
    return value.strip() if value else ''
