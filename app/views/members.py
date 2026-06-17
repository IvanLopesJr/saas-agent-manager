from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Prefetch
from datetime import date, datetime
import csv
import io
from ..models import (
    CompanyMember, Company, Chatbot, MemberChatbotAccess,
    AuditLog
)
from ..forms import CompanyMemberForm, MemberImportForm
from ..utils.csv_handler import (
    parse_csv_file,
    generate_csv_export,
    validate_csv_structure,
)
from ..utils.member_link import link_member_to_admin_user, unlink_member_from_admin_user

FIELD_LABELS = {
    'name': _('Nome'),
    'email': _('Email'),
    'phone': _('Telefone'),
    'identification_document': _('Documento de identificação'),
    'department': _('Departamento'),
    'regional': _('Regional'),
    'role_type': _('Tipo de cargo'),
    'position': _('Cargo'),
    'sex': _('Sexo'),
    'birth_date': _('Data de Nascimento'),
    'hire_date': _('Data de Admissão'),
    'status': _('Status'),
    'city': _('Cidade'),
    'state': _('Estado'),
    'country': _('País'),
}
BLOCKING_FIELDS = {'name', 'email', 'phone', 'identification_document'}


@login_required
def member_list(request):
    """Lista de Membros"""
    user = request.user
    
    # Super Admin vê todos, Admin Empresa vê apenas da sua empresa
    if user.is_super_admin():
        members = CompanyMember.objects.select_related('company').all()
    elif user.is_admin_company() and user.company:
        members = CompanyMember.objects.filter(company=user.company)
    else:
        messages.error(request, _('Acesso negado.'))
        return redirect('dashboard')
    
    # Filtros
    search = request.GET.get('search', '')
    company = request.GET.get('company', '')
    status = request.GET.get('status', '')
    chatbot = request.GET.get('chatbot', '')
    
    if search:
        members = members.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(identification_document__icontains=search) |
            Q(department__icontains=search) |
            Q(phone__icontains=search)
        )
    
    if company and user.is_super_admin():
        members = members.filter(company_id=company)
    
    if status:
        members = members.filter(status=status)
    
    if chatbot:
        members = members.filter(
            chatbot_accesses__chatbot_id=chatbot,
            chatbot_accesses__status='active'
        ).distinct()
    
    # Adicionar contagem de chatbots
    members = members.annotate(
        chatbot_count=Count('chatbot_accesses', filter=Q(chatbot_accesses__status='active'))
    )
    
    # Paginação
    paginator = Paginator(members, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estatísticas
    if user.is_super_admin():
        total_members = CompanyMember.objects.count()
        active_members = CompanyMember.objects.filter(status='active').count()
        pending_members = CompanyMember.objects.filter(status='pending').count()
        inactive_members = CompanyMember.objects.filter(status='inactive').count()
    else:
        total_members = user.company.members.count()
        active_members = user.company.members.filter(status='active').count()
        pending_members = user.company.members.filter(status='pending').count()
        inactive_members = user.company.members.filter(status='inactive').count()
    
    # Empresas e chatbots para filtros
    companies = Company.objects.filter(status='active').order_by('name') if user.is_super_admin() else []
    chatbots = Chatbot.objects.filter(status='active').order_by('name')
    
    context = {
        'page_title': _('Membros'),
        'members': page_obj,
        'companies': companies,
        'chatbots': chatbots,
        'search': search,
        'selected_company': company,
        'selected_status': status,
        'selected_chatbot': chatbot,
        'total_members': total_members,
        'active_members': active_members,
        'pending_members': pending_members,
        'inactive_members': inactive_members,
    }
    
    return render(request, 'members/list.html', context)


@login_required
def member_create(request):
    """Criar Membro"""
    user = request.user
    
    # Determinar a empresa
    if user.is_super_admin():
        company_id = request.GET.get('company')
        if not company_id:
            messages.error(request, _('Selecione uma empresa.'))
            return redirect('member_list')
        company = get_object_or_404(Company, pk=company_id)
    elif user.is_admin_company() and user.company:
        company = user.company
    else:
        messages.error(request, _('Acesso negado.'))
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CompanyMemberForm(request.POST, company=company)
        if form.is_valid():
            with transaction.atomic():
                member = form.save(commit=False)
                member.company = company
                try:
                    member.save()
                except IntegrityError:
                    error_message = _('Já existe um membro com este e-mail nesta empresa.')
                    form.add_error('email', error_message)
                    messages.error(request, error_message)
                    return render(request, template, {
                        'page_title': _('Novo Membro'),
                        'form': form,
                        'company': company,
                    })
                # Salvar chatbots selecionados
                link_member_to_admin_user(member)
                selected_chatbots = form.cleaned_data.get('chatbots', [])
                for chatbot in selected_chatbots:
                    MemberChatbotAccess.objects.create(
                        member=member,
                        chatbot=chatbot,
                        activation_date=timezone.now().date(),
                        status='active'
                    )
            
            messages.success(request, _('Membro criado com sucesso!'))
            return redirect('member_list')
    else:
        form = CompanyMemberForm(company=company)
    
    # Determinar template baseado no billing_mode
    if company.billing_mode == 'per_user':
        template = 'members/form_per_user.html'
    else:
        template = 'members/form_per_chatbot.html'
    
    context = {
        'page_title': _('Novo Membro'),
        'form': form,
        'company': company,
    }
    
    return render(request, template, context)


@login_required
def member_edit(request, pk):
    """Editar Membro"""
    user = request.user
    member = get_object_or_404(CompanyMember, pk=pk)
    
    # Verificar permissão
    if user.is_admin_company() and user.company != member.company:
        messages.error(request, _('Acesso negado.'))
        return redirect('member_list')
    
    company = member.company
    old_status = member.status
    
    if request.method == 'POST':
        form = CompanyMemberForm(request.POST, instance=member, company=company)
        if form.is_valid():
            member = form.save()
            link_member_to_admin_user(member)
            
            # Atualizar chatbots
            selected_chatbots = form.cleaned_data.get('chatbots', [])
            
            # Desativar acessos não selecionados
            removed_accesses = member.chatbot_accesses.exclude(chatbot__in=selected_chatbots)
            for access in removed_accesses:
                if access.status != 'inactive':
                    access.status = 'inactive'
                    access.save()
            
            # Criar ou reativar acessos selecionados
            for chatbot in selected_chatbots:
                access, created = MemberChatbotAccess.objects.get_or_create(
                    member=member,
                    chatbot=chatbot,
                    defaults={
                        'activation_date': timezone.now().date(),
                        'status': 'active'
                    }
                )
                if not created and access.status == 'inactive':
                    access.status = 'active'
                    access.activation_date = timezone.now().date()
                    access.save()
            
            # Registrar mudança de status
            if old_status != member.status:
                # Registrar no log de auditoria
                AuditLog.objects.create(
                    user=request.user,
                    action='member_status_changed',
                    description=f'Status de {member.name} alterado de {old_status} para {member.status}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            messages.success(request, _('Membro atualizado com sucesso!'))
            return redirect('member_list')
    else:
        form = CompanyMemberForm(instance=member, company=company)
    
    # Determinar template baseado no billing_mode
    if company.billing_mode == 'per_user':
        template = 'members/form_per_user.html'
    else:
        template = 'members/form_per_chatbot.html'
    
    context = {
        'page_title': _('Editar Membro'),
        'form': form,
        'member': member,
        'company': company,
    }
    
    return render(request, template, context)


@login_required
def member_delete(request, pk):
    """Deletar Membro"""
    user = request.user
    member = get_object_or_404(CompanyMember, pk=pk)
    
    # Verificar permissão
    if user.is_admin_company() and user.company != member.company:
        messages.error(request, _('Acesso negado.'))
        return redirect('member_list')
    
    if request.method == 'POST':
        member_name = member.name
        unlink_member_from_admin_user(member)
        member.delete()
        messages.success(request, _('Membro "{}" deletado com sucesso!').format(member_name))
        return redirect('member_list')
    
    context = {
        'page_title': _('Deletar Membro'),
        'member': member,
    }
    
    return render(request, 'members/delete_confirm.html', context)


@login_required
def member_import(request):
    """Importar Membros em Lote (CSV)"""
    user = request.user
    
    if user.is_admin_company() and user.company:
        company = user.company
    elif user.is_super_admin():
        company_id = request.GET.get('company')
        if not company_id:
            messages.error(request, _('Selecione uma empresa.'))
            return redirect('member_list')
        company = get_object_or_404(Company, pk=company_id)
    else:
        messages.error(request, _('Acesso negado.'))
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = MemberImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            is_valid, error_message = validate_csv_structure(csv_file)
            if not is_valid:
                messages.error(request, error_message)
                return redirect('member_import')
            
            try:
                # Parse CSV
                members_data = parse_csv_file(csv_file, company)
                
                # Salvar na sessão para preview (serializando datas)
                session_members_data = []
                for data in members_data:
                    serialized = data.copy()
                    hire_date = serialized.get('hire_date')
                    if isinstance(hire_date, (date, datetime)):
                        serialized['hire_date'] = hire_date.isoformat()
                    birth_date = serialized.get('birth_date')
                    if isinstance(birth_date, (date, datetime)):
                        serialized['birth_date'] = birth_date.isoformat()
                    serialized['errors'] = data.get('errors', {})
                    serialized['line_number'] = data.get('line_number')
                    session_members_data.append(serialized)
                
                request.session['import_preview'] = session_members_data
                request.session['import_company_id'] = company.id
                
                return redirect('member_import_preview')
                
            except Exception as e:
                messages.error(request, _('Erro ao processar CSV: {}').format(str(e)))
    else:
        form = MemberImportForm()
    
    context = {
        'page_title': _('Importar Membros'),
        'form': form,
        'company': company,
    }
    
    return render(request, 'members/import.html', context)


@login_required
def member_import_preview(request):
    """Preview de Importação de Membros"""
    raw_members_data = request.session.get('import_preview')
    company_id = request.session.get('import_company_id')
    
    if not raw_members_data or not company_id:
        messages.error(request, _('Nenhum dado para importar.'))
        return redirect('member_import')
    
    role_labels = dict(CompanyMember.ROLE_TYPE_CHOICES)
    sex_labels = dict(CompanyMember.SEX_CHOICES)
    members_data = []
    error_rows = []
    has_errors = False
    has_blocking_errors = False
    for item in raw_members_data:
        data = item.copy()
        hire_date = data.get('hire_date')
        if hire_date:
            try:
                data['hire_date'] = datetime.strptime(hire_date, '%Y-%m-%d').date()
            except ValueError:
                data['hire_date'] = None
        birth_date = data.get('birth_date')
        if birth_date:
            try:
                data['birth_date'] = datetime.strptime(birth_date, '%Y-%m-%d').date()
            except ValueError:
                data['birth_date'] = None
        role_type_value = data.get('role_type')
        data['role_type_display'] = role_labels.get(role_type_value, role_type_value)
        sex_value = data.get('sex')
        data['sex_display'] = sex_labels.get(sex_value, sex_value)
        errors = data.get('errors') or {}
        data['errors'] = errors
        row_error_messages = []
        for field, field_messages in errors.items():
            label = FIELD_LABELS.get(field, field)
            for message in field_messages:
                row_error_messages.append(f"{str(label)}: {message}")
        data['error_messages'] = row_error_messages
        if errors:
            has_errors = True
            if any(field in BLOCKING_FIELDS for field in errors):
                has_blocking_errors = True
            error_rows.append(data)
        members_data.append(data)
    
    company = get_object_or_404(Company, pk=company_id)
    
    if request.method == 'POST':
        # Confirmar importação
        success_count = 0
        error_count = 0
        
        for data in members_data:
            with transaction.atomic():
                try:
                    if data.get('errors'):
                        error_count += 1
                        continue
                    document_value = data.get('identification_document', '')
                    if not document_value:
                        error_count += 1
                        continue
                    if CompanyMember.objects.filter(identification_document=document_value).exists():
                        error_count += 1
                        continue

                    member = CompanyMember.objects.create(
                        company=company,
                        name=data['name'],
                        email=data['email'],
                        phone=data.get('phone', ''),
                        identification_document=document_value,
                        department=data.get('department', ''),
                        regional=data.get('regional', ''),
                        role_type=data.get('role_type') or '',
                        position=data.get('position', ''),
                        sex=data.get('sex') or '',
                        birth_date=data.get('birth_date'),
                        hire_date=data.get('hire_date'),
                        city=data.get('city', ''),
                        state=data.get('state', ''),
                        country=data.get('country', ''),
                        dealership=data.get('dealership', ''),
                        dealership_number=data.get('dealership_number', ''),
                        status=data.get('status', 'active')
                    )
                    link_member_to_admin_user(member)

                    chatbot_names = data.get('chatbots', '').split(',')
                    for chatbot_name in chatbot_names:
                        chatbot_name = chatbot_name.strip()
                        if chatbot_name:
                            try:
                                chatbot = Chatbot.objects.get(
                                    name=chatbot_name,
                                    status='active'
                                )
                                if company.company_chatbots.filter(chatbot=chatbot, status='active').exists():
                                    MemberChatbotAccess.objects.create(
                                        member=member,
                                        chatbot=chatbot,
                                        activation_date=timezone.now().date(),
                                        status='active'
                                    )
                            except Chatbot.DoesNotExist:
                                pass

                    success_count += 1

                except Exception as e:
                    error_count += 1
                    continue
        
        # Limpar sessão
        del request.session['import_preview']
        del request.session['import_company_id']
        
        messages.success(
            request,
            _('Importação concluída: {} sucesso, {} erros').format(success_count, error_count)
        )
        return redirect('member_list')
    
    context = {
        'page_title': _('Preview de Importação'),
        'members_data': members_data,
        'error_rows': error_rows,
        'has_errors': has_errors,
        'has_blocking_errors': has_blocking_errors,
        'company': company,
    }
    
    return render(request, 'members/import_preview.html', context)


@login_required
def member_export(request):
    """Exportar Membros (CSV)"""
    user = request.user
    
    # Determinar membros a exportar
    if user.is_super_admin():
        company_id = request.GET.get('company')
        if company_id:
            members = CompanyMember.objects.filter(company_id=company_id)
        else:
            members = CompanyMember.objects.all()
    elif user.is_admin_company() and user.company:
        members = CompanyMember.objects.filter(company=user.company)
    else:
        messages.error(request, _('Acesso negado.'))
        return redirect('dashboard')
    
    # Gerar CSV
    members = members.prefetch_related(
        Prefetch(
            'chatbot_accesses',
            queryset=MemberChatbotAccess.objects.filter(status='active').select_related('chatbot'),
            to_attr='_export_chatbot_accesses'
        )
    )
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="membros_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # BOM para UTF-8
    response.write('\ufeff')
    
    writer = csv.writer(response, delimiter=';')
    
    # Cabeçalho
    writer.writerow([
        'nome', 'email', 'telefone', 'documento_identificacao', 'departamento',
        'regional', 'tipo_cargo', 'cargo', 'sexo', 'data_nascimento', 'data_admissao',
        'cidade', 'estado', 'pais', 'dealership', 'dealership_number', 'status', 'chatbots'
    ])
    
    # Dados
    for member in members:
        chatbots = ','.join(
            acc.chatbot.name for acc in getattr(member, '_export_chatbot_accesses', [])
        )
        
        writer.writerow([
            member.name,
            member.email,
            member.phone,
            member.identification_document,
            member.department,
            member.regional,
            member.get_role_type_display() if member.role_type else '',
            member.position,
            member.get_sex_display() if member.sex else '',
            member.birth_date.strftime('%d/%m/%Y') if member.birth_date else '',
            member.hire_date.strftime('%d/%m/%Y') if member.hire_date else '',
            member.city,
            member.state,
            member.country,
            member.dealership,
            member.dealership_number,
            member.status,
            chatbots
        ])
    
    return response




