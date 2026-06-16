"""Centralised SEO for the public site.

Produces one `seo` context dict per request — title, meta description, canonical,
hreflang alternates, Open Graph + Twitter, and JSON-LD structured data — so a
single include (templates/partials/seo.html) renders strong, consistent meta on
every public page. Per-page title/description come from the CMS first
(Page.seo_* / Division.cms_extra["seo"]); curated bilingual defaults fill the
gaps so the site ships search-ready even before the client edits anything.
"""
import json

from django.http import HttpResponse
from django.templatetags.static import static
from django.utils.html import escape

from .models import SiteSettings, SocialLink, Brand

SITE_NAME_EN = "Arabian Projects & Supplies (APS)"
SITE_NAME_AR = "المشاريع والتوريدات العربية (APS)"

# url segment (lang-stripped, no slashes) -> internal page key
_PUBLIC = {
    "": "home", "about": "about", "contact": "contact", "faq": "faq",
    "sps": "sps", "beta-machinery": "beta", "envirosystems": "enviro",
    "advanced-green-solutions": "ags", "azolis-middle-east": "azolis",
}
_DIV_KEYS = {"sps", "beta", "enviro", "ags", "azolis"}
_PAGE_KEYS = {"home", "about", "contact"}  # Page model rows with seo_* fields

# Curated, keyword-rich defaults (title <=~60 chars, description ~150-160).
# Used only when the CMS SEO field for that page/lang is empty.
PAGE_SEO = {
    "home": {
        "en": ("APS — Integrity-led Supply & Installation in Saudi Arabia",
               "Arabian Projects & Supplies (APS) is a diversified Saudi group delivering trading, supply and electro-mechanical installation through specialized divisions and global partners."),
        "ar": ("APS — توريد وتركيب يقوده الالتزام في السعودية",
               "المشاريع والتوريدات العربية (APS) مجموعة سعودية متنوّعة تقدّم التجارة والتوريد والتركيبات الكهروميكانيكية عبر شركات متخصصة وشركاء عالميين في أنحاء المملكة."),
    },
    "about": {
        "en": ("About APS — Arabian Projects & Supplies",
               "About Arabian Projects & Supplies (APS): a diversified Saudi group delivering electro-mechanical and industrial solutions, guided by integrity, professionalism and strong governance."),
        "ar": ("من نحن — المشاريع والتوريدات العربية APS",
               "نبذة عن المشاريع والتوريدات العربية (APS): مجموعة سعودية متنوّعة تقدّم حلولاً كهروميكانيكية وصناعية، مستندة إلى النزاهة والاحترافية وإطار قائم على الحوكمة."),
    },
    "contact": {
        "en": ("Contact APS — Arabian Projects & Supplies",
               "Contact Arabian Projects & Supplies (APS) about project inquiries, partnerships and technical support. Head office in Jeddah, Saudi Arabia."),
        "ar": ("تواصل معنا — المشاريع والتوريدات العربية APS",
               "تواصل مع المشاريع والتوريدات العربية (APS) حول استفسارات المشاريع والشراكات والدعم الفني. المكتب الرئيسي في جدة، المملكة العربية السعودية."),
    },
    "faq": {
        "en": ("FAQ — Arabian Projects & Supplies (APS)",
               "Frequently asked questions about Arabian Projects & Supplies (APS): services, divisions, engineering, EPC, partnerships and how to start a project."),
        "ar": ("الأسئلة الشائعة — المشاريع والتوريدات العربية APS",
               "الأسئلة الشائعة حول المشاريع والتوريدات العربية (APS): الخدمات والأقسام والهندسة ومشاريع EPC والشراكات وكيفية بدء مشروعك."),
    },
    "sps": {
        "en": ("Saudi Projects & Supplies (SPS) — APS Division",
               "Saudi Projects & Supplies Co. (SPS): a security, safety and control-systems integrator delivering integrated solutions across Saudi Arabia since 2001."),
        "ar": ("السعودية للمشاريع والتوريدات (SPS) — قسم APS",
               "السعودية للمشاريع والتوريدات (SPS): مُتكامل أنظمة الأمن والسلامة والتحكّم، تقدّم حلولاً متكاملة في أنحاء المملكة منذ عام 2001."),
    },
    "beta": {
        "en": ("Beta Machinery — Industrial Machinery | APS",
               "Beta Machinery, an APS division, supplies high-tech industrial machinery with installation, commissioning, training and after-sales support across Saudi Arabia."),
        "ar": ("بيتا للمعدّات — معدّات صناعية | APS",
               "بيتا للمعدّات، أحد أقسام APS، تورّد المعدّات الصناعية عالية التقنية مع التركيب والتشغيل والتدريب ودعم ما بعد البيع في أنحاء المملكة."),
    },
    "enviro": {
        "en": ("Envirosystems — Water & Environmental Solutions | APS",
               "Envirosystems, the APS environmental division, provides water, wastewater and ventilation solutions across Saudi Arabia through leading international suppliers."),
        "ar": ("إنفايروسيستمز — حلول المياه والبيئة | APS",
               "إنفايروسيستمز، القسم البيئي في APS، يوفّر حلول معالجة المياه والمياه العادمة والتهوية في أنحاء المملكة عبر موردين دوليين رائدين."),
    },
    "ags": {
        "en": ("Advanced Green Solutions (AGS) — Sustainable Agronomy | APS",
               "Advanced Green Solutions (AGS), the APS trading division for plant-health and eco-friendly agronomy products supporting sustainable agriculture across the region."),
        "ar": ("الحلول الخضراء المتقدّمة (AGS) — زراعة مستدامة | APS",
               "الحلول الخضراء المتقدّمة (AGS): قسم APS التجاري لمنتجات صحّة النبات والزراعة الصديقة للبيئة لدعم الزراعة المستدامة في أنحاء المنطقة."),
    },
    "azolis": {
        "en": ("AZOLIS Middle East — Solar Power Producer | APS",
               "AZOLIS Middle East: an independent solar power producer developing, financing, engineering, building and maintaining solar plants for the commercial and industrial segment."),
        "ar": ("أزوليس الشرق الأوسط — منتج طاقة شمسية | APS",
               "أزوليس الشرق الأوسط: منتج مستقل للطاقة الشمسية يطوّر ويموّل ويهندس ويبني ويصين محطات الطاقة الشمسية لقطاع المنشآت التجارية والصناعية."),
    },
}


def _abs(request, url):
    return request.build_absolute_uri(url)


def _resolve_title_desc(key, lang):
    """CMS value first (Page.seo_* / Division.cms_extra['seo']), else curated default."""
    title, desc = PAGE_SEO[key][lang]
    try:
        if key in _PAGE_KEYS:
            from pages.models import Page
            p = Page.objects.filter(slug=key).first()
            if p:
                title = (getattr(p, "seo_title_" + lang, "") or "").strip() or title
                desc = (getattr(p, "seo_desc_" + lang, "") or "").strip() or desc
        elif key in _DIV_KEYS:
            from divisions.models import Division
            dv = Division.objects.filter(slug=key).first()
            seo = (dv.cms_extra or {}).get("seo") if dv else None
            if isinstance(seo, dict):
                title = ((seo.get("title") or {}).get(lang) or "").strip() or title
                desc = ((seo.get("desc") or {}).get(lang) or "").strip() or desc
    except Exception:
        pass
    return title, desc


def _org_jsonld(request, lang):
    """Organization structured data (rich results / knowledge panel)."""
    s = SiteSettings.load()
    b = Brand.load()
    logo = b.logo if (b.logo or "").startswith("assets/") else ("assets/images/" + b.logo if b.logo else "assets/images/brand/aps-logo.png")
    same_as = [x.url for x in SocialLink.objects.all() if x.url and x.url.strip() not in ("", "#")]
    addr = (s.address_ar if lang == "ar" else s.address_en) or s.address_en or s.address_ar
    org = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": SITE_NAME_AR if lang == "ar" else SITE_NAME_EN,
        "alternateName": "APS",
        "url": _abs(request, "/ar/" if lang == "ar" else "/"),
        "logo": _abs(request, static(logo)),
        "email": s.email or "",
        "telephone": s.phone or "",
        "areaServed": "SA",
        "address": {"@type": "PostalAddress", "addressCountry": "SA", "streetAddress": addr},
    }
    if same_as:
        org["sameAs"] = same_as
    return json.dumps(org, ensure_ascii=False)


def _faq_jsonld(lang):
    """FAQPage structured data — lets FAQ rich snippets appear in search."""
    try:
        from faq.models import FAQItem
    except Exception:
        return None
    items = []
    for f in FAQItem.objects.all():
        q = (f.question_ar if lang == "ar" else f.question_en) or ""
        a = (f.answer_ar if lang == "ar" else f.answer_en) or ""
        if q and a:
            items.append({"@type": "Question", "name": q,
                          "acceptedAnswer": {"@type": "Answer", "text": a}})
    if not items:
        return None
    return json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                       "mainEntity": items}, ensure_ascii=False)


def seo_meta(request):
    """Context processor: builds the `seo` dict for public pages (empty elsewhere)."""
    path = request.path
    is_ar = path == "/ar" or path.startswith("/ar/")
    rel = (path[3:] if is_ar else path).strip("/")
    if rel not in _PUBLIC:
        return {}
    key = _PUBLIC[rel]
    lang = "ar" if is_ar else "en"
    title, desc = _resolve_title_desc(key, lang)

    en_path = "/" if key == "home" else "/%s/" % rel
    ar_path = "/ar/" if key == "home" else "/ar/%s/" % rel
    canonical = _abs(request, ar_path if is_ar else en_path)
    alternate = _abs(request, en_path if is_ar else ar_path)

    b = Brand.load()
    og_image = _abs(request, static("assets/images/brand/aps-logo.png"))
    theme_color = getattr(b, "color_accent", "#1A6DA2") or "#1A6DA2"

    jsonld = [_org_jsonld(request, lang)]
    if key == "faq":
        fj = _faq_jsonld(lang)
        if fj:
            jsonld.append(fj)

    return {"seo": {
        "title": title,
        "description": desc,
        "canonical": canonical,
        "alternate": alternate,
        "lang": "ar" if is_ar else "en",
        "alt_lang": "en" if is_ar else "ar",
        "x_default": _abs(request, en_path),
        "site_name": SITE_NAME_AR if is_ar else SITE_NAME_EN,
        "og_locale": "ar_AR" if is_ar else "en_US",
        "og_locale_alt": "en_US" if is_ar else "ar_AR",
        "og_image": og_image,
        "theme_color": theme_color,
        "jsonld": jsonld,
    }}


# ---------------------------------------------------------------- sitemap/robots
# (en_path, ar_path) for every public page — drives sitemap.xml.
_SITEMAP_PAIRS = (
    [("/", "/ar/")]
    + [("/%s/" % seg, "/ar/%s/" % seg) for seg in _PUBLIC if seg]
)


def sitemap_xml(request):
    """Bilingual XML sitemap: every page listed for both languages, each entry
    declaring its hreflang alternates (en / ar / x-default) — the layout Google
    recommends for multilingual sites."""
    rows = []
    for en_p, ar_p in _SITEMAP_PAIRS:
        en_u, ar_u = escape(_abs(request, en_p)), escape(_abs(request, ar_p))
        alts = ('<xhtml:link rel="alternate" hreflang="en" href="%s"/>'
                '<xhtml:link rel="alternate" hreflang="ar" href="%s"/>'
                '<xhtml:link rel="alternate" hreflang="x-default" href="%s"/>' % (en_u, ar_u, en_u))
        for loc in (en_u, ar_u):
            rows.append("<url><loc>%s</loc>%s<changefreq>weekly</changefreq>"
                        "<priority>%s</priority></url>" % (loc, alts, "1.0" if en_p == "/" else "0.8"))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">' + "".join(rows) + "</urlset>")
    return HttpResponse(xml, content_type="application/xml")


def robots_txt(request):
    """robots.txt — allow the public site, keep the CMS/admin out of the index,
    and point crawlers at the sitemap."""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /cms/",
        "Disallow: /django-admin/",
        "",
        "Sitemap: " + _abs(request, "/sitemap.xml"),
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
