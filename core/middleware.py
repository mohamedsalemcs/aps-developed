from django.shortcuts import render
from .models import SiteSettings

# paths that stay reachable while the public site is in maintenance mode
_ALLOW_PREFIXES = ("/cms/", "/static/", "/media/", "/website/", "/django-admin/")


class MaintenanceMiddleware:
    """When SiteSettings.maintenance_mode is ON, the public site shows a
    maintenance page (HTTP 503); the CMS (/cms/) and assets stay reachable so
    the client can turn it back off. Wires the settings 'maintenance' toggle."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not path.startswith(_ALLOW_PREFIXES):
            if SiteSettings.load().maintenance_mode:
                return render(request, "maintenance.html", status=503)
        return self.get_response(request)
