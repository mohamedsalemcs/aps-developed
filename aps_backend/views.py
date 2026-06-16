"""Page views that serve the designer's templates with DB-backed context.

Most pages are plain TemplateViews (site-wide data comes from the
core.context_processors.site_globals processor). FAQ and the SPS/AZOLIS
division pages need their own querysets, so they get dedicated views.
The EN and AR templates share the same context — each template renders the
matching `_en` / `_ar` fields.
"""
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404

from faq.models import FAQItem
from divisions.models import Division


class FAQView(TemplateView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["faq_items"] = FAQItem.objects.all()
        return ctx


class DivisionView(TemplateView):
    """Serves a division page, injecting that division + its project cards."""
    division_slug = None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        division = get_object_or_404(Division, slug=self.division_slug)
        if division.status != "published":   # hidden/draft division -> not public
            from django.http import Http404
            raise Http404("division not published")
        ctx["division"] = division
        ctx["current_division"] = self.division_slug   # for nav aria-current
        ctx["projects"] = division.projects.all()
        cards = {}
        for c in division.cards.all():
            cards.setdefault(c.section_key, []).append(c)
        ctx["cards"] = cards
        # section keys the editor marked hidden -> the public template skips them
        extra = division.cms_extra or {}
        ctx["division_hidden"] = [k for k, v in (extra.get("hidden") or {}).items() if v]
        # per-division SEO (stored in cms_extra.seo as {title:{en,ar}, desc:{en,ar}})
        is_ar = self.request.path.startswith("/ar/")
        seo = (division.cms_extra or {}).get("seo") or {}
        def _r(v):
            return ((v.get("ar") if is_ar else v.get("en")) or "") if isinstance(v, dict) else (v or "")
        ctx["pg_seo"] = {"title": _r(seo.get("title")), "desc": _r(seo.get("desc"))}
        return ctx


class ContactView(TemplateView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sent"] = self.request.GET.get("sent") == "1"
        return ctx
