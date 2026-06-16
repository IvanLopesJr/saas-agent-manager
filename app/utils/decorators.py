"""
Custom decorators for permission checking
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _


def super_admin_required(view_func):
    """Decorator to require Super Admin role"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not request.user.is_super_admin():
            messages.error(request, _('Acesso negado. Apenas Super Admins podem acessar esta página.'))
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def admin_company_required(view_func):
    """Decorator to require Admin Company role"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not request.user.is_admin_company():
            messages.error(request, _('Acesso negado. Apenas Admins de Empresa podem acessar esta página.'))
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def company_required(view_func):
    """Decorator to require user to have a company"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not request.user.company:
            messages.error(request, _('Você precisa estar associado a uma empresa.'))
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def ajax_required(view_func):
    """Decorator to require AJAX requests"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            messages.error(request, _('Esta requisição deve ser feita via AJAX.'))
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
