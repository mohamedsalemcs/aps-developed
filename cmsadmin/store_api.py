# -*- coding: utf-8 -*-
"""Build / apply the CMS store JSON in the designer's exact store.js shape.

build_store()  : Django models -> dict (same keys/shape as his store.js SEED)
apply_store(d) : dict -> Django models, reconciling lists (create/update/delete)

His admin.js reads/writes this tree only; our server-backed store.js bootstraps
from build_store() and POSTs the whole tree back to apply_store().
"""
from django.db import transaction

from core.models import SiteSettings, SocialLink, Partner, Brand
from core.themes import THEMES, FONT_SCALES
from pages.models import Page, PageSection
from divisions.models import Division, DivisionProject, DivisionCard
from faq.models import FAQItem

ASSET_PREFIX = "assets/images/"
DIVISION_ORDER = ["banner", "about", "systems", "projects", "contact"]
CORE_DIVISIONS = {"sps", "beta", "enviro", "ags", "azolis"}  # have designed public pages

# exact header/footer menu labels (kept in cms_extra so the public nav/footer
# render the designer's labels; preserved across saves).
MENU_LABEL = {
    "sps": ("Saudi Projects & Supplies", "السعودية للمشاريع والتوريدات"),
    "beta": ("Beta Machinery", "بيتا للمعدّات"),
    "enviro": ("Envirosystems", "إنفايروسيستمز"),
    "ags": ("Advanced Green Solutions", "الحلول الخضراء المتقدّمة"),
    "azolis": ("AZOLIS Middle East", "أزوليس الشرق الأوسط"),
}


def _bi(en, ar):
    return {"en": en or "", "ar": ar or ""}


def _g(node, lang):
    """Read a {en,ar} dict safely; tolerate plain strings."""
    if isinstance(node, dict):
        return node.get(lang, "") or ""
    return node or "" if lang == "en" else ""


def _img_rel(path):
    """DB stores 'assets/images/x'; his store wants 'x' (relative to that dir).
    data:/blob:/http/ /media/ URLs pass through untouched (uploads)."""
    if not path:
        return ""
    if path.startswith(("data:", "blob:", "http", "/media")):
        return path
    if path.startswith(ASSET_PREFIX):
        return path[len(ASSET_PREFIX):]
    return path


def _img_abs(rel):
    """Inverse of _img_rel for persistence."""
    if not rel:
        return ""
    if rel.startswith(("data:", "blob:", "http", "/media", ASSET_PREFIX)):
        return rel
    return ASSET_PREFIX + rel


# Standard partner-logo tile (matches the designer's pre-framed 178x98 logos).
_TILE = (178, 98)
_TILE_PAD = 16
_TILE_BORDER = (223, 230, 238)  # ~#dfe6ee, like the designer tiles


def _frame_partner(stored_path):
    """Normalize a partner logo into the standard 178x98 tile (white bg, thin
    border, logo trimmed + centered + contained) so ANY uploaded logo matches
    the designer's pre-framed ones — AND always lands on a clean ASCII filename
    under partners_framed/ (the original designer files have spaces / Arabic in
    their names, which break on some browsers/CDNs). Idempotent: anything already
    under partners_framed/ is returned untouched. Returns the stored image path."""
    if not stored_path or stored_path.startswith(("data:", "blob:", "http", "/media")):
        return stored_path
    if stored_path.startswith("assets/images/partners_framed/"):
        return stored_path  # already normalized + clean name
    try:
        from pathlib import Path
        from django.conf import settings
        from PIL import Image, ImageDraw
        import hashlib, shutil

        base = Path(settings.STATICFILES_DIRS[0])
        src = base / stored_path
        if not src.exists():
            return stored_path
        out_dir = base / "assets" / "images" / "partners_framed"
        out_dir.mkdir(parents=True, exist_ok=True)
        name = hashlib.md5(src.read_bytes()).hexdigest()[:16] + ".png"
        out = out_dir / name

        im = Image.open(src)
        if im.size == _TILE:
            # already a proper tile (a designer logo) — keep it identical, just
            # copy to a clean ASCII filename so the URL never breaks.
            shutil.copy(src, out)
            return "assets/images/partners_framed/" + name
        # otherwise trim near-white margins + center on the standard white tile
        im = im.convert("RGBA")
        flat = Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)), im).convert("L")
        mask = flat.point(lambda p: 255 if p < 238 else 0)
        bbox = mask.getbbox()
        if bbox:
            im = im.crop(bbox)
        inner = (_TILE[0] - 2 * _TILE_PAD, _TILE[1] - 2 * _TILE_PAD)
        im.thumbnail(inner, Image.LANCZOS)
        tile = Image.new("RGBA", _TILE, (255, 255, 255, 255))
        tile.paste(im, ((_TILE[0] - im.size[0]) // 2, (_TILE[1] - im.size[1]) // 2), im)
        ImageDraw.Draw(tile).rectangle([0, 0, _TILE[0] - 1, _TILE[1] - 1], outline=_TILE_BORDER + (255,))
        tile.convert("RGB").save(out, "PNG")
        return "assets/images/partners_framed/" + name
    except Exception:
        return stored_path


# --------------------------------------------------------------------- BUILD
def build_store():
    s = SiteSettings.load()
    b = Brand.load()
    store = {
        "settings": {
            "siteName": _bi(s.site_name_en, s.site_name_ar),
            "tagline": _bi(s.tagline_en, s.tagline_ar),
            "phone": s.phone, "email": s.email, "website": s.website,
            "address": _bi(s.address_en, s.address_ar),
            "social": [{"name": x.platform, "url": x.url, "icon": x.icon}
                       for x in SocialLink.objects.all()],
            "maintenance": s.maintenance_mode,
        },
        "brand": {
            "colors": {"primary": b.color_primary, "accent": b.color_accent,
                       "hover": b.color_hover, "text": b.color_text,
                       "muted": b.color_muted, "bg": b.color_bg, "footer": b.color_footer},
            "logo": b.logo, "logoFooter": b.logo_footer, "arabicFont": b.arabic_font, "englishFont": b.english_font,
            "theme": b.theme, "fontScale": b.font_scale, "cmsTheme": b.cms_theme,
        },
        "partners": {"items": [{"name": p.name, "img": _img_rel(p.image)}
                               for p in Partner.objects.all()]},
        "faq": {"items": [{"q": _bi(f.question_en, f.question_ar),
                           "a": _bi(f.answer_en, f.answer_ar)}
                          for f in FAQItem.objects.all()]},
        "pages": {},
        "divisions": {},
        # read-only reference data for the brand screen's theme gallery + the
        # CMS panel theming in admin.js (apply_store ignores these on save).
        "themes": THEMES,
        "fontScales": list(FONT_SCALES.keys()),
    }

    for page in Page.objects.all():
        sections, order = {}, []
        for ps in page.sections.all():
            data = dict(ps.data or {})
            if ps.hidden:
                data["hidden"] = True
            sections[ps.key] = data
            order.append(ps.key)
        store["pages"][page.slug] = {
            "title": _bi(page.title_en, page.title_ar),
            "status": page.status, "updated": "",
            "seo": {"title": _bi(page.seo_title_en, page.seo_title_ar),
                    "desc": _bi(page.seo_desc_en, page.seo_desc_ar)},
            "order": order,
            "sections": sections,
        }

    for div in Division.objects.all():
        extra = div.cms_extra or {}
        hidden = extra.get("hidden", {}) or {}
        sections = {
            "banner": {"subtitle": _bi(div.banner_subtitle_en, div.banner_subtitle_ar)},
            "about": {"title": _bi(div.about_title_en, div.about_title_ar),
                      "body": _bi(div.about_body_en, div.about_body_ar)},
            "systems": {"title": _bi(div.systems_title_en, div.systems_title_ar),
                        "subtitle": _bi(div.systems_subtitle_en, div.systems_subtitle_ar)},
            "projects": {"title": extra.get("projects_title", _bi("Our Projects", "مشاريعنا")),
                         "items": [{"img": _img_rel(p.image),
                                    "title": _bi(p.title_en, p.title_ar),
                                    "location": _bi(p.location_en, p.location_ar),
                                    "typology": _bi(p.typology_en, p.typology_ar),
                                    "installed_power": _bi(p.installed_power_en, p.installed_power_ar),
                                    "contract": _bi(p.contract_en, p.contract_ar)}
                                   for p in div.projects.all()]},
            "contact": {"phone": div.contact_phone, "site": div.contact_website,
                        "email": div.contact_email},
        }
        for k, v in sections.items():
            if hidden.get(k):
                v["hidden"] = True
        # middle-section card grids, grouped by section_key
        cards = {}
        for c in div.cards.all():
            cards.setdefault(c.section_key, []).append({
                "icon": _img_rel(c.icon),
                "title": _bi(c.title_en, c.title_ar),
                "body": _bi(c.body_en, c.body_ar),
                "extra": c.extra or {},
            })
        store["divisions"][div.slug] = {
            "name": _bi(div.name_en, div.name_ar),
            "slug": extra.get("public_slug", "/" + div.slug),
            "status": div.status, "updated": "",
            "order": extra.get("order", list(DIVISION_ORDER)),
            "hidden": hidden,
            "seo": extra.get("seo") or {"title": _bi("", ""), "desc": _bi("", "")},
            "extra_titles": extra.get("extra_titles") or {},
            "sections": sections,
            "cards": cards,
        }
    return store


# --------------------------------------------------------------------- APPLY
@transaction.atomic
def apply_store(data):
    """Map the full store tree back into models. Lists are reconciled by index
    (create/update/delete). DivisionProject spec fields (AZOLIS) are preserved
    because his admin's project repeater only edits img+title."""
    # ---- settings
    st = data.get("settings", {})
    s = SiteSettings.load()
    s.site_name_en = _g(st.get("siteName"), "en"); s.site_name_ar = _g(st.get("siteName"), "ar")
    s.tagline_en = _g(st.get("tagline"), "en"); s.tagline_ar = _g(st.get("tagline"), "ar")
    s.phone = st.get("phone", "") or ""; s.email = st.get("email", "") or ""
    s.website = st.get("website", "") or ""
    s.address_en = _g(st.get("address"), "en"); s.address_ar = _g(st.get("address"), "ar")
    s.maintenance_mode = bool(st.get("maintenance", False))
    s.save()

    social = st.get("social", []) or []
    keep_social = []
    for i, soc in enumerate(social):
        obj, _ = SocialLink.objects.update_or_create(
            order=i, defaults=dict(platform=soc.get("name", ""), url=soc.get("url", "") or "",
                                   icon=soc.get("icon", "") or ""))
        keep_social.append(obj.pk)
    if social:  # guard: never wipe all rows on an empty/partial payload
        SocialLink.objects.exclude(pk__in=keep_social).delete()

    # ---- brand
    br = data.get("brand", {})
    cols = br.get("colors", {}) or {}
    b = Brand.load()
    b.color_primary = cols.get("primary", b.color_primary); b.color_accent = cols.get("accent", b.color_accent)
    b.color_hover = cols.get("hover", b.color_hover); b.color_text = cols.get("text", b.color_text)
    b.color_muted = cols.get("muted", b.color_muted); b.color_bg = cols.get("bg", b.color_bg)
    b.color_footer = cols.get("footer", b.color_footer)
    b.logo = br.get("logo", "") or ""
    b.logo_footer = br.get("logoFooter", "") or ""
    b.arabic_font = br.get("arabicFont", b.arabic_font); b.english_font = br.get("englishFont", b.english_font)
    b.theme = br.get("theme", b.theme) or b.theme
    b.font_scale = br.get("fontScale", b.font_scale) or b.font_scale
    b.cms_theme = br.get("cmsTheme", b.cms_theme) or b.cms_theme
    b.save()

    # ---- partners (reconcile by index)
    items = (data.get("partners", {}) or {}).get("items", []) or []
    keep = []
    for i, it in enumerate(items):
        obj, _ = Partner.objects.update_or_create(
            order=i, defaults=dict(name=it.get("name", ""),
                                   image=_frame_partner(_img_abs(it.get("img", "")))))
        keep.append(obj.pk)
    if items:  # guard: never wipe all partners on an empty/partial payload
        Partner.objects.exclude(pk__in=keep).delete()

    # ---- faq (reconcile by index)
    fitems = (data.get("faq", {}) or {}).get("items", []) or []
    keep = []
    for i, it in enumerate(fitems):
        obj, _ = FAQItem.objects.update_or_create(
            order=i, defaults=dict(question_en=_g(it.get("q"), "en"), question_ar=_g(it.get("q"), "ar"),
                                   answer_en=_g(it.get("a"), "en"), answer_ar=_g(it.get("a"), "ar")))
        keep.append(obj.pk)
    if fitems:  # guard: never wipe all FAQs on an empty/partial payload
        FAQItem.objects.exclude(pk__in=keep).delete()

    # ---- pages
    for slug, pdata in (data.get("pages", {}) or {}).items():
        page = Page.objects.filter(slug=slug).first()
        if not page:
            continue
        page.title_en = _g(pdata.get("title"), "en"); page.title_ar = _g(pdata.get("title"), "ar")
        page.status = pdata.get("status", page.status)
        seo = pdata.get("seo", {}) or {}
        page.seo_title_en = _g(seo.get("title"), "en"); page.seo_title_ar = _g(seo.get("title"), "ar")
        page.seo_desc_en = _g(seo.get("desc"), "en"); page.seo_desc_ar = _g(seo.get("desc"), "ar")
        page.save()
        order = pdata.get("order") or list((pdata.get("sections") or {}).keys())
        sections = pdata.get("sections", {}) or {}
        keep_keys = []
        for i, key in enumerate(order):
            content = dict(sections.get(key, {}) or {})
            hidden = bool(content.pop("hidden", False))
            PageSection.objects.update_or_create(
                page=page, key=key, defaults=dict(order=i, hidden=hidden, data=content))
            keep_keys.append(key)
        page.sections.exclude(key__in=keep_keys).delete()

    # ---- divisions
    for key, ddata in (data.get("divisions", {}) or {}).items():
        div = Division.objects.filter(slug=key).first()
        secs = ddata.get("sections", {}) or {}
        banner, about, systems, projects, contact = (
            secs.get("banner", {}), secs.get("about", {}), secs.get("systems", {}),
            secs.get("projects", {}), secs.get("contact", {}))
        fields = dict(
            name_en=_g(ddata.get("name"), "en"), name_ar=_g(ddata.get("name"), "ar"),
            status=ddata.get("status", "published"),
            banner_subtitle_en=_g(banner.get("subtitle"), "en"), banner_subtitle_ar=_g(banner.get("subtitle"), "ar"),
            about_title_en=_g(about.get("title"), "en"), about_title_ar=_g(about.get("title"), "ar"),
            about_body_en=_g(about.get("body"), "en"), about_body_ar=_g(about.get("body"), "ar"),
            systems_title_en=_g(systems.get("title"), "en"), systems_title_ar=_g(systems.get("title"), "ar"),
            systems_subtitle_en=_g(systems.get("subtitle"), "en"), systems_subtitle_ar=_g(systems.get("subtitle"), "ar"),
            contact_phone=contact.get("phone", "") or "", contact_website=contact.get("site", "") or "",
            contact_email=contact.get("email", "") or "",
        )
        # hidden map: base-section flags (legacy) merged with the editor's explicit
        # per-section hidden map (covers card sections like suppliers/foundation too).
        hidden = dict({k: bool((secs.get(k) or {}).get("hidden")) for k in secs},
                      **{k: bool(v) for k, v in (ddata.get("hidden") or {}).items()})
        prev = (div.cms_extra or {}) if div else {}
        # menu labels: keep existing -> fall back to the canonical map -> name
        # nav/footer label follows the division NAME so a name edit reflects in
        # the site header (reviewer: "editing a division name should show in the header").
        extra = dict(projects_title=projects.get("title", _bi("Our Projects", "مشاريعنا")),
                     public_slug=ddata.get("slug", "/" + key),
                     menu_en=fields["name_en"],
                     menu_ar=fields["name_ar"],
                     order=ddata.get("order", list(DIVISION_ORDER)),
                     hidden=hidden,
                     seo=ddata.get("seo") or prev.get("seo") or {},
                     extra_titles=ddata.get("extra_titles") or prev.get("extra_titles") or {})
        if div:
            for f, v in fields.items():
                setattr(div, f, v)
            div.cms_extra = extra
            div.save()
        else:
            div = Division.objects.create(slug=key, **fields, cms_extra=extra)

        # projects: reconcile img+title (+ AZOLIS specs when present) by index
        pitems = projects.get("items", []) or []
        keep = []
        for i, it in enumerate(pitems):
            defaults = dict(image=_img_abs(it.get("img", "")),
                            title_en=_g(it.get("title"), "en"), title_ar=_g(it.get("title"), "ar"))
            for fld in ("location", "typology", "installed_power", "contract"):
                if fld in it:  # only touch specs the editor actually sent
                    defaults[f"{fld}_en"] = _g(it.get(fld), "en")
                    defaults[f"{fld}_ar"] = _g(it.get(fld), "ar")
            obj, _ = DivisionProject.objects.update_or_create(
                division=div, order=i, defaults=defaults)
            keep.append(obj.pk)
        if pitems:  # guard: never wipe all projects on an empty/partial payload
            div.projects.exclude(pk__in=keep).delete()

        # middle-section cards: reconcile per section_key by index (only if sent)
        if "cards" in ddata:
            keep_cards = []
            for section_key, items in (ddata.get("cards") or {}).items():
                for i, cd in enumerate(items or []):
                    obj, _ = DivisionCard.objects.update_or_create(
                        division=div, section_key=section_key, order=i,
                        defaults=dict(icon=_img_abs(cd.get("icon", "")),
                                      title_en=_g(cd.get("title"), "en"), title_ar=_g(cd.get("title"), "ar"),
                                      body_en=_g(cd.get("body"), "en"), body_ar=_g(cd.get("body"), "ar"),
                                      extra=cd.get("extra", {}) or {}))
                    keep_cards.append(obj.pk)
            div.cards.exclude(pk__in=keep_cards).delete()

    # Division delete semantics: a division removed from the admin tree is gone
    # from the incoming data. Core divisions (designed pages) -> SOFT delete
    # (status=draft) so their template isn't orphaned and they 404 + drop from
    # listings; new/extra divisions -> hard delete (no designed page to keep).
    incoming = set((data.get("divisions") or {}).keys())
    if incoming:  # only reconcile when a real division payload was sent
        for div in Division.objects.exclude(slug__in=incoming):
            if div.slug in CORE_DIVISIONS:
                if div.status != "draft":
                    div.status = "draft"
                    div.save(update_fields=["status"])
            else:
                div.delete()
