
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.forms import PasswordResetForm
from django.conf import settings
from django.core.cache import cache
from django.views.decorators.http import require_POST
from ..forms import LoginForm
from ..models import AuditLog
from ..utils.system_settings import get_system_settings, build_system_absolute_uri
from ..utils.email_branding import get_branding_colors


LOGIN_ATTEMPT_PREFIX = 'login_attempt_'
MAX_LOGIN_ATTEMPTS = 5
LOGIN_BLOCK_MINUTES = 15


def get_client_ip(request):
    """Obtém o IP do cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR') if getattr(settings, 'USE_X_FORWARDED_FOR', False) else None
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def login_view(request):
    """View de Login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()
        cache_key = f'{LOGIN_ATTEMPT_PREFIX}{get_client_ip(request)}'
        attempts = cache.get(cache_key, 0)
        form = LoginForm(request, data=request.POST)

        if attempts >= MAX_LOGIN_ATTEMPTS:
            messages.error(request, _('Muitas tentativas de login. Tente novamente em {} minutos.').format(LOGIN_BLOCK_MINUTES))
            return render(request, 'login.html', {'form': form, 'page_title': _('Login')})

        if form.is_valid():
            remember_me = form.cleaned_data.get('remember_me')
            user = form.get_user()
            
            if user is not None:
                company_is_active = not user.company_id or user.company.status == 'active'
                if user.status == 'active' and company_is_active:
                    cache.delete(cache_key)
                    login(request, user)
                    user.last_login = timezone.now()
                    user.save(update_fields=['last_login'])
                    
                    # Configurar sessão
                    if not remember_me:
                        request.session.set_expiry(0)
                    
                    messages.success(request, _('Login realizado com sucesso!'))
                    
                    # Redirecionar para próxima página ou dashboard
                    next_url = request.GET.get('next', 'dashboard')
                    if not url_has_allowed_host_and_scheme(
                        next_url,
                        allowed_hosts={request.get_host()},
                        require_https=request.is_secure()
                    ):
                        next_url = 'dashboard'
                    return redirect(next_url)
                else:
                    messages.error(request, _('Usuário ou empresa inativa. Contate o administrador.'))
                    
                    # Registrar tentativa de login com usuário inativo
                    AuditLog.objects.create(
                        user=user,
                        action='login_failed',
                        description=f'Tentativa de login com usuário inativo: {identifier}',
                        ip_address=get_client_ip(request)
                    )
            else:
                messages.error(request, _('Usuário ou senha incorretos.'))
                
                # Registrar tentativa de login falhada
                AuditLog.objects.create(
                    action='login_failed',
                    description=f'Tentativa de login falhada: {identifier}',
                    ip_address=get_client_ip(request)
                )
                cache.set(cache_key, attempts + 1, LOGIN_BLOCK_MINUTES * 60)
        else:
            messages.error(request, _('Usuário ou senha incorretos.'))
            AuditLog.objects.create(
                action='login_failed',
                description=f'Tentativa de login falhada: {identifier}',
                ip_address=get_client_ip(request)
            )
            cache.set(cache_key, attempts + 1, LOGIN_BLOCK_MINUTES * 60)
    else:
        form = LoginForm()
    
    context = {
        'form': form,
        'page_title': _('Login'),
    }
    return render(request, 'login.html', context)


@login_required
@require_POST
def logout_view(request):
    """View de Logout"""
    logout(request)
    messages.success(request, _('Logout realizado com sucesso!'))
    return redirect('login')


def password_reset_request(request):

    """View de Requisição de Reset de Senha"""

    if request.method == 'POST':

        form = PasswordResetForm(request.POST)

        if form.is_valid():

            system_settings_obj = get_system_settings(apply_email=True)
            primary_color, primary_color_soft = get_branding_colors(system_settings_obj)
            logo_absolute_url = ''
            if system_settings_obj.logo_url:
                logo_absolute_url = build_system_absolute_uri(
                    system_settings_obj.logo_url.url,
                    request=request,
                )

            form.save(

                request=request,

                use_https=request.is_secure(),

                from_email=settings.DEFAULT_FROM_EMAIL or system_settings_obj.smtp_user,

                email_template_name='registration/password_reset_email.txt',
                html_email_template_name='registration/password_reset_email.html',

                subject_template_name='registration/password_reset_subject.txt',

                extra_email_context={

                    'system_name': system_settings_obj.system_name,

                    'support_email': system_settings_obj.support_email,
                    'logo_url': logo_absolute_url,
                    'footer_text': system_settings_obj.footer_text,
                    'show_footer_text': system_settings_obj.show_footer_text,
                    'primary_color': primary_color,
                    'primary_color_soft': primary_color_soft,

                },

            )

            messages.success(

                request,

                _('Enviamos instruções para redefinir sua senha. Verifique seu e-mail.')

            )

            return redirect('password_reset_done')

        messages.error(

            request,

            _('Não foi possível processar sua solicitação. Verifique o e-mail informado.')

        )

    else:
        prefilled_email = request.GET.get('email', '').strip()
        if prefilled_email:
            form = PasswordResetForm(initial={'email': prefilled_email})
        else:
            form = PasswordResetForm()



    context = {

        'form': form,

        'page_title': _('Redefinir Senha'),

    }

    return render(request, 'registration/password_reset_form.html', context)
