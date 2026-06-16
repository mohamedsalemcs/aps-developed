"""URL config for aps_backend.

Serves the designer's 18 pages (9 EN at root, 9 AR under /ar/). Most are plain
TemplateViews; FAQ / SPS / AZOLIS / Contact use DB-backed views (Phase 3).
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.static import serve

from .views import FAQView, DivisionView, ContactView
from submissions.views import contact_submit
from core.seo import sitemap_xml, robots_txt

from pathlib import Path
STATIC_SRC = str(Path(__file__).resolve().parent.parent / "static")

# url path segment -> template basename (same set for EN and AR)
PAGES = {
    "": "index",
    "about": "about",
    "sps": "sps",
    "beta-machinery": "beta-machinery",
    "envirosystems": "envirosystems",
    "advanced-green-solutions": "advanced-green-solutions",
    "azolis-middle-east": "azolis-middle-east",
    "faq": "faq",
    "contact": "contact",
}


# page name -> division slug (all 5 division pages are DB-backed now)
DIVISION_SLUG = {
    "sps": "sps", "beta-machinery": "beta", "envirosystems": "enviro",
    "advanced-green-solutions": "ags", "azolis-middle-east": "azolis",
}


def view_for(name, template):
    """Pick the DB-backed view for pages that need page-specific context,
    else a plain TemplateView."""
    if name == "faq":
        return FAQView.as_view(template_name=template)
    if name == "contact":
        return ContactView.as_view(template_name=template)
    if name in DIVISION_SLUG:
        return DivisionView.as_view(template_name=template, division_slug=DIVISION_SLUG[name])
    return TemplateView.as_view(template_name=template)


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("sitemap.xml", sitemap_xml, name="sitemap"),
    path("robots.txt", robots_txt, name="robots"),
    path("contact/submit/", contact_submit, name="contact-submit"),
    path("cms/", include("cmsadmin.urls")),
    # His admin.js builds image previews with a hardcoded '../../website/...'
    # prefix; from /cms/<page>/ that resolves to /website/... — serve it from
    # our static dir so his JS works unedited.
    re_path(r"^website/(?P<path>.*)$", serve, {"document_root": STATIC_SRC}),
]

# English at root, Arabic mirror under /ar/
for segment, name in PAGES.items():
    urlpatterns.append(
        path(segment if segment == "" else f"{segment}/",
             view_for(name, f"en/{name}.html"), name=f"en-{name}")
    )
for segment, name in PAGES.items():
    urlpatterns.append(
        path("ar/" if segment == "" else f"ar/{segment}/",
             view_for(name, f"ar/{name}.html"), name=f"ar-{name}")
    )
