"""
Formatting utilities for currency, dates, phone numbers, etc.
"""

from decimal import Decimal
from datetime import datetime, date


def format_currency(value, currency='BRL', symbol='R$'):
    """
    Format currency value based on currency type
    
    Args:
        value: Decimal or float value
        currency: Currency code (BRL, USD, EUR, MXN)
        symbol: Currency symbol
    
    Returns:
        Formatted string
    """
    if value is None:
        return f"{symbol} 0,00"
    
    value = Decimal(str(value))
    
    if currency == 'BRL':
        # Brazilian format: R$ 1.234,56
        formatted = f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"{symbol} {formatted}"
    elif currency in ['USD', 'MXN']:
        # US/Mexican format: $ 1,234.56
        formatted = f"{value:,.2f}"
        return f"{symbol} {formatted}"
    elif currency == 'EUR':
        # European format: € 1.234,56
        formatted = f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"{symbol} {formatted}"
    else:
        # Default format
        return f"{symbol} {value:.2f}"


def format_cpf(cpf):
    """Format CPF: 123.456.789-00"""
    if not cpf:
        return ''
    cpf = cpf.replace('.', '').replace('-', '')
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf


def format_phone(phone):
    """Format phone: (11)98765-4321 or (11)3456-7890"""
    if not phone:
        return ''
    phone = phone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
    if len(phone) == 11:
        return f"({phone[:2]}){phone[2:7]}-{phone[7:]}"
    elif len(phone) == 10:
        return f"({phone[:2]}){phone[2:6]}-{phone[6:]}"
    return phone


def format_date(date_obj, format='%d/%m/%Y'):
    """Format date object to string"""
    if isinstance(date_obj, (datetime, date)):
        return date_obj.strftime(format)
    return str(date_obj)


def format_datetime(datetime_obj, format='%d/%m/%Y %H:%M'):
    """Format datetime object to string"""
    if isinstance(datetime_obj, datetime):
        return datetime_obj.strftime(format)
    return str(datetime_obj)


def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
