import base64
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from cryptography.fernet import Fernet
from django.conf import settings as django_settings


def _get_fernet():
    key = base64.urlsafe_b64encode(
        django_settings.SECRET_KEY.encode()[:32].ljust(32, b'\0')
    )
    return Fernet(key)


class Company(models.Model):
    """Modelo de Empresa"""
    CURRENCY_CHOICES = [
        ('BRL', _('Real Brasileiro (R$)')),
        ('USD', _('Dólar Americano ($)')),
        ('EUR', _('Euro (€)')),
        ('MXN', _('Peso Mexicano ($)')),
    ]
    
    BILLING_MODE_CHOICES = [
        ('per_user', _('Por Usuário')),
        ('per_user_chatbot', _('Por Usuário/Chatbot')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Ativo')),
        ('inactive', _('Inativo')),
    ]
    
    name = models.CharField(_('Nome'), max_length=200)
    email = models.EmailField(_('E-mail'))
    phone = models.CharField(_('Telefone'), max_length=20, blank=True)
    identification_document = models.CharField(
        _('Documento de identificação Fiscal'),
        max_length=50,
        unique=True
    )
    address = models.TextField(_('Endereço'), blank=True)
    logo_url = models.ImageField(_('Logo'), upload_to='companies/logos/', blank=True, null=True)
    member_price = models.DecimalField(
        _('Preço por Membro'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_('Usado quando billing_mode = per_user')
    )
    bill_admin_users = models.BooleanField(_('Cobra Admin da Empresa'), default=False)
    currency = models.CharField(_('Moeda'), max_length=3, choices=CURRENCY_CHOICES, default='BRL')
    currency_symbol = models.CharField(_('Símbolo da Moeda'), max_length=5, default='R$')
    billing_mode = models.CharField(
        _('Modo de Cobrança'),
        max_length=20,
        choices=BILLING_MODE_CHOICES,
        default='per_user'
    )
    charge_inactive_members = models.BooleanField(
        _('Cobrar membros sem chatbot'),
        default=False,
        help_text=_('Quando ativo, membros sem acesso a chatbot também são cobrados (modo per_user)')
    )
    status = models.CharField(_('Status'), max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    first_cycle_price_snapshot = models.DecimalField(
        _('Snapshot de Preço (1º ciclo)'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    first_cycle_completed = models.BooleanField(
        _('Primeiro ciclo concluído'),
        default=False
    )
    
    class Meta:
        verbose_name = _('Empresa')
        verbose_name_plural = _('Empresas')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Auto-set currency_symbol based on currency
        currency_symbols = {
            'BRL': 'R$',
            'USD': '$',
            'EUR': '€',
            'MXN': '$',
        }
        if not self.currency_symbol or self.currency_symbol == 'R$':
            self.currency_symbol = currency_symbols.get(self.currency, 'R$')
        super().save(*args, **kwargs)


class User(AbstractUser):
    """Modelo de Usuário Customizado (Super Admin e Admin Empresa)"""
    ROLE_CHOICES = [
        ('super_admin', _('Super Admin')),
        ('admin_company', _('Admin da Empresa')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Ativo')),
        ('inactive', _('Inativo')),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True,
        verbose_name=_('Empresa')
    )
    email = models.EmailField(_('E-mail'), unique=True)
    phone = models.CharField(_('Telefone'), max_length=20, blank=True)
    role = models.CharField(_('Papel'), max_length=20, choices=ROLE_CHOICES, default='admin_company')
    status = models.CharField(_('Status'), max_length=10, choices=STATUS_CHOICES, default='active')
    sync_member_profile = models.BooleanField(
        _('Considerar como membro'),
        default=True,
        help_text=_('Quando habilitado, cria ou atualiza um membro vinculado a este admin.')
    )
    last_login = models.DateTimeField(_('Último Login'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Usuário')
        verbose_name_plural = _('Usuários')
        ordering = ['username']
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
    
    def is_super_admin(self):
        return self.role == 'super_admin'
    
    def is_admin_company(self):
        return self.role == 'admin_company'

    def get_member_profile(self):
        """Retorna o membro vinculado a este usuário (ou None)."""
        try:
            return self.member_profile
        except CompanyMember.DoesNotExist:
            return None

    def clean(self):
        super().clean()
        if self.is_admin_company() and not self.company:
            raise ValidationError({
                'company': _('Admin da empresa precisa estar vinculado a uma empresa.')
            })

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        should_validate = (
            update_fields is None or
            any(field in update_fields for field in ('company', 'role', 'email'))
        )
        if self.role != 'admin_company':
            self.sync_member_profile = False
        if should_validate:
            self.full_clean()
        super().save(*args, **kwargs)


class CompanyMember(models.Model):
    """Membros da Empresa (usuários administrativos, sem login)"""
    STATUS_CHOICES = [
        ('active', _('Ativo')),
        ('inactive', _('Inativo')),
        ('pending', _('Pendente')),
    ]
    ROLE_TYPE_CHOICES = [
        ('management', _('Gerencial')),
        ('operational', _('Operacional')),
        ('technical', _('Técnico')),
        ('support', _('Suporte')),
        ('other', _('Outro')),
    ]
    SEX_CHOICES = [
        ('male', _('Masculino')),
        ('female', _('Feminino')),
        ('other', _('Outro')),
        ('prefer_not', _('Prefere não informar')),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='members',
        verbose_name=_('Empresa')
    )
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        related_name='member_profile',
        null=True,
        blank=True,
        verbose_name=_('Usuário Administrador')
    )
    name = models.CharField(_('Nome'), max_length=200)
    email = models.EmailField(_('E-mail'))
    phone = models.CharField(_('Telefone'), max_length=20, blank=True)
    department = models.CharField(_('Departamento'), max_length=100, blank=True)
    role_type = models.CharField(_('Tipo de cargo'), max_length=20, choices=ROLE_TYPE_CHOICES, blank=True)
    position = models.CharField(_('Cargo'), max_length=100, blank=True)
    sex = models.CharField(_('Sexo'), max_length=20, choices=SEX_CHOICES, blank=True)
    regional = models.CharField(_('Regional'), max_length=120, blank=True)
    identification_document = models.CharField(_('Documento de identificação'), max_length=50, unique=True)
    birth_date = models.DateField(_('Data de nascimento'), null=True, blank=True)
    hire_date = models.DateField(_('Data de Admissão'), null=True, blank=True)
    city = models.CharField(_('Cidade'), max_length=120, blank=True)
    state = models.CharField(_('Estado'), max_length=120, blank=True)
    country = models.CharField(_('País'), max_length=120, blank=True)
    dealership = models.CharField(_('Concessionária'), max_length=200, blank=True)
    dealership_number = models.CharField(_('Número da Concessionária'), max_length=50, blank=True)
    status = models.CharField(_('Status'), max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    first_cycle_price_snapshot = models.DecimalField(
        _('Snapshot de Preço (1º ciclo)'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    first_cycle_completed = models.BooleanField(
        _('Primeiro ciclo concluído'),
        default=False
    )
    
    class Meta:
        verbose_name = _('Membro da Empresa')
        verbose_name_plural = _('Membros da Empresa')
        ordering = ['name']
        unique_together = [['company', 'email']]
    
    def __str__(self):
        return f"{self.name} - {self.company.name}"

    def save(self, *args, **kwargs):
        previous_status = None
        if self.pk:
            previous_status = CompanyMember.objects.filter(pk=self.pk).values_list('status', flat=True).first()

        company_price = self.company.member_price if getattr(self, 'company', None) else None

        if self.status == 'active':
            became_active = previous_status != 'active'
            if (became_active or self.first_cycle_price_snapshot is None) and company_price is not None:
                self.first_cycle_price_snapshot = company_price
            if became_active:
                self.first_cycle_completed = False
        super().save(*args, **kwargs)


class Chatbot(models.Model):
    """Chatbots disponíveis no sistema"""
    STATUS_CHOICES = [
        ('active', _('Ativo')),
        ('inactive', _('Inativo')),
    ]
    
    name = models.CharField(_('Nome'), max_length=200)
    description = models.TextField(_('Descrição'), blank=True)
    base_price = models.DecimalField(
        _('Preço Base'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    status = models.CharField(_('Status'), max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    
    class Meta:
        verbose_name = _('Chatbot')
        verbose_name_plural = _('Chatbots')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class CompanyChatbot(models.Model):
    """Vínculo entre Empresa e Chatbot com preço customizado"""
    STATUS_CHOICES = [
        ('active', _('Ativo')),
        ('inactive', _('Inativo')),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='company_chatbots',
        verbose_name=_('Empresa')
    )
    chatbot = models.ForeignKey(
        Chatbot,
        on_delete=models.CASCADE,
        related_name='company_chatbots',
        verbose_name=_('Chatbot')
    )
    custom_price = models.DecimalField(
        _('Preço Customizado'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_('Deixe em branco para usar o preço base do chatbot')
    )
    status = models.CharField(_('Status'), max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    
    class Meta:
        verbose_name = _('Chatbot da Empresa')
        verbose_name_plural = _('Chatbots das Empresas')
        unique_together = [['company', 'chatbot']]
        ordering = ['company__name', 'chatbot__name']
    
    def __str__(self):
        return f"{self.chatbot.name} - {self.company.name}"

    def clean(self):
        super().clean()
        if self.custom_price is not None and self.custom_price <= Decimal('0.00'):
            raise ValidationError({
                'custom_price': _('O preço customizado deve ser maior que zero.')
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_price(self):
        """Retorna o preço customizado ou o preço base. Retorna 0 se inativo."""
        if self.status != 'active':
            return Decimal('0.00')
        return self.custom_price if self.custom_price else self.chatbot.base_price


class MemberChatbotAccess(models.Model):
    """Acesso de membros aos chatbots"""
    STATUS_CHOICES = [
        ('active', _('Ativo')),
        ('inactive', _('Inativo')),
    ]
    
    member = models.ForeignKey(
        CompanyMember,
        on_delete=models.CASCADE,
        related_name='chatbot_accesses',
        verbose_name=_('Membro')
    )
    chatbot = models.ForeignKey(
        Chatbot,
        on_delete=models.CASCADE,
        related_name='member_accesses',
        verbose_name=_('Chatbot')
    )
    activation_date = models.DateField(_('Data de Ativação'))
    deactivation_date = models.DateField(_('Data de Desativação'), null=True, blank=True)
    status = models.CharField(_('Status'), max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    first_cycle_price_snapshot = models.DecimalField(
        _('Snapshot de Preço (1º ciclo)'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    first_cycle_completed = models.BooleanField(
        _('Primeiro ciclo concluído'),
        default=False
    )
    
    class Meta:
        verbose_name = _('Acesso ao Chatbot')
        verbose_name_plural = _('Acessos aos Chatbots')
        unique_together = [['member', 'chatbot']]
        ordering = ['member__name', 'chatbot__name']
    
    def __str__(self):
        return f"{self.member.name} - {self.chatbot.name}"

    def clean(self):
        super().clean()
        if self.status != 'active' or not self.member_id or not self.chatbot_id:
            return
        if not CompanyChatbot.objects.filter(
            company=self.member.company,
            chatbot=self.chatbot,
            status='active'
        ).exists():
            raise ValidationError({
                'chatbot': _('O chatbot precisa estar vinculado e ativo para a empresa do membro.')
            })

    def _resolve_current_price(self):
        company = getattr(self.member, 'company', None)
        if not company:
            return self.chatbot.base_price
        company_chatbot = company.company_chatbots.filter(
            chatbot=self.chatbot,
            status='active'
        ).first()
        if company_chatbot:
            return company_chatbot.get_price()
        return self.chatbot.base_price

    def save(self, *args, **kwargs):
        self.full_clean()
        previous_status = None
        if self.pk:
            previous_status = MemberChatbotAccess.objects.filter(pk=self.pk).values_list('status', flat=True).first()

        if self.status == 'active':
            became_active = previous_status != 'active'
            self.deactivation_date = None
            if became_active or self.first_cycle_price_snapshot is None:
                self.first_cycle_price_snapshot = self._resolve_current_price()
            if became_active:
                self.first_cycle_completed = False
        else:
            if previous_status == 'active' and self.deactivation_date is None:
                from django.utils import timezone
                self.deactivation_date = timezone.now().date()

        super().save(*args, **kwargs)


class UserStatusHistory(models.Model):
    """Histórico de mudanças de status (users e company_members)"""
    STATUS_CHOICES = [
        ('active', _('Ativo')),
        ('inactive', _('Inativo')),
        ('pending', _('Pendente')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='status_history',
        null=True,
        blank=True,
        verbose_name=_('Usuário')
    )
    member = models.ForeignKey(
        CompanyMember,
        on_delete=models.CASCADE,
        related_name='status_history',
        null=True,
        blank=True,
        verbose_name=_('Membro')
    )
    status = models.CharField(_('Status'), max_length=10, choices=STATUS_CHOICES)
    date_start = models.DateField(_('Data Início'))
    date_end = models.DateField(_('Data Fim'), null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='status_changes_created',
        verbose_name=_('Criado por')
    )
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Histórico de Status')
        verbose_name_plural = _('Históricos de Status')
        ordering = ['-date_start']
    
    def __str__(self):
        target = self.user or self.member
        return f"{target} - {self.get_status_display()} ({self.date_start})"


class Billing(models.Model):
    """Cobrança mensal por empresa"""
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='billings',
        verbose_name=_('Empresa')
    )
    period_start = models.DateField(_('Início do Período'))
    period_end = models.DateField(_('Fim do Período'))
    total_value = models.DecimalField(
        _('Valor Total'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='billings_generated',
        verbose_name=_('Gerado por')
    )
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Cobrança')
        verbose_name_plural = _('Cobranças')
        ordering = ['-period_start', 'company__name']
        unique_together = [['company', 'period_start', 'period_end']]
    
    def __str__(self):
        return f"{self.company.name} - {self.period_start} a {self.period_end}"


class BillingDetail(models.Model):
    """Detalhes da cobrança (por usuário/membro/chatbot)"""
    BILLING_TYPE_CHOICES = [
        ('full', _('Integral')),
        ('proportional', _('Proporcional')),
    ]
    
    billing = models.ForeignKey(
        Billing,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name=_('Cobrança')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_details',
        verbose_name=_('Usuário')
    )
    member = models.ForeignKey(
        CompanyMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_details',
        verbose_name=_('Membro')
    )
    chatbot = models.ForeignKey(
        Chatbot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_details',
        verbose_name=_('Chatbot')
    )
    activation_date = models.DateField(_('Data de Ativação'))
    days_active = models.IntegerField(_('Dias Ativos'))
    daily_rate = models.DecimalField(
        _('Tarifa Diária'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    value = models.DecimalField(
        _('Valor'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    unit_price = models.DecimalField(
        _('Preço Unitário'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    billing_type = models.CharField(
        _('Tipo de Cobrança'),
        max_length=15,
        choices=BILLING_TYPE_CHOICES
    )
    
    class Meta:
        verbose_name = _('Detalhe da Cobrança')
        verbose_name_plural = _('Detalhes das Cobranças')
        ordering = ['billing', 'member__name']
    
    def __str__(self):
        target = self.user or self.member
        chatbot_info = f" - {self.chatbot.name}" if self.chatbot else ""
        return f"{self.billing} - {target}{chatbot_info}"


class SystemSettings(models.Model):
    """Configurações globais do sistema"""
    THEME_DEFAULTS = {
        'primary_color': '#007bff',
        'secondary_color': '#6c757d',
        'light_color': '#f8f9fa',
        'btn_primary_bg': '#0d6efd',
        'btn_primary_text': '#ffffff',
        'btn_secondary_bg': '#6c757d',
        'btn_secondary_text': '#ffffff',
        'btn_success_bg': '#198754',
        'btn_success_text': '#ffffff',
        'btn_info_bg': '#17a2b8',
        'btn_info_text': '#ffffff',
        'btn_warning_bg': '#ffc107',
        'btn_warning_text': '#212529',
        'btn_danger_bg': '#dc3545',
        'btn_danger_text': '#ffffff',
        'btn_filter_bg': '#0d6efd',
        'btn_filter_text': '#ffffff',
        'btn_clear_filter_bg': '#6c757d',
        'btn_clear_filter_text': '#ffffff',
        'btn_export_bg': '#0dcaf0',
        'btn_export_text': '#212529',
        'btn_import_bg': '#198754',
        'btn_import_text': '#ffffff',
        'link_color': '#0d6efd',
        'sidebar_bg': '#2c3e50',
        'sidebar_text': '#f8f9fa',
        'sidebar_active_bg': '#1f2d3d',
        'sidebar_active_text': '#ffffff',
        'base_font_size': '16px',
        'heading_font_size': '1.75rem',
        'sidebar_font_size': '0.95rem',
        'chart_title_font_size': '1.25rem',
        'page_background_color': '#f5f7fa',
        'list_item_background_color': '#ffffff',
    }
    billing_cutoff_day = models.IntegerField(
        _('Dia de Corte'),
        default=15,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text=_('Dia do mês para corte de cobrança integral')
    )
    default_bill_admin_users = models.BooleanField(
        _('Cobrar Admin da Empresa por Padrão'),
        default=False
    )
    smtp_host = models.CharField(_('SMTP Host'), max_length=200, blank=True)
    smtp_port = models.IntegerField(_('SMTP Port'), default=587)
    smtp_user = models.CharField(_('SMTP User'), max_length=200, blank=True)
    smtp_password = models.CharField(_('SMTP Password'), max_length=200, blank=True)
    primary_color = models.CharField(_('Cor Primária'), max_length=7, default='#007bff')
    secondary_color = models.CharField(_('Cor Secundária'), max_length=7, default='#6c757d')
    btn_primary_bg = models.CharField(_('Cor do Botão Primário'), max_length=7, default='#0d6efd', blank=True)
    btn_primary_text = models.CharField(_('Cor do Texto do Botão Primário'), max_length=7, default='#ffffff', blank=True)
    btn_secondary_bg = models.CharField(_('Cor do Botão Secundário'), max_length=7, default='#6c757d', blank=True)
    btn_secondary_text = models.CharField(_('Cor do Texto do Botão Secundário'), max_length=7, default='#ffffff', blank=True)
    btn_success_bg = models.CharField(_('Cor do Botão de Sucesso'), max_length=7, default='#198754', blank=True)
    btn_success_text = models.CharField(_('Cor do Texto de Sucesso'), max_length=7, default='#ffffff', blank=True)
    btn_info_bg = models.CharField(_('Cor do Botão de Informação'), max_length=7, default='#17a2b8', blank=True)
    btn_info_text = models.CharField(_('Cor do Texto de Informação'), max_length=7, default='#ffffff', blank=True)
    btn_warning_bg = models.CharField(_('Cor do Botão de Alerta'), max_length=7, default='#ffc107', blank=True)
    btn_warning_text = models.CharField(_('Cor do Texto de Alerta'), max_length=7, default='#212529', blank=True)
    btn_danger_bg = models.CharField(_('Cor do Botão de Perigo'), max_length=7, default='#dc3545', blank=True)
    btn_danger_text = models.CharField(_('Cor do Texto de Perigo'), max_length=7, default='#ffffff', blank=True)
    btn_filter_bg = models.CharField(_('Cor do Botão de Filtro'), max_length=7, default='#0d6efd', blank=True)
    btn_filter_text = models.CharField(_('Cor do Texto do Botão de Filtro'), max_length=7, default='#ffffff', blank=True)
    btn_clear_filter_bg = models.CharField(
        _('Cor do Botão de Limpar Filtros'),
        max_length=7,
        default='#6c757d',
        blank=True,
    )
    btn_clear_filter_text = models.CharField(
        _('Cor do Texto do Botão de Limpar Filtros'),
        max_length=7,
        default='#ffffff',
        blank=True,
    )
    btn_export_bg = models.CharField(_('Cor do Botão de Exportação'), max_length=7, default='#0dcaf0', blank=True)
    btn_export_text = models.CharField(_('Cor do Texto do Botão de Exportação'), max_length=7, default='#212529', blank=True)
    btn_import_bg = models.CharField(_('Cor do Botão de Importação'), max_length=7, default='#198754', blank=True)
    btn_import_text = models.CharField(_('Cor do Texto do Botão de Importação'), max_length=7, default='#ffffff', blank=True)
    link_color = models.CharField(_('Cor dos Links'), max_length=7, default='#0d6efd', blank=True)
    sidebar_bg = models.CharField(_('Cor do Fundo do Sidebar'), max_length=7, default='#2c3e50', blank=True)
    sidebar_text = models.CharField(_('Cor do Texto do Sidebar'), max_length=7, default='#f8f9fa', blank=True)
    sidebar_active_bg = models.CharField(_('Cor do Item Ativo do Sidebar'), max_length=7, default='#1f2d3d', blank=True)
    sidebar_active_text = models.CharField(_('Cor do Texto Ativo do Sidebar'), max_length=7, default='#ffffff', blank=True)
    base_font_size = models.CharField(_('Tamanho Base da Fonte'), max_length=10, default='16px', blank=True)
    heading_font_size = models.CharField(_('Tamanho da Fonte dos Títulos'), max_length=10, default='1.75rem', blank=True)
    sidebar_font_size = models.CharField(_('Tamanho da Fonte do Sidebar'), max_length=10, default='0.95rem', blank=True)
    chart_title_font_size = models.CharField(_('Tamanho dos Títulos de Gráficos'), max_length=10, default='1.25rem', blank=True)
    light_color = models.CharField(_('Cor Clara (cards, cabeçalhos)'), max_length=7, default='#f8f9fa', blank=True)
    page_background_color = models.CharField(_('Cor de Fundo das Páginas'), max_length=7, default='#f5f7fa', blank=True)
    list_item_background_color = models.CharField(
        _('Cor de Fundo das Linhas de Tabela'),
        max_length=7,
        default='#ffffff',
        blank=True,
    )
    custom_favicon = models.ImageField(_('Favicon Personalizado'), upload_to='system/', blank=True, null=True)
    custom_domain = models.URLField(_('Domínio personalizado'), max_length=255, blank=True)
    use_custom_domain = models.BooleanField(_('Usar domínio personalizado'), default=False)
    system_name = models.CharField(_('Nome do Sistema'), max_length=200, default='Sistema Multi-Empresas')
    logo_url = models.ImageField(_('Logo do Sistema'), upload_to='system/', blank=True, null=True)
    login_background_url = models.ImageField(
        _('Background Login'),
        upload_to='system/',
        blank=True,
        null=True
    )
    support_email = models.EmailField(_('E-mail de suporte'), max_length=254, blank=True)
    footer_text = models.CharField(_('Texto do Rodapé'), max_length=255, blank=True)
    show_footer_text = models.BooleanField(_('Exibir texto do rodapé'), default=False)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    
    class Meta:
        verbose_name = _('Configuração do Sistema')
        verbose_name_plural = _('Configurações do Sistema')
    
    def __str__(self):
        return str(_('Configurações do Sistema'))

    @classmethod
    def get_settings(cls):
        """Retorna as configurações do sistema (singleton)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = SystemSettings.objects.get(pk=self.pk)
                if old.smtp_password != self.smtp_password:
                    self.smtp_password = self._encrypt_password(self.smtp_password)
            except SystemSettings.DoesNotExist:
                if self.smtp_password:
                    self.smtp_password = self._encrypt_password(self.smtp_password)
        else:
            if self.smtp_password:
                self.smtp_password = self._encrypt_password(self.smtp_password)
        super().save(*args, **kwargs)

    def reset_theme_defaults(self):
        for field, value in self.THEME_DEFAULTS.items():
            setattr(self, field, value)
        self.save(update_fields=list(self.THEME_DEFAULTS.keys()))

    @staticmethod
    def _encrypt_password(raw):
        if not raw:
            return ''
        return _get_fernet().encrypt(raw.encode()).decode()

    @staticmethod
    def _decrypt_password(encrypted):
        if not encrypted:
            return ''
        try:
            return _get_fernet().decrypt(encrypted.encode()).decode()
        except Exception:
            return encrypted

    def get_smtp_password(self):
        return self._decrypt_password(self.smtp_password)


class AuditLog(models.Model):
    """Log de auditoria simples (operações críticas)"""
    ACTION_CHOICES = [
        ('super_admin_created', _('Super Admin Criado')),
        ('company_created', _('Empresa Criada')),
        ('company_deleted', _('Empresa Deletada')),
        ('settings_updated', _('Configurações Atualizadas')),
        ('billing_generated', _('Cobrança Gerada')),
        ('member_price_changed', _('Preço de Membro Alterado')),
        ('login_failed', _('Login Falhou')),
        ('billing_mode_changed', _('Modo de Cobrança Alterado')),
        ('chatbot_linked', _('Chatbot Vinculado')),
        ('chatbot_unlinked', _('Chatbot Desvinculado')),
        ('member_status_changed', _('Status de Membro Alterado')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_('Usuário')
    )
    action = models.CharField(_('Ação'), max_length=50, choices=ACTION_CHOICES)
    description = models.TextField(_('Descrição'))
    ip_address = models.GenericIPAddressField(_('IP'), null=True, blank=True)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Log de Auditoria')
        verbose_name_plural = _('Logs de Auditoria')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.created_at}"
