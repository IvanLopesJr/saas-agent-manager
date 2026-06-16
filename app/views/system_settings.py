from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_POST
from ..models import SystemSettings, AuditLog
from ..forms import SystemSettingsForm, CompanySettingsForm, UserProfileForm
from ..utils.decorators import super_admin_required
from ..utils.system_settings import get_system_settings


@login_required
@super_admin_required
def system_settings_view(request):
    """Configurações do Sistema (Super Admin)"""
    settings_obj = SystemSettings.get_settings()
    
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            get_system_settings(apply_email=True)
            messages.success(request, _('Configurações atualizadas com sucesso!'))
            
            AuditLog.objects.create(
                user=request.user,
                action='settings_updated',
                description='Configurações do sistema atualizadas',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return redirect('system_settings')
    else:
        form = SystemSettingsForm(instance=settings_obj)
    
    smtp_configured = bool(settings_obj.smtp_host and settings_obj.get_smtp_password())
    
    context = {
        'page_title': _('Configurações do Sistema'),
        'form': form,
        'settings': settings_obj,
        'smtp_configured': smtp_configured,
    }
    
    return render(request, 'settings/system.html', context)


@login_required
@super_admin_required
@require_POST
def reset_theme(request):
    """Restaurar cores e tipografia para o padrão"""
    settings_obj = SystemSettings.get_settings()
    settings_obj.reset_theme_defaults()
    get_system_settings(apply_email=True)
    messages.info(request, _('Cores e tipografia restauradas para o padrão.'))
    return redirect('system_settings')


@login_required
@super_admin_required
@require_POST
def test_smtp(request):
    """Testar Configurações SMTP"""
    settings_obj = SystemSettings.get_settings()
    
    if not settings_obj.smtp_host or not settings_obj.smtp_user:
        messages.error(request, _('Configure o SMTP antes de testar.'))
        return redirect('system_settings')
    
    try:
        # Configurar temporariamente as configurações de email
        from django.core.mail import get_connection
        
        connection = get_connection(
            host=settings_obj.smtp_host,
            port=settings_obj.smtp_port,
            username=settings_obj.smtp_user,
            password=settings_obj.get_smtp_password(),
            use_tls=True,
        )
        
        # Enviar email de teste
        send_mail(
            subject=_('Teste SMTP - Sistema Multi-Empresas'),
            message='Este é um email de teste do sistema.',
            from_email=settings_obj.smtp_user,
            recipient_list=[request.user.email],
            connection=connection,
        )
        
        messages.success(request, _('Email de teste enviado com sucesso!'))
    except Exception as e:
        messages.error(request, _('Erro ao enviar email: {}').format(str(e)))
    
    return redirect('system_settings')


@login_required
def company_settings_view(request):
    """Configurações da Empresa (Admin Empresa)"""
    user = request.user
    
    if not user.is_admin_company() or not user.company:
        messages.error(request, _('Acesso negado.'))
        return redirect('dashboard')
    
    company = user.company
    
    if request.method == 'POST':
        form = CompanySettingsForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, _('Configurações da empresa atualizadas com sucesso!'))
            return redirect('company_settings')
    else:
        form = CompanySettingsForm(instance=company)
    
    context = {
        'page_title': _('Configurações da Empresa'),
        'form': form,
        'company': company,
    }
    
    return render(request, 'settings/company.html', context)


@login_required
def user_profile_view(request):
    """Perfil do Usuário"""
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Perfil atualizado com sucesso!'))
            return redirect('user_profile')
    else:
        form = UserProfileForm(instance=user)
    
    context = {
        'page_title': _('Meu Perfil'),
        'form': form,
    }
    
    return render(request, 'settings/profile.html', context)


@login_required
def change_password(request):
    """Alterar Senha"""
    from django.contrib.auth.forms import PasswordChangeForm
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            messages.success(request, _('Senha alterada com sucesso!'))
            return redirect('user_profile')
        else:
            messages.error(request, _('Erro ao alterar senha. Verifique os dados.'))
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'page_title': _('Alterar Senha'),
        'form': form,
    }
    
    return render(request, 'settings/change_password.html', context)
