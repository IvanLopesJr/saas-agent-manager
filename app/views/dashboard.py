from datetime import date

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.utils import formats
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from ..models import (
    Company,
    CompanyMember,
    Chatbot,
    Billing,
    User,
    AuditLog,
    MemberChatbotAccess,
    CompanyChatbot,
)
from ..utils.billing import calculate_estimated_cost


def _month_range(months=6):
    """Return a list of date objects representing the first day of the last N months."""
    today = timezone.now().date()
    current_month = today.replace(day=1)
    start = current_month - relativedelta(months=months - 1)
    return [start + relativedelta(months=i) for i in range(months)]


def _format_month_label(d: date) -> str:
    return formats.date_format(d, format='M Y', use_l10n=True)


@login_required
def dashboard_view(request):
    """Dashboard principal (redireciona conforme perfil)"""
    user = request.user
    
    if user.is_super_admin():
        return dashboard_super_admin(request)
    elif user.is_admin_company():
        return dashboard_admin_empresa(request)
    else:
        return render(request, 'dashboard/no_access.html')


def dashboard_super_admin(request):
    """Dashboard do Super Admin"""
    total_companies = Company.objects.filter(status='active').count()
    total_members = CompanyMember.objects.filter(status='active').count()
    total_chatbots = Chatbot.objects.filter(status='active').count()

    total_monthly_cost = Decimal('0.00')
    for company in Company.objects.filter(status='active').iterator():
        total_monthly_cost += calculate_estimated_cost(company)

    recent_activities = AuditLog.objects.select_related('user').order_by('-created_at')[:10]

    month_sequence = _month_range()
    member_evolution_raw = CompanyMember.objects.filter(
        created_at__date__gte=month_sequence[0]
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    member_evolution_map = {
        (item['month'].date() if hasattr(item['month'], 'date') else item['month']): item['count']
        for item in member_evolution_raw
    }
    member_evolution_chart = {
        'labels': [_format_month_label(month) for month in month_sequence],
        'values': [member_evolution_map.get(month, 0) for month in month_sequence],
    }

    billing_evolution_raw = Billing.objects.filter(
        period_start__gte=month_sequence[0]
    ).annotate(
        month=TruncMonth('period_start')
    ).values('month').annotate(
        total=Sum('total_value')
    ).order_by('month')
    billing_evolution_map = {
        (item['month'].date() if hasattr(item['month'], 'date') else item['month']): float(item['total'])
        for item in billing_evolution_raw
    }
    billing_evolution_chart = {
        'labels': [_format_month_label(month) for month in month_sequence],
        'values': [billing_evolution_map.get(month, 0.0) for month in month_sequence],
    }

    billing_mode_qs = Company.objects.values('billing_mode').annotate(count=Count('id'))
    billing_mode_chart = {
        'labels': [
            str(dict(Company.BILLING_MODE_CHOICES).get(item['billing_mode'], item['billing_mode']))
            for item in billing_mode_qs
        ],
        'values': [item['count'] for item in billing_mode_qs],
    }

    top_companies = Company.objects.filter(status='active').annotate(
        member_count=Count('members', filter=Q(members__status='active'))
    ).order_by('-member_count')[:5]
    top_companies_chart = {
        'labels': [company.name for company in top_companies],
        'values': [company.member_count for company in top_companies],
    }
    top_companies_table = [
        {'name': company.name, 'member_count': company.member_count}
        for company in top_companies
    ]

    recent_companies = Company.objects.filter(status='active').annotate(
        active_member_count=Count('members', filter=Q(members__status='active'))
    ).order_by('-created_at')[:5]
    company_growth_chart = {
        'labels': [company.name for company in recent_companies],
        'values': [company.active_member_count for company in recent_companies],
    }

    context = {
        'page_title': _('Dashboard'),
        'total_companies': total_companies,
        'total_members': total_members,
        'total_chatbots': total_chatbots,
        'total_monthly_cost': total_monthly_cost,
        'recent_activities': recent_activities,
        'member_evolution_chart': member_evolution_chart,
        'billing_evolution_chart': billing_evolution_chart,
        'billing_mode_chart': billing_mode_chart,
        'company_growth_chart': company_growth_chart,
        'top_companies_chart': top_companies_chart,
        'top_companies_table': top_companies_table,
    }

    return render(request, 'dashboard/super_admin.html', context)

def dashboard_admin_empresa(request):
    """Dashboard do Admin da Empresa"""
    user = request.user
    company = user.company

    if not company:
        return render(request, 'dashboard/no_company.html')

    total_members = company.members.filter(status='active').count()
    pending_members = company.members.filter(status='pending').count()
    inactive_members = company.members.filter(status='inactive').count()

    total_chatbots = company.company_chatbots.filter(status='active').count()

    monthly_cost = calculate_estimated_cost(company)
    admin_user_count = company.users.filter(
        role='admin_company',
        status='active'
    ).count()

    recent_billings = company.billings.order_by('-period_start')[:5]
    recent_members = company.members.order_by('-created_at')[:5]

    month_sequence = _month_range()
    billing_trend_raw = company.billings.filter(
        period_start__gte=month_sequence[0]
    ).annotate(
        month=TruncMonth('period_start')
    ).values('month').annotate(
        total=Sum('total_value')
    ).order_by('month')
    company_billing_map = {
        (item['month'].date() if hasattr(item['month'], 'date') else item['month']): float(item['total'])
        for item in billing_trend_raw
    }
    company_billing_trend_chart = {
        'labels': [_format_month_label(month) for month in month_sequence],
        'values': [company_billing_map.get(month, 0.0) for month in month_sequence],
    }

    status_legend = dict(CompanyMember.STATUS_CHOICES)
    status_qs = company.members.values('status').annotate(count=Count('id'))
    status_distribution_chart = {
        'labels': [str(status_legend.get(item['status'], item['status'])) for item in status_qs],
        'values': [item['count'] for item in status_qs],
    }

    chatbot_usage_qs = MemberChatbotAccess.objects.filter(
        member__company=company,
        status='active'
    ).values('chatbot__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    chatbot_usage_chart = {
        'labels': [item['chatbot__name'] or _('Sem nome') for item in chatbot_usage_qs],
        'values': [item['count'] for item in chatbot_usage_qs],
    }

    team_overview_chart = {
        'labels': [
            str(_('Admins ativos')),
            str(_('Membros ativos')),
            str(_('Membros pendentes')),
            str(_('Membros inativos')),
        ],
        'values': [
            admin_user_count,
            total_members,
            pending_members,
            inactive_members,
        ],
    }

    chatbot_status_qs = company.company_chatbots.values('status').annotate(count=Count('id'))
    chatbot_status_display = dict(CompanyChatbot.STATUS_CHOICES)
    chatbot_status_chart = {
        'labels': [
            str(chatbot_status_display.get(item['status'], item['status']))
            for item in chatbot_status_qs
        ],
        'values': [item['count'] for item in chatbot_status_qs],
    }

    context = {
        'page_title': _('Dashboard'),
        'company': company,
        'total_members': total_members,
        'pending_members': pending_members,
        'inactive_members': inactive_members,
        'total_chatbots': total_chatbots,
        'monthly_cost': monthly_cost,
        'recent_billings': recent_billings,
        'recent_members': recent_members,
        'company_billing_trend_chart': company_billing_trend_chart,
        'status_distribution_chart': status_distribution_chart,
        'chatbot_usage_chart': chatbot_usage_chart,
        'team_overview_chart': team_overview_chart,
        'chatbot_status_chart': chatbot_status_chart,
    }

    return render(request, 'dashboard/admin_empresa.html', context)
