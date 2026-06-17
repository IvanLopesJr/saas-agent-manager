from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from datetime import timedelta
import csv
from django.utils import timezone
from ..models import AuditLog
from ..utils.decorators import super_admin_required


@login_required
@super_admin_required
def audit_log_list(request):
    """Lista paginada e filtrável do histórico de auditoria"""
    logs = AuditLog.objects.select_related('user').all()

    action = request.GET.get('action', '')
    user_id = request.GET.get('user', '')
    date_start = request.GET.get('date_start', '')
    date_end = request.GET.get('date_end', '')
    company = request.GET.get('company', '')

    if action:
        logs = logs.filter(action=action)
    if user_id:
        logs = logs.filter(user_id=user_id)
    if date_start:
        logs = logs.filter(created_at__date__gte=date_start)
    if date_end:
        logs = logs.filter(created_at__date__lte=date_end)
    if company:
        logs = logs.filter(user__company_id=company)

    logs = logs.order_by('-created_at')

    total_30d = AuditLog.objects.filter(
        created_at__date__gte=timezone.now().date() - timedelta(days=30)
    ).count()

    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    action_choices = AuditLog.ACTION_CHOICES

    from ..models import Company, User
    users = User.objects.filter(status='active').order_by('username')
    companies = Company.objects.filter(status='active').order_by('name')

    is_export = request.GET.get('export') == 'csv'
    if is_export:
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response.write('\ufeff')
        response['Content-Disposition'] = 'attachment; filename="auditoria.csv"'
        writer = csv.writer(response)
        writer.writerow(['Data/Hora', 'Usuário', 'Ação', 'Descrição', 'IP'])
        for log in page_obj.object_list:
            writer.writerow([
                log.created_at.strftime('%d/%m/%Y %H:%M'),
                log.user.get_full_name() or log.user.username if log.user else '-',
                log.get_action_display(),
                log.description,
                log.ip_address or '',
            ])
        return response

    context = {
        'page_title': _('Histórico de Auditoria'),
        'logs': page_obj,
        'action': action,
        'user_id': user_id,
        'date_start': date_start,
        'date_end': date_end,
        'company': company,
        'total_30d': total_30d,
        'action_choices': action_choices,
        'users': users,
        'companies': companies,
    }
    return render(request, 'audit/list.html', context)
