from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db.models.deletion import ProtectedError
from ..models import Company, AuditLog
from ..forms import CompanyForm
from ..utils.decorators import super_admin_required


@login_required
@super_admin_required
def company_list(request):
    """Lista de Empresas"""
    companies = Company.objects.all()
    
    # Filtros
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    billing_mode = request.GET.get('billing_mode', '')
    
    if search:
        companies = companies.filter(
            Q(name__icontains=search) |
            Q(identification_document__icontains=search) |
            Q(email__icontains=search)
        )
    
    if status:
        companies = companies.filter(status=status)
    
    if billing_mode:
        companies = companies.filter(billing_mode=billing_mode)
    
    # Adicionar contadores
    companies = companies.annotate(
        member_count=Count('members', filter=Q(members__status='active'), distinct=True),
        chatbot_count=Count('company_chatbots', filter=Q(company_chatbots__status='active'), distinct=True)
    )
    
    # Paginação
    paginator = Paginator(companies, 12)  # 12 cards por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_title': _('Empresas'),
        'companies': page_obj,
        'search': search,
        'status': status,
        'billing_mode': billing_mode,
    }
    
    return render(request, 'companies/list.html', context)


@login_required
@super_admin_required
def company_create(request):
    """Criar Empresa"""
    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES)
        if form.is_valid():
            company = form.save()
            messages.success(request, _('Empresa criada com sucesso!'))
            
            AuditLog.objects.create(
                user=request.user,
                action='company_created',
                description=f'Empresa criada: {company.name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return redirect('company_detail', pk=company.pk)
    else:
        form = CompanyForm()
    
    context = {
        'page_title': _('Nova Empresa'),
        'form': form,
    }
    
    return render(request, 'companies/form.html', context)


@login_required
@super_admin_required
def company_edit(request, pk):
    """Editar Empresa"""
    company = get_object_or_404(Company, pk=pk)
    
    if request.method == 'POST':
        old_billing_mode = company.billing_mode
        old_member_price = company.member_price
        
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            company = form.save()
            messages.success(request, _('Empresa atualizada com sucesso!'))
            
            # Registrar mudanças críticas
            if old_billing_mode != company.billing_mode:
                AuditLog.objects.create(
                    user=request.user,
                    action='billing_mode_changed',
                    description=f'Modo de cobrança alterado de {old_billing_mode} para {company.billing_mode} - Empresa: {company.name}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            if old_member_price != company.member_price:
                AuditLog.objects.create(
                    user=request.user,
                    action='member_price_changed',
                    description=f'Preço de membro alterado de {old_member_price} para {company.member_price} - Empresa: {company.name}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            return redirect('company_detail', pk=company.pk)
    else:
        form = CompanyForm(instance=company)
    
    context = {
        'page_title': _('Editar Empresa'),
        'form': form,
        'company': company,
    }
    
    return render(request, 'companies/form.html', context)


@login_required
@super_admin_required
def company_detail(request, pk):
    """Detalhes da Empresa (hub central)"""
    from datetime import date
    from decimal import Decimal
    from django.utils import timezone
    from django.utils import formats
    from django.db.models.functions import TruncMonth
    from django.db.models import Sum
    from dateutil.relativedelta import relativedelta
    from ..utils.billing import calculate_estimated_cost

    company = get_object_or_404(Company, pk=pk)
    
    total_members = company.members.filter(status='active').count()
    total_chatbots = company.company_chatbots.filter(status='active').count()
    total_users = company.users.filter(status='active').count()
    pending_members = company.members.filter(status='pending').count()
    
    monthly_cost = calculate_estimated_cost(company)
    
    recent_billings = company.billings.order_by('-period_start')[:5]
    recent_members = company.members.order_by('-created_at')[:5]
    
    chatbot_active = company.company_chatbots.filter(status='active').count()
    chatbot_inactive = company.company_chatbots.filter(status='inactive').count()
    
    today = timezone.now().date()
    current_month_start = today.replace(day=1)
    has_current_billing = company.billings.filter(period_end__gte=current_month_start).exists()
    
    month_sequence = []
    for i in range(5, -1, -1):
        month_sequence.append(current_month_start - relativedelta(months=i))
    
    billing_trend_raw = company.billings.filter(
        period_start__gte=month_sequence[0]
    ).annotate(
        month=TruncMonth('period_start')
    ).values('month').annotate(
        total=Sum('total_value')
    ).order_by('month')
    
    billing_trend_map = {}
    for item in billing_trend_raw:
        m = item['month'].date() if hasattr(item['month'], 'date') else item['month']
        billing_trend_map[m] = float(item['total'])
    
    billing_trend_chart = {
        'labels': [formats.date_format(m, format='M Y', use_l10n=True) for m in month_sequence],
        'values': [billing_trend_map.get(m, 0.0) for m in month_sequence],
    }
    
    context = {
        'page_title': company.name,
        'company': company,
        'total_members': total_members,
        'pending_members': pending_members,
        'total_chatbots': total_chatbots,
        'total_users': total_users,
        'monthly_cost': monthly_cost,
        'recent_billings': recent_billings,
        'recent_members': recent_members,
        'chatbot_active': chatbot_active,
        'chatbot_inactive': chatbot_inactive,
        'has_current_billing': has_current_billing,
        'billing_trend_chart': billing_trend_chart,
    }
    
    return render(request, 'companies/detail.html', context)


@login_required
@super_admin_required
def company_delete(request, pk):
    """Deletar Empresa (confirmação)"""
    company = get_object_or_404(Company, pk=pk)
    
    if request.method == 'POST':
        company_name = company.name
        try:
            company.delete()
        except ProtectedError as e:
            protected_objects = e.protected_objects if hasattr(e, 'protected_objects') else []
            related_names = set()
            for obj in protected_objects:
                related_names.add(obj._meta.verbose_name_plural)
            if not related_names:
                related_names = {'usuários', 'membros', 'cobranças', 'vinculações'}
            messages.error(
                request,
                _('Não é possível deletar "{}". Existem {} vinculados a esta empresa. '
                  'Inative a empresa em vez de deletá-la.').format(company_name, ', '.join(related_names))
            )
            return redirect('company_detail', pk=company.pk)
        
        messages.success(request, _('Empresa "{}" deletada com sucesso!').format(company_name))
        
        AuditLog.objects.create(
            user=request.user,
            action='company_deleted',
            description=f'Empresa deletada: {company_name}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return redirect('company_list')
    
    context = {
        'page_title': _('Deletar Empresa'),
        'company': company,
    }
    
    return render(request, 'companies/delete_confirm.html', context)


@login_required
@super_admin_required
@require_POST
def company_toggle_status(request, pk):
    """Ativar/Inativar Empresa"""
    company = get_object_or_404(Company, pk=pk)
    
    if company.status == 'active':
        company.status = 'inactive'
        messages.success(request, _('Empresa inativada com sucesso!'))
    else:
        company.status = 'active'
        messages.success(request, _('Empresa ativada com sucesso!'))
    
    company.save()
    
    return redirect('company_detail', pk=company.pk)
