"""
Billing utilities for generating company invoices
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Q
from ..models import (
    Billing, BillingDetail, Company, CompanyMember,
    User, SystemSettings, MemberChatbotAccess
)


MONEY_QUANT = Decimal('0.01')


def _money(value):
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _active_status_during_period_q(prefix, period_start, period_end):
    return (
        Q(**{f'{prefix}status_history__status': 'active'}) &
        Q(**{f'{prefix}status_history__date_start__lte': period_end}) &
        (
            Q(**{f'{prefix}status_history__date_end__isnull': True}) |
            Q(**{f'{prefix}status_history__date_end__gte': period_start})
        )
    )


def _access_active_during_period_q(period_start, period_end):
    return (
        Q(activation_date__lte=period_end) &
        (
            Q(status='active') |
            Q(deactivation_date__gte=period_start)
        )
    )


def generate_billing_for_company(company, period_start, period_end, generated_by):
    """
    Generate billing for a company for a specific period
    
    Args:
        company: Company instance
        period_start: date object for period start
        period_end: date object for period end
        generated_by: User who generated the billing
    
    Returns:
        Billing instance or None if no charges
    """
    
    # Get system settings
    settings = SystemSettings.get_settings()
    cutoff_day = settings.billing_cutoff_day
    
    # Calculate total days in period
    total_days = (period_end - period_start).days + 1
    
    # Initialize total
    total_value = Decimal('0.00')
    details = []
    
    if company.billing_mode == 'per_user':
        # Mode: Per User (fixed price per user regardless of chatbots)
        total_value, details, members_first_cycle_to_close = _calculate_per_user_billing(
            company, period_start, period_end, cutoff_day, total_days
        )
        access_ids_to_close = set()
    else:
        # Mode: Per User/Chatbot (price per user per chatbot)
        total_value, details, access_ids_to_close = _calculate_per_chatbot_billing(
            company, period_start, period_end, cutoff_day, total_days
        )
        members_first_cycle_to_close = set()
    
    # Only create billing if there are charges
    if total_value <= 0:
        return None
    
    # Create billing record with transaction
    with transaction.atomic():
        billing = Billing.objects.create(
            company=company,
            period_start=period_start,
            period_end=period_end,
            total_value=total_value,
            generated_by=generated_by
        )
        
        # Create billing details
        for detail_data in details:
            BillingDetail.objects.create(
                billing=billing,
                **detail_data
            )

        if members_first_cycle_to_close:
            CompanyMember.objects.filter(id__in=members_first_cycle_to_close).update(first_cycle_completed=True)
        if access_ids_to_close:
            MemberChatbotAccess.objects.filter(id__in=access_ids_to_close).update(first_cycle_completed=True)
    
    return billing


def _calculate_per_user_billing(company, period_start, period_end, cutoff_day, total_days):
    """Calculate billing for per_user mode"""
    
    details = []
    total = Decimal('0.00')
    members_first_cycle_to_close = set()
    
    # Get members active during the period. Admin-linked members only count
    # when company.bill_admin_users is enabled.
    members = CompanyMember.objects.filter(
        company=company,
        created_at__date__lte=period_end,
    ).filter(
        _active_status_during_period_q('', period_start, period_end)
    ).select_related('user').distinct()
    if not company.bill_admin_users:
        members = members.filter(user__isnull=True)
    
    # Calculate for each member
    for member in members:
        # Check if member has any chatbot access;
        # charge_inactive_members overrides this filter
        has_access = member.chatbot_accesses.filter(
            _access_active_during_period_q(period_start, period_end)
        ).exists()
        
        if not has_access and not company.charge_inactive_members:
            continue  # Skip members without chatbot access
        
        # Get activation date (earliest chatbot access or member creation)
        earliest_access = member.chatbot_accesses.filter(
            _access_active_during_period_q(period_start, period_end)
        ).order_by('activation_date').first()
        
        if not earliest_access:
            if not company.charge_inactive_members:
                continue
            raw_activation_date = member.created_at.date()
            activation_date = max(raw_activation_date, period_start)
            is_first_cycle = (
                not member.first_cycle_completed
                and period_start <= raw_activation_date <= period_end
            )
        else:
            activation_date = max(earliest_access.activation_date, period_start)
            is_first_cycle = (
                not member.first_cycle_completed
                and period_start <= earliest_access.activation_date <= period_end
            )

        price_snapshot = member.first_cycle_price_snapshot or company.member_price
        member_price = price_snapshot if is_first_cycle else company.member_price

        # Determine billing type
        if activation_date.day <= cutoff_day:
            # Full month billing
            value = _money(member_price)
            days_active = total_days
            billing_type = 'full'
        else:
            # Proportional billing
            days_remaining = (period_end - activation_date).days + 1
            daily_rate = member_price / Decimal(str(total_days))
            value = _money(daily_rate * Decimal(str(days_remaining)))
            days_active = days_remaining
            billing_type = 'proportional'
        
        details.append({
            'member_id': member.id,
            'user_id': member.user_id,
            'chatbot_id': None,
            'activation_date': activation_date,
            'days_active': days_active,
            'daily_rate': _money(member_price / Decimal(str(total_days))),
            'value': value,
            'billing_type': billing_type,
            'unit_price': _money(member_price)
        })
        
        total += value
        if is_first_cycle:
            members_first_cycle_to_close.add(member.id)
    
    return _money(total), details, members_first_cycle_to_close


def _calculate_per_chatbot_billing(company, period_start, period_end, cutoff_day, total_days):
    """Calculate billing for per_user_chatbot mode"""
    
    details = []
    total = Decimal('0.00')
    access_ids_to_close = set()
    
    # Get all chatbot accesses active during the period. Admin-linked member
    # accesses only count when company.bill_admin_users is enabled.
    accesses = MemberChatbotAccess.objects.filter(
        member__company=company,
    ).filter(
        _access_active_during_period_q(period_start, period_end),
        _active_status_during_period_q('member__', period_start, period_end),
    ).select_related('member', 'member__user', 'chatbot').distinct()
    if not company.bill_admin_users:
        accesses = accesses.filter(member__user__isnull=True)
    
    # Calculate for each access
    for access in accesses:
        # Get price for this chatbot
        company_chatbot = company.company_chatbots.filter(
            chatbot=access.chatbot,
            status='active'
        ).first()
        
        if not company_chatbot:
            continue
        
        price = company_chatbot.get_price()
        is_first_cycle = (
            not access.first_cycle_completed
            and period_start <= access.activation_date <= period_end
        )
        price_snapshot = access.first_cycle_price_snapshot or price
        effective_price = price_snapshot if is_first_cycle else price
        activation_date = max(access.activation_date, period_start)
        
        # Determine billing type
        if activation_date.day <= cutoff_day:
            value = _money(effective_price)
            days_active = total_days
            billing_type = 'full'
        else:
            days_remaining = (period_end - activation_date).days + 1
            daily_rate = effective_price / Decimal(str(total_days))
            value = _money(daily_rate * Decimal(str(days_remaining)))
            days_active = days_remaining
            billing_type = 'proportional'
        
        details.append({
            'member_id': access.member.id,
            'user_id': access.member.user_id,
            'chatbot_id': access.chatbot.id,
            'activation_date': activation_date,
            'days_active': days_active,
            'daily_rate': _money(effective_price / Decimal(str(total_days))),
            'value': value,
            'billing_type': billing_type,
            'unit_price': _money(effective_price)
        })
        
        total += value
        if is_first_cycle:
            access_ids_to_close.add(access.id)
    
    return _money(total), details, access_ids_to_close

def calculate_estimated_cost(company, include_admins=None):
    """
    Calculate estimated monthly cost for a company
    
    Args:
        company: Company instance
        include_admins: Override company.bill_admin_users setting
    
    Returns:
        Decimal: Estimated monthly cost
    """
    
    total = Decimal('0.00')
    
    if include_admins is None:
        include_admins = company.bill_admin_users
    
    if company.billing_mode == 'per_user':
        # Count active members. When charge_inactive_members is False,
        # only count members with chatbot access.
        if company.charge_inactive_members:
            active_members_qs = company.members.filter(status='active')
        else:
            active_members_qs = company.members.filter(
                status='active',
                chatbot_accesses__status='active'
            )
        if not include_admins:
            active_members_qs = active_members_qs.filter(user__isnull=True)
        active_members = active_members_qs.distinct().count()
        
        total = Decimal(str(active_members)) * company.member_price
    
    else:  # per_user_chatbot
        # Sum all active chatbot accesses. Admin-linked member accesses only
        # count when include_admins is enabled.
        accesses = MemberChatbotAccess.objects.filter(
            member__company=company,
            member__status='active',
            status='active'
        ).select_related('member', 'chatbot')
        if not include_admins:
            accesses = accesses.filter(member__user__isnull=True)
        
        for access in accesses:
            company_chatbot = company.company_chatbots.filter(
                chatbot=access.chatbot,
                status='active'
            ).first()
            if company_chatbot:
                total += company_chatbot.get_price()
    
    return total




