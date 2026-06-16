"""
Audit middleware for logging critical actions
"""

from django.utils.translation import gettext as _
from ..models import AuditLog


class AuditMiddleware:
    """
    Middleware to automatically log critical actions
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._log_action(request, response)
        return response

    def _log_action(self, request, response):
        """Log certain actions after response"""

        if not request.user.is_authenticated:
            return

        path = request.path
        method = request.method

        if method not in ['POST', 'PUT', 'DELETE']:
            return

        if response.status_code >= 400:
            return

        action_mapping = {
            '/users/create/': 'super_admin_created',
            '/billing/generate/': 'billing_generated',
            '/companies/': 'member_price_changed',
            '/chatbots/': 'chatbot_linked',
        }

        for pattern, action in action_mapping.items():
            if pattern in path and method == 'POST':
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(',')[0]
                else:
                    ip_address = request.META.get('REMOTE_ADDR')

                try:
                    action_label = dict(AuditLog.ACTION_CHOICES).get(action, action)
                    description = _('%(username)s executou %(acao)s em %(rota)s') % {
                        'username': request.user.username,
                        'acao': str(action_label),
                        'rota': path,
                    }

                    AuditLog.objects.create(
                        user=request.user,
                        action=action,
                        description=description,
                        ip_address=ip_address
                    )
                except Exception:
                    pass

                break
