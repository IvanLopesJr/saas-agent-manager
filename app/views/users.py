from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from django.contrib import messages

from django.utils.translation import gettext_lazy as _

from django.core.paginator import Paginator

from django.db.models import Q

from django.core.mail import send_mail

from django.urls import reverse

from django.conf import settings

from django.template.loader import render_to_string

from ..models import User, Company, AuditLog
from ..utils.member_link import ensure_member_for_admin_user

from ..forms import UserForm

from ..utils.decorators import super_admin_required

from ..utils.system_settings import get_system_settings, build_system_absolute_uri

from ..utils.email_branding import get_branding_colors





@login_required
@super_admin_required
def user_list(request):
    """Lista de Usuários (Super Admin e Admin Empresa)"""
    users = User.objects.select_related('company').all()

    

    # Filtros

    search = request.GET.get('search', '')

    company = request.GET.get('company', '')

    role = request.GET.get('role', '')

    status = request.GET.get('status', '')

    

    if search:

        users = users.filter(

            Q(username__icontains=search) |

            Q(email__icontains=search) |

            Q(first_name__icontains=search) |

            Q(last_name__icontains=search)

        )

    

    if company:

        users = users.filter(company_id=company)

    

    if role:

        users = users.filter(role=role)

    

    if status:

        users = users.filter(status=status)

    

    # Paginação

    paginator = Paginator(users, 20)

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(page_number)

    

    # Empresas para filtro

    companies = Company.objects.filter(status='active').order_by('name')

    

    context = {
        'page_title': _('Usuários'),
        'users': page_obj,

        'companies': companies,

        'search': search,

        'selected_company': company,

        'selected_role': role,

        'selected_status': status,

    }

    

    return render(request, 'users/list.html', context)





@login_required
@super_admin_required
def user_create(request):
    """Criar Usuário"""
    if request.method == 'POST':

        form = UserForm(request.POST, user=request.user)

        if form.is_valid():

            user = form.save(commit=False)

            raw_password = form.cleaned_data['password1']

            user.set_password(raw_password)

            user.save()
            ensure_member_for_admin_user(
                user,
                form.cleaned_data.get('sync_member_profile', False),
                form.cleaned_data.get('member_active', False)
            )



            if form.cleaned_data.get('send_credentials'):

                if user.email:

                    try:

                        system_settings_obj = get_system_settings(apply_email=True)

                        system_name = system_settings_obj.system_name or _('Sistema Multi-Empresas')

                        login_url = build_system_absolute_uri(reverse('login'), request=request)

                        subject = _('%(system_name)s - Seus dados de acesso') % {'system_name': system_name}
                        logo_absolute_url = ''

                        if system_settings_obj.logo_url:

                            logo_absolute_url = build_system_absolute_uri(

                                system_settings_obj.logo_url.url,

                                request=request,

                            )

                        primary_color, primary_color_soft = get_branding_colors(system_settings_obj)

                        context = {
                            'system_name': system_name,
                            'login_url': login_url,
                            'username': user.username,
                            'password': raw_password,
                            'recipient_name': user.get_full_name() or user.username,
                            'support_email': system_settings_obj.support_email,
                            'logo_url': logo_absolute_url,
                            'primary_color': primary_color,
                            'primary_color_soft': primary_color_soft,

                            'footer_text': system_settings_obj.footer_text,

                            'show_footer_text': system_settings_obj.show_footer_text,

                        }

                        text_body = render_to_string('emails/user_credentials_email.txt', context)

                        html_body = render_to_string('emails/user_credentials_email.html', context)

                        from_email = system_settings_obj.smtp_user or settings.DEFAULT_FROM_EMAIL

                        send_mail(

                            subject,

                            text_body,

                            from_email,

                            [user.email],

                            fail_silently=False,

                            html_message=html_body,

                        )

                        messages.info(request, _('Credenciais enviadas por e-mail para o usuário.'))

                    except Exception as exc:

                        messages.warning(

                            request,

                            _('Usuário criado, mas ocorreu um erro ao enviar o e-mail: %(error)s') % {'error': exc}

                        )

                else:

                    messages.warning(

                        request,

                        _('Usuário criado, mas não foi possível enviar o e-mail porque o endereço não foi informado.')

                    )



            messages.success(request, _('Usuário criado com sucesso!'))
            

            # Registrar no log

            if user.role == 'super_admin':

                AuditLog.objects.create(

                    user=request.user,

                    action='super_admin_created',

                    description=f'Super Admin criado: {user.username}',

                    ip_address=request.META.get('REMOTE_ADDR')

                )

            

            return redirect('user_list')

    else:

        form = UserForm(user=request.user)

    

    context = {
        'page_title': _('Novo Usuário'),
        'form': form,

    }

    

    return render(request, 'users/form.html', context)





@login_required
@super_admin_required
def user_edit(request, pk):
    """Editar Usuário"""
    user = get_object_or_404(User, pk=pk)

    

    if request.method == 'POST':

        form = UserForm(request.POST, instance=user, user=request.user)

        # Remove validação de senha para edição

        form.fields['password1'].required = False

        form.fields['password2'].required = False

        

        if form.is_valid():

            user = form.save(commit=False)

            

            # Atualizar senha se fornecida

            password = form.cleaned_data.get('password1')

            if password:

                user.set_password(password)

            

            user.save()
            ensure_member_for_admin_user(
                user,
                form.cleaned_data.get('sync_member_profile', False),
                form.cleaned_data.get('member_active', False)
            )

            messages.success(request, _('Usuário atualizado com sucesso!'))
            return redirect('user_list')

    else:

        form = UserForm(instance=user, user=request.user)

        # Remove campos de senha para edição

        form.fields['password1'].required = False

        form.fields['password2'].required = False

    

    context = {
        'page_title': _('Editar Usuário'),
        'form': form,

        'user_obj': user,

    }

    

    return render(request, 'users/form.html', context)





@login_required
@super_admin_required
def user_delete(request, pk):
    """Deletar Usuário"""
    user = get_object_or_404(User, pk=pk)

    

    # Não permitir deletar a si mesmo

    if user == request.user:

        messages.error(request, _('Você não pode deletar seu próprio usuário!'))

        return redirect('user_list')

    

    if request.method == 'POST':

        username = user.username

        user.delete()

        messages.success(request, _('Usuário "{}" deletado com sucesso!').format(username))
        return redirect('user_list')

    

    context = {
        'page_title': _('Deletar Usuário'),
        'user_obj': user,

    }

    

    return render(request, 'users/delete_confirm.html', context)





@login_required
@super_admin_required
@require_POST
def user_toggle_status(request, pk):
    """Ativar/Inativar Usuário"""
    user = get_object_or_404(User, pk=pk)

    

    # Não permitir inativar a si mesmo

    if user == request.user:

        messages.error(request, _('Você não pode inativar seu próprio usuário!'))

        return redirect('user_list')

    

    if user.status == 'active':

        user.status = 'inactive'

        messages.success(request, _('Usuário inativado com sucesso!'))
    else:
        user.status = 'active'
        messages.success(request, _('Usuário ativado com sucesso!'))
    

    user.save()

    

    return redirect('user_list')

