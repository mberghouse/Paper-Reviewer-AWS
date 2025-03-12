
from django.http import HttpResponseForbidden
import re

class SecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Compile patterns of suspicious URLs
        self.suspicious_patterns = re.compile(r'^/[a-zA-Z0-9]{5,10}$')

    def __call__(self, request):
        # Block suspicious patterns
        if self.suspicious_patterns.match(request.path) and request.path != '/favicon.ico':
            return HttpResponseForbidden('Access Denied')
        return self.get_response(request)

class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; img-src 'self' data: https:; font-src 'self' data: https:;"
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response

class StaticFileProtectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.protected_paths = [
            r'^/static/.*\.(py|js|jsx|ts|tsx)$',
            r'^/media/.*\.(py|js|jsx|ts|tsx)$'
        ]

    def __call__(self, request):
        path = request.path_info.lstrip('/')
        
        for pattern in self.protected_paths:
            if re.match(pattern, path):
                return HttpResponseForbidden()
                
        return self.get_response(request)