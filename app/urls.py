from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    # Auth
    login_view, logout_view, password_reset_request,
    # Dashboard
    dashboard_view,
    # Companies
    company_list, company_create, company_edit, company_detail,
    company_delete, company_toggle_status,
    # Users
    user_list, user_create, user_edit, user_delete, user_toggle_status,
    # Chatbots
    chatbot_list, chatbot_create, chatbot_edit, chatbot_delete,
    chatbot_vincular, chatbot_desvincular, chatbot_meus_chatbots,
    # Members
    member_list, member_create, member_edit, member_delete,
    member_import, member_import_preview, member_export,
    # Billing
    billing_list, billing_generate, billing_preview, billing_detail,
    billing_export_csv, billing_export_excel, billing_export_pdf, billing_delete,
    # Settings
    system_settings_view, reset_theme, test_smtp, company_settings_view,
    user_profile_view, change_password,
)

urlpatterns = [
    # Autenticação
    path('', login_view, name='login'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('password-reset/', password_reset_request, name='password_reset'),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html'
        ),
        name='password_reset_confirm'
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
    
    # Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),
    
    # Empresas (Super Admin)
    path('companies/', company_list, name='company_list'),
    path('companies/create/', company_create, name='company_create'),
    path('companies/<int:pk>/', company_detail, name='company_detail'),
    path('companies/<int:pk>/edit/', company_edit, name='company_edit'),
    path('companies/<int:pk>/delete/', company_delete, name='company_delete'),
    path('companies/<int:pk>/toggle-status/', company_toggle_status, name='company_toggle_status'),
    
    # Usuários (Super Admin)
    path('users/', user_list, name='user_list'),
    path('users/create/', user_create, name='user_create'),
    path('users/<int:pk>/edit/', user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', user_delete, name='user_delete'),
    path('users/<int:pk>/toggle-status/', user_toggle_status, name='user_toggle_status'),
    
    # Chatbots (Super Admin)
    path('chatbots/', chatbot_list, name='chatbot_list'),
    path('chatbots/create/', chatbot_create, name='chatbot_create'),
    path('chatbots/<int:pk>/edit/', chatbot_edit, name='chatbot_edit'),
    path('chatbots/<int:pk>/delete/', chatbot_delete, name='chatbot_delete'),
    path('chatbots/<int:pk>/vincular/', chatbot_vincular, name='chatbot_vincular'),
    path('chatbots/<int:chatbot_pk>/desvincular/<int:company_pk>/', chatbot_desvincular, name='chatbot_desvincular'),
    
    # Meus Chatbots (Admin Empresa)
    path('meus-chatbots/', chatbot_meus_chatbots, name='chatbot_meus_chatbots'),
    
    # Membros
    path('members/', member_list, name='member_list'),
    path('members/create/', member_create, name='member_create'),
    path('members/<int:pk>/edit/', member_edit, name='member_edit'),
    path('members/<int:pk>/delete/', member_delete, name='member_delete'),
    path('members/import/', member_import, name='member_import'),
    path('members/import/preview/', member_import_preview, name='member_import_preview'),
    path('members/export/', member_export, name='member_export'),
    
    # Cobranças
    path('billing/', billing_list, name='billing_list'),
    path('billing/generate/', billing_generate, name='billing_generate'),
    path('billing/preview/', billing_preview, name='billing_preview'),
    path('billing/<int:pk>/', billing_detail, name='billing_detail'),
    path('billing/<int:pk>/export/csv/', billing_export_csv, name='billing_export_csv'),
    path('billing/<int:pk>/export/excel/', billing_export_excel, name='billing_export_excel'),
    path('billing/<int:pk>/export/pdf/', billing_export_pdf, name='billing_export_pdf'),
    path('billing/<int:pk>/delete/', billing_delete, name='billing_delete'),
    
    # Relatórios
    
    # Configurações
    path('settings/system/', system_settings_view, name='system_settings'),
    path('settings/system/reset-theme/', reset_theme, name='reset_theme'),
    path('settings/system/test-smtp/', test_smtp, name='test_smtp'),
    path('settings/company/', company_settings_view, name='company_settings'),
    path('settings/profile/', user_profile_view, name='user_profile'),
    path('settings/password/', change_password, name='change_password'),
]
