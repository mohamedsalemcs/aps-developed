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


class NoHTMLCacheMiddleware:
    """Stop the browser from serving a stale HTML document from cache, so a
    PLAIN refresh always shows the latest CMS edits (text + freshly-uploaded
    images, whose URLs change on upload). HTML pages are dynamic (DB-backed),
    so there's nothing to gain from caching them; CSS/JS keep caching but are
    cache-busted via ?v= (see core.context_processors.asset_version).

    Only text/html is touched — static assets, images, JSON, downloads are
    left alone so they still cache normally."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        ctype = response.get("Content-Type", "")
        if ctype.startswith("text/html") and not response.streaming:
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response
