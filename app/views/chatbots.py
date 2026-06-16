from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from decimal import Decimal, InvalidOperation
from ..models import Chatbot, Company, CompanyChatbot, AuditLog, MemberChatbotAccess
from ..forms import ChatbotForm, CompanyChatbotForm
from ..utils.decorators import super_admin_required


@login_required
@super_admin_required
def chatbot_list(request):
    """Lista de Chatbots (Super Admin)"""
    chatbots = Chatbot.objects.all()
    
    # Filtros
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    if search:
        chatbots = chatbots.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    if status:
        chatbots = chatbots.filter(status=status)
    
    # Adicionar contagem de empresas vinculadas
    chatbots = chatbots.annotate(
        company_count=Count('company_chatbots', filter=Q(company_chatbots__status='active'))
    )
    
    # Paginação
    paginator = Paginator(chatbots, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_title': _('Chatbots'),
        'chatbots': page_obj,
        'search': search,
        'status': status,
    }
    
    return render(request, 'chatbots/list.html', context)


@login_required
@super_admin_required
def chatbot_create(request):
    """Criar Chatbot"""
    if request.method == 'POST':
        form = ChatbotForm(request.POST)
        if form.is_valid():
            chatbot = form.save()
            messages.success(request, _('Chatbot criado com sucesso!'))
            return redirect('chatbot_list')
    else:
        form = ChatbotForm()
    
    context = {
        'page_title': _('Novo Chatbot'),
        'form': form,
    }
    
    return render(request, 'chatbots/form.html', context)


@login_required
@super_admin_required
def chatbot_edit(request, pk):
    """Editar Chatbot"""
    chatbot = get_object_or_404(Chatbot, pk=pk)
    
    if request.method == 'POST':
        form = ChatbotForm(request.POST, instance=chatbot)
        if form.is_valid():
            chatbot = form.save()
            messages.success(request, _('Chatbot atualizado com sucesso!'))
            return redirect('chatbot_list')
    else:
        form = ChatbotForm(instance=chatbot)
    
    context = {
        'page_title': _('Editar Chatbot'),
        'form': form,
        'chatbot': chatbot,
    }
    
    return render(request, 'chatbots/form.html', context)


@login_required
@super_admin_required
def chatbot_delete(request, pk):
    """Deletar Chatbot"""
    chatbot = get_object_or_404(Chatbot, pk=pk)
    
    # Verificar se está vinculado a alguma empresa
    linked_companies = chatbot.company_chatbots.filter(status='active').count()
    
    if linked_companies > 0:
        messages.error(
            request,
            _('Este chatbot está vinculado a {} empresa(s). Desvincule antes de deletar.').format(linked_companies)
        )
        return redirect('chatbot_list')
    
    if request.method == 'POST':
        chatbot_name = chatbot.name
        chatbot.delete()
        messages.success(request, _('Chatbot "{}" deletado com sucesso!').format(chatbot_name))
        return redirect('chatbot_list')
    
    context = {
        'page_title': _('Deletar Chatbot'),
        'chatbot': chatbot,
    }
    
    return render(request, 'chatbots/delete_confirm.html', context)


@login_required
@super_admin_required
def chatbot_vincular(request, pk):
    """Vincular Chatbot a Empresas"""
    chatbot = get_object_or_404(Chatbot, pk=pk)
    companies = list(Company.objects.filter(status='active').order_by('name'))
    company_links = list(CompanyChatbot.objects.filter(chatbot=chatbot).select_related('company'))
    links_map = {link.company_id: link for link in company_links}
    active_link_ids = {link.company_id for link in company_links if link.status == 'active'}
    
    pending_unlink_entries = []
    require_confirmation = False
    confirm_ack = False
    confirm_error = False
    price_errors = []
    selected_company_ids = set()
    custom_price_inputs = {}
    total_members_impacted = 0
    
    if request.method == 'POST':
        company_ids = request.POST.getlist('companies')
        selected_company_ids = {
            int(company_id) for company_id in company_ids if str(company_id).isdigit()
        }
        custom_price_inputs = {
            company.id: request.POST.get(f'custom_price_{company.id}', '').strip()
            for company in companies
        }

        for company in companies:
            if company.id not in selected_company_ids:
                continue
            custom_price = custom_price_inputs.get(company.id, '')
            if not custom_price:
                continue
            try:
                if Decimal(custom_price) <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                price_errors.append(company.name)
        
        removed_company_ids = active_link_ids - selected_company_ids
        impacted_counts = {}
        if removed_company_ids:
            impacted_qs = MemberChatbotAccess.objects.filter(
                member__company_id__in=removed_company_ids,
                chatbot=chatbot,
                status='active'
            ).values('member__company_id').annotate(member_count=Count('id'))
            impacted_counts = {
                row['member__company_id']: row['member_count'] for row in impacted_qs
            }
            pending_unlink_entries = [
                {
                    'company': links_map[company_id].company,
                    'member_count': impacted_counts.get(company_id, 0),
                }
                for company_id in removed_company_ids
                if impacted_counts.get(company_id, 0) > 0
            ]
        
        require_confirmation = bool(pending_unlink_entries)
        confirm_ack = request.POST.get('confirm_unlink') == 'on'
        
        if price_errors:
            messages.error(
                request,
                _('Informe um preço customizado válido e maior que zero para: {}').format(', '.join(price_errors))
            )
        elif require_confirmation and not confirm_ack:
            confirm_error = True
        else:
            # Processar empresas selecionadas
            for company in companies:
                company_id = company.id
                custom_price = custom_price_inputs.get(company_id, '').strip()
                link = links_map.get(company_id)
                is_selected = company_id in selected_company_ids
                
                if is_selected:
                    if not link:
                        link = CompanyChatbot(company=company, chatbot=chatbot)
                        links_map[company_id] = link
                    link.custom_price = Decimal(custom_price) if custom_price else None
                    link.status = 'active'
                    link.save()
                    
                    AuditLog.objects.create(
                        user=request.user,
                        action='chatbot_linked',
                        description=f'Chatbot {chatbot.name} vinculado à empresa {company.name}',
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                else:
                    if link and link.status == 'active':
                        link.status = 'inactive'
                        link.save()
                        impacted = MemberChatbotAccess.objects.filter(
                            member__company=company,
                            chatbot=chatbot,
                            status='active'
                        ).update(status='inactive', deactivation_date=timezone.now().date())
                        total_members_impacted += impacted
                        
                        AuditLog.objects.create(
                            user=request.user,
                            action='chatbot_unlinked',
                            description=f'Chatbot {chatbot.name} desvinculado da empresa {company.name}',
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
            
            if total_members_impacted > 0:
                messages.success(
                    request,
                    _('Vínculos atualizados. %(count)d membro(s) perderam acesso ao chatbot.') % {
                        'count': total_members_impacted
                    }
                )
            else:
                messages.success(request, _('Vínculos atualizados com sucesso!'))
            return redirect('chatbot_list')
    else:
        custom_price_inputs = {
            company.id: (
                str(links_map[company.id].custom_price)
                if company.id in links_map and links_map[company.id].custom_price is not None
                else ''
            )
            for company in companies
        }
    
    company_entries = []
    for company in companies:
        link = links_map.get(company.id)
        was_linked = bool(link and link.status == 'active')
        is_selected = (
            company.id in selected_company_ids if request.method == 'POST' else was_linked
        )
        entry_price = custom_price_inputs.get(company.id, '')
        if request.method != 'POST' and link and link.custom_price is not None:
            entry_price = str(link.custom_price)
        company_entries.append({
            'company': company,
            'is_linked': is_selected,
            'was_linked': was_linked,
            'custom_price_value': entry_price,
        })
    
    context = {
        'page_title': _('Vincular Chatbot'),
        'chatbot': chatbot,
        'company_entries': company_entries,
        'pending_unlink_entries': pending_unlink_entries,
        'require_confirmation': require_confirmation,
        'confirm_ack': confirm_ack,
        'confirm_error': confirm_error,
    }
    
    return render(request, 'chatbots/vincular.html', context)


@login_required
@super_admin_required
@require_POST
def chatbot_desvincular(request, chatbot_pk, company_pk):
    """Desvincular Chatbot de Empresa"""
    company_chatbot = get_object_or_404(
        CompanyChatbot,
        chatbot_id=chatbot_pk,
        company_id=company_pk
    )
    
    company_chatbot.status = 'inactive'
    company_chatbot.save()
    impacted = MemberChatbotAccess.objects.filter(
        member__company=company_chatbot.company,
        chatbot=company_chatbot.chatbot,
        status='active'
    ).update(status='inactive', deactivation_date=timezone.now().date())
    
    if impacted:
        messages.success(
            request,
            _('Chatbot desvinculado com sucesso. %(count)d membro(s) perderam acesso.') % {'count': impacted}
        )
    else:
        messages.success(request, _('Chatbot desvinculado com sucesso!'))
    return redirect('chatbot_list')


@login_required
def chatbot_meus_chatbots(request):
    """Meus Chatbots (Admin Empresa)"""
    user = request.user
    
    if not user.is_admin_company() or not user.company:
        messages.error(request, _('Acesso negado.'))
        return redirect('dashboard')
    
    company = user.company
    
    # Chatbots vinculados à empresa
    company_chatbots = CompanyChatbot.objects.filter(
        company=company,
        status='active'
    ).select_related('chatbot')
    
    # Calcular estatísticas
    chatbots_data = []
    for cc in company_chatbots:
        # Contar membros com acesso a este chatbot
        member_count = cc.chatbot.member_accesses.filter(
            member__company=company,
            member__status='active',
            status='active'
        ).count()
        
        chatbots_data.append({
            'chatbot': cc.chatbot,
            'price': cc.get_price(),
            'member_count': member_count,
        })
    
    context = {
        'page_title': _('Meus Chatbots'),
        'company': company,
        'chatbots_data': chatbots_data,
    }
    
    return render(request, 'chatbots/meus_chatbots.html', context)
