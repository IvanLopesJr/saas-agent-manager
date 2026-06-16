from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from .models import (
    Company, User, CompanyMember, Chatbot, CompanyChatbot,
    SystemSettings, MemberChatbotAccess
)
import csv
import io


class LoginForm(AuthenticationForm):
    """Formulário de Login"""
    username = forms.CharField(
        label=_('E-mail ou Usuário'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Digite seu e-mail ou usuário'),
            'autofocus': True
        })
    )
    password = forms.CharField(
        label=_('Senha'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Digite sua senha')
        })
    )
    remember_me = forms.BooleanField(
        label=_('Lembrar-me'),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def confirm_login_allowed(self, user):
        # Permitir que o backend trate status e outros bloqueios
        return


class CompanyForm(forms.ModelForm):
    """Formulário de Empresa"""
    
    class Meta:
        model = Company
        fields = [
            'name', 'email', 'phone', 'identification_document', 'address', 'logo_url',
            'currency', 'billing_mode', 'member_price', 'bill_admin_users',
            'charge_inactive_members', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('5511999999999')}),
            'identification_document': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': _('Documento (CNPJ, RFC, etc.)')}
            ),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'logo_url': forms.FileInput(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'billing_mode': forms.Select(attrs={'class': 'form-select'}),
            'member_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bill_admin_users': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'charge_inactive_members': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['identification_document'].label = _('Documento de identificação Fiscal')
        self.fields['identification_document'].widget.attrs['placeholder'] = _('Documento (CNPJ, RFC, etc.)')
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'


class UserForm(UserCreationForm):
    """Formulário de Usuário (Super Admin e Admin Empresa)"""
    send_credentials = forms.BooleanField(
        label=_('Enviar credenciais por e-mail'),
        required=False,
        help_text=_('Envie usuário e senha para o e-mail informado após salvar.'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    member_active = forms.BooleanField(
        label=_('Membro ativo'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input me-2'})
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'phone',
            'company', 'role', 'status', 'sync_member_profile',
            'password1', 'password2'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'sync_member_profile': forms.CheckboxInput(attrs={'class': 'form-check-input me-2'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Se não for Super Admin, não pode escolher empresa
        if self.user and not self.user.is_super_admin():
            self.fields['company'].widget = forms.HiddenInput()
            self.fields['company'].initial = self.user.company
            self.fields['role'].choices = [('admin_company', _('Admin da Empresa'))]
            self.initial.setdefault('role', 'admin_company')
        
        # Configurações específicas dos campos extras
        self.fields['sync_member_profile'].label = _('Considerar membro?')
        self.fields['sync_member_profile'].help_text = _(
            'Quando marcado, o administrador terá um registro de membro vinculado automaticamente.'
        )
        self.fields['member_active'].initial = True
        
        if self.is_bound:
            role_value = self.data.get('role')
        else:
            role_value = (
                self.initial.get('role')
                or getattr(self.instance, 'role', None)
                or self.fields['role'].initial
                or ''
            )
        self.show_member_options = role_value == 'admin_company'
        
        if self.instance and self.instance.pk:
            try:
                member = self.instance.member_profile
            except CompanyMember.DoesNotExist:
                member = None
            if member:
                self.fields['member_active'].initial = (member.status == 'active')
                self.fields['sync_member_profile'].initial = self.instance.sync_member_profile
        else:
            self.fields['sync_member_profile'].initial = True
        
        # Adicionar classes CSS aos campos de senha
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        company = cleaned_data.get('company')

        if role == 'admin_company' and not company:
            self.add_error('company', _('Selecione uma empresa para administradores de empresa.'))

        if role == 'super_admin':
            cleaned_data['company'] = None
            cleaned_data['sync_member_profile'] = False
            cleaned_data['member_active'] = False

        if role != 'admin_company':
            cleaned_data['sync_member_profile'] = False
            cleaned_data['member_active'] = False

        if not cleaned_data.get('sync_member_profile'):
            cleaned_data['member_active'] = False

        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            return username

        qs = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                _('Já existe um usuário com este nome de usuário.')
            )

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            return email

        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                _('Já existe um usuário com este e-mail.')
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')

        if not password and self.instance and self.instance.pk:
            # Restore original password when editing without changing it
            original = User.objects.get(pk=self.instance.pk)
            user.password = original.password

        if commit:
            user.save()
        return user


class CompanyMemberForm(forms.ModelForm):
    """Formulário de Membro da Empresa"""
    chatbots = forms.ModelMultipleChoiceField(
        queryset=Chatbot.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Chatbots com Acesso')
    )
    
    class Meta:
        model = CompanyMember
        fields = [
            'name', 'email', 'phone', 'identification_document', 'department',
            'regional', 'role_type', 'position', 'sex', 'birth_date', 'hire_date',
            'city', 'state', 'country', 'dealership', 'dealership_number', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Ex: 5511999999999')}),
            'identification_document': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Documento (CPF, DNI, etc.)')}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'regional': forms.TextInput(attrs={'class': 'form-control'}),
            'role_type': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'sex': forms.Select(attrs={'class': 'form-select'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'dealership': forms.TextInput(attrs={'class': 'form-control'}),
            'dealership_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if self.company:
            # Filtrar chatbots disponíveis para a empresa
            self.fields['chatbots'].queryset = Chatbot.objects.filter(
                company_chatbots__company=self.company,
                company_chatbots__status='active',
                status='active'
            )
            
            # Se estiver editando, marcar chatbots já selecionados
            if self.instance.pk:
                self.fields['chatbots'].initial = self.instance.chatbot_accesses.filter(
                    status='active'
                ).values_list('chatbot_id', flat=True)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and self.company:
            qs = CompanyMember.objects.filter(company=self.company, email__iexact=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    _('Já existe um membro com este e-mail nesta empresa.')
                )
        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if not phone:
            raise forms.ValidationError(_('Informe o telefone com DDI e apenas números (ex: 5511999999999).'))
        if not phone.isdigit():
            raise forms.ValidationError(_('Informe o telefone com DDI e apenas números (ex: 5511999999999).'))
        if len(phone) < 11:
            raise forms.ValidationError(_('Telefone deve ter no mínimo 11 dígitos.'))
        return phone


class ChatbotForm(forms.ModelForm):
    """Formulário de Chatbot"""
    
    class Meta:
        model = Chatbot
        fields = ['name', 'description', 'base_price', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class CompanyChatbotForm(forms.ModelForm):
    """Formulário de Vínculo Empresa-Chatbot"""
    companies = forms.ModelMultipleChoiceField(
        queryset=Company.objects.filter(status='active'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Empresas')
    )
    
    class Meta:
        model = CompanyChatbot
        fields = ['custom_price', 'status']
        widgets = {
            'custom_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': _('Deixe em branco para usar preço base')
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class SystemSettingsForm(forms.ModelForm):
    """Formulário de Configurações do Sistema"""

    class Meta:
        model = SystemSettings
        fields = [
            'system_name', 'logo_url', 'custom_favicon', 'login_background_url',
            'primary_color', 'secondary_color', 'link_color',
            'light_color', 'page_background_color', 'list_item_background_color',
            'btn_primary_bg', 'btn_primary_text',
            'btn_secondary_bg', 'btn_secondary_text',
            'btn_success_bg', 'btn_success_text',
            'btn_info_bg', 'btn_info_text',
            'btn_warning_bg', 'btn_warning_text',
            'btn_danger_bg', 'btn_danger_text',
            'btn_filter_bg', 'btn_filter_text',
            'btn_clear_filter_bg', 'btn_clear_filter_text',
            'btn_export_bg', 'btn_export_text',
            'btn_import_bg', 'btn_import_text',
            'sidebar_bg', 'sidebar_text',
            'sidebar_active_bg', 'sidebar_active_text',
            'base_font_size', 'heading_font_size', 'sidebar_font_size', 'chart_title_font_size',
            'custom_domain', 'use_custom_domain', 'support_email', 'footer_text', 'show_footer_text',
            'billing_cutoff_day', 'default_bill_admin_users',
            'smtp_host', 'smtp_port', 'smtp_user', 'smtp_password'
        ]
        widgets = {
            'system_name': forms.TextInput(attrs={'class': 'form-control'}),
            'logo_url': forms.FileInput(attrs={'class': 'form-control'}),
            'custom_favicon': forms.FileInput(attrs={'class': 'form-control'}),
            'login_background_url': forms.FileInput(attrs={'class': 'form-control'}),
            'primary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'link_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'light_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'page_background_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'list_item_background_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_primary_bg': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_primary_text': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_secondary_bg': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_secondary_text': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_success_bg': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_success_text': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_info_bg': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_info_text': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_warning_bg': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_warning_text': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_danger_bg': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_danger_text': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_filter_bg': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_filter_text': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_clear_filter_bg': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_clear_filter_text': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_export_bg': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_export_text': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_import_bg': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'btn_import_text': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'sidebar_bg': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'sidebar_text': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'sidebar_active_bg': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'sidebar_active_text': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'base_font_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('16px')}),
            'heading_font_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('1.75rem')}),
            'sidebar_font_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('0.95rem')}),
            'chart_title_font_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('1.25rem')}),
            'custom_domain': forms.URLInput(attrs={'class': 'form-control', 'placeholder': _('https://app.suaempresa.com')}),
            'use_custom_domain': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'support_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('suporte@suaempresa.com')}),
            'footer_text': forms.TextInput(attrs={'class': 'form-control'}),
            'show_footer_text': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'billing_cutoff_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 28}),
            'default_bill_admin_users': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'smtp_host': forms.TextInput(attrs={'class': 'form-control'}),
            'smtp_port': forms.NumberInput(attrs={'class': 'form-control'}),
            'smtp_user': forms.TextInput(attrs={'class': 'form-control'}),
            'smtp_password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('smtp_password')
        if not password and self.instance and self.instance.pk:
            cleaned_data['smtp_password'] = self.instance.smtp_password
        return cleaned_data

    def clean_billing_cutoff_day(self):
        cutoff_day = self.cleaned_data.get('billing_cutoff_day')
        if cutoff_day is not None and cutoff_day > 28:
            raise forms.ValidationError(_('O dia de corte deve ser no máximo 28.'))
        return cutoff_day


class CompanySettingsForm(forms.ModelForm):
    """Formulário de Configurações da Empresa (Admin Empresa)"""
    
    class Meta:
        model = Company
        fields = ['name', 'address', 'phone', 'logo_url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'logo_url': forms.FileInput(attrs={'class': 'form-control'}),
        }


class MemberImportForm(forms.Form):
    """Formulário de Importação de Membros em Lote"""
    csv_file = forms.FileField(
        label=_('Arquivo CSV'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        }),
        help_text=_('Faça upload de um arquivo CSV com os dados dos membros')
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError(_('O arquivo deve ser um CSV (.csv)'))
        
        # Validar tamanho (máximo 5MB)
        if csv_file.size > 5 * 1024 * 1024:
            raise forms.ValidationError(_('O arquivo não pode ser maior que 5MB'))
        
        return csv_file


class BillingFilterForm(forms.Form):
    """Formulário de Filtro de Cobranças"""
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(status='active'),
        required=False,
        empty_label=_('Todas as Empresas'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    period_start = forms.DateField(
        required=False,
        label=_('Período Início'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    period_end = forms.DateField(
        required=False,
        label=_('Período Fim'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class BillingGenerateForm(forms.Form):
    """Formulário de Geração de Cobrança"""
    period_start = forms.DateField(
        label=_('Início do Período'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text=_('Data de início do período de cobrança')
    )
    period_end = forms.DateField(
        label=_('Fim do Período'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text=_('Data de fim do período de cobrança')
    )
    companies = forms.ModelMultipleChoiceField(
        queryset=Company.objects.filter(status='active'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Empresas'),
        help_text=_('Deixe em branco para gerar para todas as empresas ativas')
    )
    
    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get('period_start')
        period_end = cleaned_data.get('period_end')
        
        if period_start and period_end and period_start >= period_end:
            raise forms.ValidationError(
                _('A data de início deve ser anterior à data de fim')
            )
        
        return cleaned_data


class UserProfileForm(forms.ModelForm):
    """Formulário de Perfil do Usuário"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
