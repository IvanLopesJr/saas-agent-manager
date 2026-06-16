from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    Company, User, CompanyMember, Chatbot, CompanyChatbot,
    MemberChatbotAccess, UserStatusHistory, Billing, BillingDetail,
    SystemSettings, AuditLog
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'identification_document', 'currency', 'billing_mode', 'status', 'created_at']
    list_filter = ['status', 'currency', 'billing_mode', 'created_at']
    search_fields = ['name', 'identification_document', 'email']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (_('Informações Básicas'), {
            'fields': ('name', 'email', 'phone', 'identification_document', 'address', 'logo_url', 'status')
        }),
        (_('Configurações de Cobrança'), {
            'fields': ('currency', 'currency_symbol', 'billing_mode', 'member_price', 'bill_admin_users')
        }),
        (_('Metadados'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'get_full_name', 'company', 'role', 'status', 'last_login']
    list_filter = ['role', 'status', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Informações Pessoais'), {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        (_('Empresa e Papel'), {'fields': ('company', 'role', 'status')}),
        (_('Permissões'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Datas Importantes'), {'fields': ('last_login', 'date_joined')}),
    )


@admin.register(CompanyMember)
class CompanyMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'company', 'department', 'status', 'created_at']
    list_filter = ['status', 'company', 'department', 'created_at']
    search_fields = ['name', 'email', 'identification_document']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Chatbot)
class ChatbotAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_price', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CompanyChatbot)
class CompanyChatbotAdmin(admin.ModelAdmin):
    list_display = ['company', 'chatbot', 'custom_price', 'status', 'created_at']
    list_filter = ['status', 'company', 'chatbot']
    search_fields = ['company__name', 'chatbot__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(MemberChatbotAccess)
class MemberChatbotAccessAdmin(admin.ModelAdmin):
    list_display = ['member', 'chatbot', 'activation_date', 'status']
    list_filter = ['status', 'chatbot', 'activation_date']
    search_fields = ['member__name', 'chatbot__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserStatusHistory)
class UserStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['get_target', 'status', 'date_start', 'date_end', 'created_by']
    list_filter = ['status', 'date_start']
    search_fields = ['user__username', 'member__name']
    readonly_fields = ['created_at']
    
    def get_target(self, obj):
        return obj.user or obj.member
    get_target.short_description = _('Alvo')


@admin.register(Billing)
class BillingAdmin(admin.ModelAdmin):
    list_display = ['company', 'period_start', 'period_end', 'total_value', 'generated_by', 'created_at']
    list_filter = ['period_start', 'company']
    search_fields = ['company__name']
    readonly_fields = ['created_at']


@admin.register(BillingDetail)
class BillingDetailAdmin(admin.ModelAdmin):
    list_display = ['billing', 'get_target', 'chatbot', 'activation_date', 'unit_price', 'value', 'billing_type']
    list_filter = ['billing_type', 'chatbot']
    search_fields = ['billing__company__name', 'member__name']
    
    def get_target(self, obj):
        return obj.user or obj.member
    get_target.short_description = _('Usuário/Membro')


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ['system_name', 'billing_cutoff_day', 'updated_at']
    readonly_fields = ['updated_at']
    
    def has_add_permission(self, request):
        # Apenas uma instância permitida
        return not SystemSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Não permitir deletar
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__username', 'description', 'ip_address']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
