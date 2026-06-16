"""
Middleware for Content-Security-Policy and other security headers.
"""

from django.conf import settings


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        csp_parts = []
        if hasattr(settings, 'CSP_DEFAULT_SRC') and settings.CSP_DEFAULT_SRC:
            for directive, sources in [
                ('default-src', getattr(settings, 'CSP_DEFAULT_SRC', None)),
                ('style-src', getattr(settings, 'CSP_STYLE_SRC', None)),
                ('script-src', getattr(settings, 'CSP_SCRIPT_SRC', None)),
                ('img-src', getattr(settings, 'CSP_IMG_SRC', None)),
                ('font-src', getattr(settings, 'CSP_FONT_SRC', None)),
                ('connect-src', getattr(settings, 'CSP_CONNECT_SRC', None)),
                ('frame-src', getattr(settings, 'CSP_FRAME_SRC', None)),
            ]:
                if sources:
                    csp_parts.append(f"{directive} {' '.join(sources)}")

        if csp_parts:
            response['Content-Security-Policy'] = '; '.join(csp_parts)

        return response
