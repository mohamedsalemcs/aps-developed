import os

from django.conf import settings
from django.templatetags.static import static
from .models import SiteSettings, Partner, SocialLink, Brand
from .themes import get_theme, get_font_scale, DARK_OVERRIDE_CSS, THEMES
from divisions.models import Division
from pages.models import Page

# request path (lang stripped) -> editable Page slug
_PAGE_SLUG = {"/": "home", "/about": "about", "/contact": "contact"}

# Files whose changes must bust the browser cache. ASSET_V (their newest mtime)
# is appended as ?v= to the CSS/JS <link>/<script> tags, so editing any of them
# yields a new URL — the client sees style/script updates on a PLAIN refresh,
# no Ctrl+Shift+R. (HTML + freshly-uploaded images are handled separately by
# NoHTMLCacheMiddleware + per-upload unique filenames.)
_ASSET_FILES = [
    "css/main.css", "css/variables.css", "js/main.js",
    "cms/css/admin.css", "cms/css/aps-toast.css", "cms/js/admin.js", "cms/js/store.js",
]
_asset_v_cache = None


def asset_version(request):
    """`ASSET_V` = newest mtime across the CSS/JS source files (cache-bust token).
    Recomputed every request in DEBUG so dev edits show instantly; computed once
    otherwise."""
    global _asset_v_cache
    if _asset_v_cache is None or settings.DEBUG:
        base = settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT
        newest = 0
        for rel in _ASSET_FILES:
            try:
                newest = max(newest, int(os.path.getmtime(os.path.join(str(base), *rel.split("/")))))
            except OSError:
                pass
        _asset_v_cache = str(newest or 1)
    return {"ASSET_V": _asset_v_cache}


def page_content(request):
    """Expose the current static page's CMS content as `pg`, already resolved to
    the request's language, so the public Home/About/Contact templates render
    their text from the DB (i.e. CMS edits to these pages reflect on the site)."""
    path = request.path
    is_ar = path == "/ar" or path.startswith("/ar/")
    rel = "/" + (path[3:] if is_ar else path).strip("/")
    slug = _PAGE_SLUG.get(rel)
    if not slug:
        return {}
    page = Page.objects.filter(slug=slug).prefetch_related("sections").first()
    if not page:
        return {}
    lang = "ar" if is_ar else "en"

    def resolve(v):
        if isinstance(v, dict):
            if "en" in v or "ar" in v:
                return v.get(lang) or v.get("en") or ""
            return {k: resolve(x) for k, x in v.items()}
        if isinstance(v, list):
            return [resolve(x) for x in v]
        return v

    pg = {s.key: resolve(s.data or {}) for s in page.sections.all()}

    # Resolve hero quick-feature icons to a usable static URL (icons may be a
    # bare filename, an "uploads/..." upload, or a full "assets/..." path) so
    # CMS-edited feature icons actually render on the public hero.
    hero = pg.get("hero")
    if isinstance(hero, dict) and isinstance(hero.get("features"), list):
        for f in hero["features"]:
            if isinstance(f, dict):
                f["icon_url"] = _icon_url(f.get("icon", ""))

    # Any page-section card grid (home divisions, about foundation/principles,
    # …): resolve each card's image/icon to a usable static URL so CMS-uploaded
    # media renders. Templates read c.img_url / c.icon_url instead of wrapping
    # the raw stored value in {% static %} (which breaks for "uploads/..." paths).
    for _sec in pg.values():
        if isinstance(_sec, dict) and isinstance(_sec.get("cards"), list):
            for c in _sec["cards"]:
                if isinstance(c, dict):
                    if "img" in c:
                        c["img_url"] = _img_static_url(c.get("img", ""))
                    if "icon" in c:
                        c["icon_url"] = _icon_url(c.get("icon", ""))

    # Ordered list of VISIBLE section keys (sections are ordered by their CMS
    # `order`; hidden ones are dropped) so the public template can honour the
    # editor's section reorder + show/hide just like the division pages.
    pg_order = [s.key for s in page.sections.all() if not s.hidden]
    pg_seo = {
        "title": (page.seo_title_ar if is_ar else page.seo_title_en) or "",
        "desc": (page.seo_desc_ar if is_ar else page.seo_desc_en) or "",
    }
    return {"pg": pg, "pg_order": pg_order, "pg_seo": pg_seo}


def _icon_url(v):
    """A CMS icon value -> a public static URL. Handles bare filenames
    (assets/images/icons/X), uploads (assets/images/uploads/X) and full paths."""
    v = (v or "").strip()
    if not v:
        return ""
    if v.startswith(("http://", "https://", "data:", "/")):
        return v
    if v.startswith("assets/"):
        return static(v)
    if v.startswith("uploads/"):
        return static("assets/images/" + v)
    return static("assets/images/icons/" + v)


def _img_static_url(v):
    """A CMS image value -> a public static URL. Like _icon_url but for images
    (no icons/ default): handles full 'assets/...', 'uploads/...', and paths
    relative to assets/images (e.g. 'divisions/x.jpg')."""
    v = (v or "").strip()
    if not v:
        return ""
    if v.startswith(("http://", "https://", "data:", "/")):
        return v
    if v.startswith("assets/"):
        return static(v)
    return static("assets/images/" + v)


def _brand_css(b, theme_override=None):
    """:root override of his variables.css tokens from the Brand row. Values
    equal his CSS defaults by default, so the public site renders identically
    until the client picks a theme/font size in /cms/brand/.

    The chosen theme preset (b.theme) supplies a full coordinated palette —
    including surface/border/footer-text — so dark presets actually render dark
    (cards + borders flip). The "custom" theme falls back to the legacy
    per-colour fields. b.font_scale multiplies the --fs-* type scale globally.

    `theme_override` lets a logged-in admin PREVIEW a theme via ?preview_theme=
    without saving (see site_globals)."""
    theme_key = theme_override or b.theme
    is_preset = bool(theme_key) and theme_key != "custom" and get_theme(theme_key).get("mode")
    # A known preset wins; "custom" (or any unknown key) uses the stored colours
    # so the existing per-colour data isn't lost.
    if is_preset:
        t = get_theme(theme_key)
        primary, accent, hover = t["primary"], t["accent"], t["hover"]
        text, muted, bg = t["text"], t["muted"], t["bg"]
        footer, surface, border = t["footer"], t["surface"], t["border"]
        footer_text = t["footer_text"]
        is_dark = t["mode"] == "dark"
    else:
        primary, accent, hover = b.color_primary, b.color_accent, b.color_hover
        text, muted, bg = b.color_text, b.color_muted, b.color_bg
        footer, surface, border, footer_text = b.color_footer, "#ffffff", "#e2e8f0", "#cbd5e1"
        is_dark = False

    scale = get_font_scale(getattr(b, "font_scale", "md"))

    # Load the two chosen brand fonts from Google Fonts so a font picked in
    # /cms/brand/ actually renders on the public site (only Inter+Cairo are
    # bundled locally; any other choice would otherwise silently fall back).
    fams = []
    for f in (b.english_font, b.arabic_font):
        f = (f or "").strip()
        if f and f not in [x.split(":")[0].replace("family=", "").replace("+", " ") for x in fams]:
            fams.append("family=" + f.replace(" ", "+") + ":wght@400;500;600;700")
    font_import = ('@import url("https://fonts.googleapis.com/css2?' + "&".join(fams)
                   + '&display=swap");') if fams else ""
    return (
        font_import +
        ":root{"
        f"--color-primary:{primary};"
        f"--color-primary-hover:{hover};"
        f"--color-accent:{accent};"
        f"--color-text-primary:{text};"
        f"--color-text-secondary:{muted};"
        f"--color-background:{bg};"
        f"--color-surface:{surface};"
        f"--color-border:{border};"
        f"--color-footer-bg:{footer};"
        f"--color-footer-text:{footer_text};"
        f"--font-scale:{scale};"
        f'--font-en:"{b.english_font}",system-ui,-apple-system,"Segoe UI",sans-serif;'
        f'--font-ar:"{b.arabic_font}",system-ui,sans-serif;'
        "}"
        # client request: drop the decorative offset frame that peeked awkwardly
        # from behind the About image (loaded after main.css so it wins).
        ".about__media::after{display:none!important;}"
        # keep long contact values (e.g. emails) inside their card instead of
        # overflowing the box.
        ".contact-card{min-inline-size:0;}"
        ".contact-card__value{min-inline-size:0;overflow-wrap:anywhere;}"
        # the header logo is now an <img> (CMS-replaceable) — keep any uploaded
        # logo's aspect ratio inside the 40x52 mark box.
        "img.logo__mark{object-fit:contain;}"
        # dark themes: additive layer re-pointing main.css's hardcoded light
        # literals at the theme tokens (only emitted for dark presets).
        + (DARK_OVERRIDE_CSS if is_dark else "")
    )


def _brand_logo_url(b):
    """Public URL for the HEADER logo (single image): the CMS-uploaded header
    logo if set, else the default APS logo image."""
    if b.logo:
        rel = b.logo if b.logo.startswith("assets/") else "assets/images/" + b.logo
        return static(rel)
    return static("assets/images/brand/aps-logo.png")


def _brand_footer_logo_url(b):
    """Public URL for the FOOTER logo (single image): the CMS-uploaded footer
    logo if set, else the default white footer logo."""
    if b.logo_footer:
        rel = b.logo_footer if b.logo_footer.startswith("assets/") else "assets/images/" + b.logo_footer
        return static(rel)
    return static("assets/images/brand/aps-logo-footer.svg")


def _brand_favicon_url(b):
    """Public URL for the browser-tab FAVICON: the CMS-uploaded favicon if set,
    else the bundled SQUARE APS mark — far clearer at favicon sizes than the wide
    full logo that was previously hardcoded. Handles upload data:/blob:/http URLs
    and absolute paths as passthrough, and bare 'assets/...'/relative paths via
    {% static %}."""
    v = (getattr(b, "favicon", "") or "").strip()
    if v:
        if v.startswith(("http://", "https://", "data:", "blob:", "/")):
            return v
        return static(v if v.startswith("assets/") else "assets/images/" + v)
    return static("assets/images/brand/aps-logo-mark.svg")


def site_globals(request):
    """Inject site-wide content available to every template:
    - `site`      : SiteSettings singleton (footer/contact text)
    - `partners`  : partner marquee logos
    - `social`    : footer social links
    - `brand_css` : :root token overrides for the public <head> (brand screen -> site)
    These appear across many of the designer's pages, so a context processor
    avoids per-view plumbing.
    """
    # public division listings (header dropdown + footer): published only,
    # ordered by Division.order; nav/footer use cms_extra.menu_en/ar + public_slug.
    nav_divisions = list(Division.objects.filter(status="published").order_by("order", "id"))
    division_visible = {d.slug: (d.status == "published") for d in Division.objects.all()}
    brand = Brand.load()
    # Logged-in admins can preview any theme on the live site via ?preview_theme=
    # (e.g. the CMS "Preview" button opens the site with it) without persisting.
    preview = request.GET.get("preview_theme")
    if preview and preview not in THEMES:
        preview = None
    if preview and not getattr(request.user, "is_staff", False):
        preview = None
    # Resolve each social link's icon to a real static URL. The stored value may
    # be a bundled icon name ("linkedin.svg" -> assets/images/icons/), a CMS
    # upload ("uploads/x.png" -> assets/images/uploads/), or a full path. The
    # footer templates previously hardcoded the "icons/" prefix, which broke any
    # uploaded/replaced icon; they now read s.icon_url instead.
    social = list(SocialLink.objects.all())
    for s in social:
        s.icon_url = _icon_url(s.icon)
    return {
        "site": SiteSettings.load(),
        "partners": Partner.objects.all(),
        "social": social,
        "brand_css": _brand_css(brand, theme_override=preview),
        "brand_logo_url": _brand_logo_url(brand),
        "brand_footer_logo_url": _brand_footer_logo_url(brand),
        "brand_favicon_url": _brand_favicon_url(brand),
        "nav_divisions": nav_divisions,
        "division_visible": division_visible,
    }


# CMS sidebar: bilingual labels for the per-division section sub-menu items.
# (en, ar) — keyed by the section key stored in Division.cms_extra["order"].
_CMS_SECTION_LABELS = {
    "banner": ("Banner", "البانر"),
    "about": ("About", "عن القسم"),
    "systems": ("Systems & Solutions", "الأنظمة والحلول"),
    "categories": ("Machinery Categories", "فئات الآلات"),
    "suppliers": ("Suppliers", "الموردون الدوليون"),
    "solutions": ("Solutions", "الحلول"),
    "foundation": ("Vision & Mission", "الرؤية والرسالة"),
    "products": ("Products", "مجموعة المنتجات"),
    "lifecycle": ("Lifecycle", "مراحل دورة الحياة"),
    "projects": ("Our Projects", "مشاريعنا"),
    "partners": ("Partners", "الشركاء"),
    "contact": ("Contact", "بيانات التواصل"),
}


def cms_nav(request):
    """CMS sidebar data: each division's REAL bilingual name + its actual ordered
    sections (bilingual labels), so the divisions sub-menu mirrors the page. Only
    built for /cms/ requests. `active_div` = the division being edited (?div=)."""
    if not request.path.startswith("/cms/"):
        return {}
    divs = []
    for d in Division.objects.order_by("order", "id"):
        order = (d.cms_extra or {}).get("order") or []
        sections = [{"key": k,
                     "en": _CMS_SECTION_LABELS.get(k, (k, k))[0],
                     "ar": _CMS_SECTION_LABELS.get(k, (k, k))[1]} for k in order]
        divs.append({"slug": d.slug, "name_en": d.name_en, "name_ar": d.name_ar,
                     "sections": sections})
    return {"cms_nav_divisions": divs, "active_div": request.GET.get("div") or ""}
