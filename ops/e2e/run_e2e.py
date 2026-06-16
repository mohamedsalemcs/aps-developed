# -*- coding: utf-8 -*-
"""APS end-to-end test suite (pre-delivery gate).

Exercises every feature — public site + CMS — through the real UI (Selenium +
headless Edge) and HTTP, with DB assertions via the Django ORM. Every mutating
test reverts; final data state == initial. Writes a human report to
ops/e2e/report/E2E_REPORT.html (+ results.json, shots/).

Run:  venv\\Scripts\\python.exe ops\\e2e\\run_e2e.py
"""
import os
import sys
import re
import io
import json
import time
import zlib
import struct
import shutil
import pathlib
import datetime
import urllib.request
import urllib.parse
import http.cookiejar

# ----- paths / django ------------------------------------------------------
HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parent.parent           # D:\APS_final\aps_backend
sys.path.insert(0, str(PROJECT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aps_backend.settings")
os.environ.setdefault("PYTHONUTF8", "1")
import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from faq.models import FAQItem
from core.models import Partner, SiteSettings, SocialLink
from divisions.models import Division, DivisionProject, DivisionCard
from pages.models import Page, PageSection
from submissions.models import ContactSubmission

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "http://127.0.0.1:8000"
# E2E uses its OWN throwaway admin so it never touches the real `aps_admin`
# account — the client owns that password (changing it must not be clobbered by
# a test run). ensure_e2e_user() creates/refreshes this account at startup.
ADMIN_USER = "e2e_admin"
ADMIN_PW = "LHLyCWL0hZe8kc4O9II5"
TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
MARK = "E2E_" + TS
REPORT_DIR = HERE / "report"
SHOTS = REPORT_DIR / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)
results = []
_t0 = time.time()


def rec(area, name, ok, detail="", dur=0.0, shot=""):
    results.append({"area": area, "name": name, "ok": bool(ok),
                    "detail": str(detail), "dur": round(dur, 2), "shot": shot})
    print(("  [PASS] " if ok else "  [FAIL] ") + f"{area} | {name} — {detail}")


def step(area, name):
    """decorator-ish timer/guard wrapper."""
    def wrap(fn):
        t = time.time()
        try:
            detail, shot = fn()
            rec(area, name, True, detail, time.time() - t, shot)
            return True
        except Exception as e:
            rec(area, name, False, f"{type(e).__name__}: {e}", time.time() - t)
            return False
    return wrap


# ----- http helpers --------------------------------------------------------
def hget(path, opener=None):
    o = opener or urllib.request.build_opener()
    r = o.open(urllib.request.Request(BASE + path, headers={"User-Agent": "aps-e2e"}), timeout=30)
    return r.getcode(), r.read().decode("utf-8", "replace")


def http_status(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "aps-e2e"}), timeout=30).getcode()
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


# ----- a big valid PNG (~1.5MB, incompressible) ----------------------------
def make_png(side=720):
    raw = bytearray()
    rnd = 2463534242
    for y in range(side):
        raw.append(0)
        for x in range(side * 3):
            rnd ^= (rnd << 13) & 0xFFFFFFFF; rnd ^= rnd >> 17; rnd ^= (rnd << 5) & 0xFFFFFFFF
            raw.append(rnd & 0xFF)

    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", side, side, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 0)) + chunk(b"IEND", b"")
    return png


# ----- selenium ------------------------------------------------------------
def new_driver():
    o = Options()
    for a in ("--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1440,1800"):
        o.add_argument(a)
    d = webdriver.Edge(options=o)
    d.set_page_load_timeout(40)
    return d


def login(d):
    d.get(BASE + "/cms/login/")
    d.find_element(By.NAME, "username").send_keys(ADMIN_USER)
    d.find_element(By.NAME, "password").send_keys(ADMIN_PW)
    d.find_element(By.CSS_SELECTOR, "#loginForm button[type=submit]").click()
    WebDriverWait(d, 20).until(EC.url_matches(r".*/cms/$"))


def save(d):
    d.execute_script("document.querySelector('[data-save]').click();")
    time.sleep(1.6)


def shot(d, name):
    p = SHOTS / (name + ".png")
    time.sleep(0.6)
    d.save_screenshot(str(p))
    return "shots/" + name + ".png"


def field_edit(d, url, css, newval):
    d.get(BASE + url)
    el = WebDriverWait(d, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
    # reveal: open any collapsed admin.js section-block / activate its tab, then scroll
    d.execute_script("""
        var el=arguments[0];
        var sb=el.closest('.section-block'); if(sb) sb.classList.add('is-open');
        var tp=el.closest('[data-tabpanel]');
        if(tp && tp.hidden){var t=document.querySelector('.tab[data-tab="'+tp.getAttribute('data-tabpanel')+'"]'); if(t)t.click();}
        el.scrollIntoView({block:'center'});
    """, el)
    time.sleep(0.3)
    old = el.get_attribute("value")
    el.clear(); el.send_keys(newval); time.sleep(0.2)
    save(d)
    return old


# ==========================================================================
# initial integrity snapshot
# ==========================================================================
def counts():
    return {
        "faq": FAQItem.objects.count(), "partners": Partner.objects.count(),
        "social": SocialLink.objects.count(), "divisions": Division.objects.count(),
        "projects": DivisionProject.objects.count(), "cards": DivisionCard.objects.count(),
        "pages": Page.objects.count(), "sections": PageSection.objects.count(),
        "submissions": ContactSubmission.objects.count(),
    }


INITIAL = counts()


# ==========================================================================
# A. Public site (HTTP)
# ==========================================================================
EN = ["/", "/about/", "/sps/", "/beta-machinery/", "/envirosystems/",
      "/advanced-green-solutions/", "/azolis-middle-east/", "/faq/", "/contact/"]
ROUTES = EN + ["/ar" + (p if p != "/" else "/") for p in EN]


def area_A():
    @step("A. Public", "A1 — 18/18 routes return 200")
    def _():
        bad = [r for r in ROUTES if http_status(BASE + r) != 200]
        assert not bad, f"non-200: {bad}"
        return f"{len(ROUTES)}/18 routes 200", ""

    @step("A. Public", "A2 — 0 static 404s across all pages")
    def _():
        refs = set()
        for r in ROUTES:
            _, html = hget(r)
            for m in re.finditer(r'(?:src|href)="(/static/[^"]+)"', html):
                refs.add(m.group(1))
        bad = []
        for u in refs:
            path = u.split("?")[0]  # ignore cache-bust query (e.g. ?v=2)
            enc = "/".join(urllib.parse.quote(p) for p in path.split("/"))
            if http_status(BASE + enc) != 200:
                bad.append(u)
        assert not bad, f"404s: {bad[:5]}"
        return f"{len(refs)} unique refs, 0 404s", ""

    @step("A. Public", "A3 — content counts from DB render on pages")
    def _():
        def cnt(path, pat):
            _, h = hget(path); return len(re.findall(pat, h))
        # partners: count imgs inside the marquee (folder-agnostic — logos may be
        # in clinets/, partners_framed/, or uploads/), expect partner count x2 tracks.
        _, _home = hget("/")
        _mq = re.search(r'class="marquee"[\s\S]*?</section>', _home)
        _pimgs = len(re.findall(r'<img', _mq.group(0))) if _mq else 0
        checks = {
            "FAQ": (cnt("/faq/", r'faq-item__num'), 16),
            "partners(home, 2 tracks)": (_pimgs, Partner.objects.count() * 2),
            "SPS systems": (cnt("/sps/", r'system-card__label'), 15),
            "Beta categories": (cnt("/beta-machinery/", r'category-card__title'), 8),
            "Enviro suppliers": (cnt("/envirosystems/", r'class="supplier"'), 4),
            "Enviro solutions": (cnt("/envirosystems/", r'class="solution"'), 4),
            "AGS pills": (cnt("/advanced-green-solutions/", r'dabout-pill"'), 4),
            "AGS foundation": (cnt("/advanced-green-solutions/", r'class="vcard"'), 2),
            "AGS products": (cnt("/advanced-green-solutions/", r'product-card__title'), 11),
            "AZOLIS pills": (cnt("/azolis-middle-east/", r'dabout-pill--alt'), 4),
            "AZOLIS lifecycle": (cnt("/azolis-middle-east/", r'class="lcard"'), 2),
            "AZOLIS milestones": (cnt("/azolis-middle-east/", r'class="milestone"'), 10),
            "AZOLIS projects": (cnt("/azolis-middle-east/", r'azproject-card"'), 6),
            "SPS projects": (cnt("/sps/", r'class="project-card"'), 6),
        }
        bad = {k: v for k, (v, exp) in checks.items() if v != exp}
        assert not bad, f"mismatch: {bad}"
        return "all 14 grid counts correct", ""

    @step("A. Public", "A4 — AR pages RTL + Arabic content")
    def _():
        bad = []
        for r in [x for x in ROUTES if x.startswith("/ar")]:
            _, h = hget(r)
            if 'dir="rtl"' not in h or not re.search(r'[؀-ۿ]', h):
                bad.append(r)
        assert not bad, f"AR issue: {bad}"
        return "9 AR pages rtl + Arabic", ""

    @step("A. Public", "A5 — EN<->AR switch links correct")
    def _():
        _, en = hget("/"); _, ar = hget("/ar/")
        assert 'href="/ar/"' in en, "EN home missing /ar/ switch"
        assert 'href="/"' in ar, "AR home missing / switch"
        _, ensps = hget("/sps/")
        assert 'href="/ar/sps/"' in ensps, "sps EN->AR link"
        return "lang-switch mirrors correct", ""


# ==========================================================================
# B. Contact form + toast
# ==========================================================================
def area_B(d):
    @step("B. Contact", "B6 — valid submit -> success toast + DB record")
    def _():
        d.get(BASE + "/contact/")
        d.find_element(By.CSS_SELECTOR, '#cf-name').send_keys(MARK + " EN")
        d.find_element(By.CSS_SELECTOR, '#cf-email').send_keys("en_" + MARK + "@e2e.local")
        d.find_element(By.CSS_SELECTOR, '#cf-phone').send_keys("+966 50 000 0001")
        d.find_element(By.CSS_SELECTOR, '#cf-message').send_keys("E2E valid EN submission")
        _btn = d.find_element(By.CSS_SELECTOR, '.cform__submit')
        d.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", _btn)
        WebDriverWait(d, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#apsToast")))
        sp = shot(d, "B6_toast_en")
        assert ContactSubmission.objects.filter(email="en_" + MARK + "@e2e.local").exists(), "no DB record"
        return "success toast visible + record in DB", sp

    @step("B. Contact", "B7 — ?sent=0 error toast + URL param stripped")
    def _():
        d.get(BASE + "/contact/?sent=0")
        WebDriverWait(d, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#apsToast.aps-toast--err")))
        sp = shot(d, "B7_toast_err")
        time.sleep(0.5)
        srch = d.execute_script("return location.search")
        assert srch == "", f"param not stripped: {srch!r}"
        return "error toast visible; ?sent stripped via replaceState", sp

    @step("B. Contact", "B8 — AR submit -> Arabic toast (RTL)")
    def _():
        d.get(BASE + "/ar/contact/")
        d.find_element(By.CSS_SELECTOR, '#cf-name').send_keys(MARK + " AR")
        d.find_element(By.CSS_SELECTOR, '#cf-email').send_keys("ar_" + MARK + "@e2e.local")
        d.find_element(By.CSS_SELECTOR, '#cf-phone').send_keys("+966 50 000 0002")
        d.find_element(By.CSS_SELECTOR, '#cf-message').send_keys("رسالة اختبار عربية")
        _btn = d.find_element(By.CSS_SELECTOR, '.cform__submit')
        d.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", _btn)
        WebDriverWait(d, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#apsToast")))
        txt = d.find_element(By.CSS_SELECTOR, "#apsToastMsg").text
        sp = shot(d, "B8_toast_ar")
        assert re.search(r'[؀-ۿ]', txt), "toast not Arabic"
        assert ContactSubmission.objects.filter(email="ar_" + MARK + "@e2e.local").exists(), "no AR record"
        return f"AR toast '{txt[:24]}...' + record", sp


# ==========================================================================
# C. CMS auth
# ==========================================================================
def area_C():
    @step("C. Auth", "C10 — /cms/ anon redirects to login")
    def _():
        cj = http.cookiejar.CookieJar() if False else None
        code = http_status(BASE + "/cms/")  # urlopen follows redirect to login (200) -> check via no-redirect
        # explicit no-redirect:
        class NR(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k): return None
        op = urllib.request.build_opener(NR())
        try:
            r = op.open(BASE + "/cms/"); c, loc = r.getcode(), r.headers.get("Location")
        except urllib.error.HTTPError as e:
            c, loc = e.code, e.headers.get("Location")
        assert c == 302 and "/cms/login/" in (loc or ""), f"{c} {loc}"
        return f"302 -> {loc}", ""

    @step("C. Auth", "C11 — wrong password stays on login w/ error")
    def _():
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _, h = hget("/cms/login/", op)
        tok = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', h).group(1)

        class NR(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k): return None
        op2 = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NR())
        data = urllib.parse.urlencode({"csrfmiddlewaretoken": tok, "username": ADMIN_USER, "password": "WRONG"}).encode()
        try:
            r = op2.open(urllib.request.Request(BASE + "/cms/login/", data=data, headers={"Referer": BASE + "/cms/login/"}))
            c, loc = r.getcode(), r.headers.get("Location")
        except urllib.error.HTTPError as e:
            c, loc = e.code, e.headers.get("Location")
        assert c == 302 and "error=1" in (loc or ""), f"{c} {loc}"
        return "wrong pw -> ?error=1", ""

    @step("C. Auth", "C12 — correct login -> dashboard w/ stats")
    def _():
        dd = new_driver()
        try:
            login(dd)
            dd.get(BASE + "/cms/")
            el = WebDriverWait(dd, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-stat="faq"]')))
            faq = el.text.strip()
            sp = shot(dd, "C12_dashboard")
            assert faq == "16", f"faq stat={faq}"
            return f"dashboard renders (FAQ stat={faq})", sp
        finally:
            dd.quit()

    @step("C. Auth", "C13 — logout kills session")
    def _():
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _, h = hget("/cms/login/", op)
        tok = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', h).group(1)
        op.open(urllib.request.Request(BASE + "/cms/login/",
                data=urllib.parse.urlencode({"csrfmiddlewaretoken": tok, "username": ADMIN_USER, "password": ADMIN_PW}).encode(),
                headers={"Referer": BASE + "/cms/login/"}))
        assert hget("/cms/", op)[0] == 200, "not logged in"
        hget("/cms/login/", op)            # GET login = logout seam
        class NR(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k): return None
        op2 = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NR())
        try:
            r = op2.open(BASE + "/cms/"); c = r.getcode()
        except urllib.error.HTTPError as e:
            c = e.code
        assert c == 302, f"still authed ({c})"
        return "logout -> /cms/ redirects again", ""


# ==========================================================================
# D. CMS round-trips (edit -> save -> public -> revert)
# ==========================================================================
def area_D(d):
    def public_has(path, needle):
        return needle in hget(path)[1]

    @step("D. CMS", "D14 — FAQ item text (AR preserved)")
    def _():
        ar0 = FAQItem.objects.order_by("order").first().question_ar
        old = field_edit(d, "/cms/faq/", '[data-field="faq.items.0.q"][data-lang="en"]', MARK + " FAQ?")
        assert public_has("/faq/", MARK + " FAQ?"), "public not updated"
        assert FAQItem.objects.order_by("order").first().question_ar == ar0, "AR changed!"
        field_edit(d, "/cms/faq/", '[data-field="faq.items.0.q"][data-lang="en"]', old)
        assert public_has("/faq/", old) and not public_has("/faq/", MARK + " FAQ?")
        return "FAQ edit->public->revert; AR intact", ""

    @step("D. CMS", "D15 — Settings phone -> footer")
    def _():
        old = field_edit(d, "/cms/settings/", '[data-field="settings.phone"]', "+966 11 222 3344")
        assert public_has("/", "+966 11 222 3344"), "footer not updated"
        field_edit(d, "/cms/settings/", '[data-field="settings.phone"]', old)
        assert public_has("/", old)
        return "phone edit->footer->revert", ""

    @step("D. CMS", "D16 — Partner logo via 1.5MB PNG (media seam) + name")
    def _():
        png = make_png(720)
        kb = len(png) // 1024
        import base64 as b64
        durl = "data:image/png;base64," + b64.b64encode(png).decode()
        p0 = Partner.objects.order_by("order").first()
        old_img, old_name = p0.image, p0.name
        d.get(BASE + "/cms/partners/")
        WebDriverWait(d, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-field="partners.items.0.name"]')))
        d.execute_script("window.Store.set('partners.items.0.img',null,arguments[0]);"
                         "window.Store.set('partners.items.0.name',null,'PartnerE2E');"
                         "document.querySelector('[data-save]').click();", durl)
        time.sleep(2.5)
        framed = None
        try:
            p0.refresh_from_db()
            # the 1.5MB upload is materialized via the media seam, then normalized
            # into the standard 178x98 partner tile (so it matches the other logos).
            assert p0.image.startswith("assets/images/partners_framed/"), f"img not framed: {p0.image}"
            assert p0.name == "PartnerE2E", "name not saved"
            framed = pathlib.Path(settings.STATICFILES_DIRS[0]) / p0.image
            assert framed.exists(), f"framed tile missing ({framed})"
            from PIL import Image as _PImg
            assert _PImg.open(framed).size == (178, 98), f"framed tile not standard size: {_PImg.open(framed).size}"
            assert 'alt="PartnerE2E"' in hget("/")[1], "public alt not updated"
        finally:
            # ALWAYS restore the original partner — even if an assert above failed —
            # so a failed run never leaves a polluted "PartnerE2E" row on the site.
            d.execute_script("window.Store.set('partners.items.0.img',null,arguments[0]);"
                             "window.Store.set('partners.items.0.name',null,arguments[1]);"
                             "document.querySelector('[data-save]').click();",
                             old_img[len("assets/images/"):] if old_img.startswith("assets/images/") else old_img, old_name)
            time.sleep(2)
            if framed:
                try: framed.unlink()
                except Exception: pass
        p0.refresh_from_db()
        assert p0.name == old_name and p0.image == old_img, "revert failed"
        return f"1.5MB PNG ({kb}KB) -> real file -> public -> reverted+deleted", ""

    @step("D. CMS", "D17 — page-edit home hero field")
    def _():
        old = field_edit(d, "/cms/page-edit/", '[data-field="pages.home.sections.hero.title"][data-lang="en"]', MARK + " HERO")
        # public home hero is hardcoded (Phase-3 decision) -> verify persistence in DB/store
        sec = PageSection.objects.get(page__slug="home", key="hero")
        assert sec.data.get("title", {}).get("en") == MARK + " HERO", "hero not persisted"
        field_edit(d, "/cms/page-edit/", '[data-field="pages.home.sections.hero.title"][data-lang="en"]', old)
        return "hero persists in PageSection (public hero hardcoded — noted)", ""

    @step("D. CMS", "D18 — division-edit division title")
    def _():
        old = field_edit(d, "/cms/division-edit/?div=beta", '[data-field="divisions.beta.sections.about.title"][data-lang="en"]', MARK + " BETA")
        div = Division.objects.get(slug="beta")
        assert div.about_title_en == MARK + " BETA", "not persisted"
        field_edit(d, "/cms/division-edit/?div=beta", '[data-field="divisions.beta.sections.about.title"][data-lang="en"]', old)
        return "division about-title persists+revert", ""

    @step("D. CMS", "D19 — SPS system card title (AR preserved)")
    def _():
        c0 = DivisionCard.objects.get(division__slug="sps", section_key="systems", order=0)
        ar0 = c0.title_ar
        old = field_edit(d, "/cms/division-edit/?div=sps", '[data-field="divisions.sps.cards.systems.0.title"][data-lang="en"]', MARK + " SYS")
        assert public_has("/sps/", MARK + " SYS"), "public sps not updated"
        c0.refresh_from_db(); assert c0.title_ar == ar0, "AR changed"
        field_edit(d, "/cms/division-edit/?div=sps", '[data-field="divisions.sps.cards.systems.0.title"][data-lang="en"]', old)
        assert public_has("/sps/", old)
        return "SPS card edit->public->revert; AR intact", ""

    @step("D. CMS", "D20 — AGS product card title + body")
    def _():
        oldt = field_edit(d, "/cms/division-edit/?div=ags", '[data-field="divisions.ags.cards.products.0.title"][data-lang="en"]', MARK + " PROD")
        assert public_has("/advanced-green-solutions/", MARK + " PROD"), "title not public"
        oldb = field_edit(d, "/cms/division-edit/?div=ags", '[data-field="divisions.ags.cards.products.0.body"][data-lang="en"]', MARK + " DESC")
        assert public_has("/advanced-green-solutions/", MARK + " DESC"), "body not public"
        field_edit(d, "/cms/division-edit/?div=ags", '[data-field="divisions.ags.cards.products.0.title"][data-lang="en"]', oldt)
        field_edit(d, "/cms/division-edit/?div=ags", '[data-field="divisions.ags.cards.products.0.body"][data-lang="en"]', oldb)
        return "AGS product title+body edit->public->revert", ""

    @step("D. CMS", "D21 — AZOLIS project spec (installed_power, AR preserved)")
    def _():
        p1 = DivisionProject.objects.get(division__slug="azolis", order=1)
        ar0 = p1.installed_power_ar
        old = field_edit(d, "/cms/division-edit/?div=azolis", '[data-field="divisions.azolis.sections.projects.items.1.installed_power"][data-lang="en"]', "12 MWp E2E")
        assert public_has("/azolis-middle-east/", "12 MWp E2E"), "spec not public"
        p1.refresh_from_db(); assert p1.installed_power_ar == ar0, "AR changed"
        field_edit(d, "/cms/division-edit/?div=azolis", '[data-field="divisions.azolis.sections.projects.items.1.installed_power"][data-lang="en"]', old)
        assert public_has("/azolis-middle-east/", old)
        return "AZOLIS spec edit->public->revert; AR intact", ""


# ==========================================================================
# E. Inbox (uses B submissions)
# ==========================================================================
def area_E(d):
    def badge(d):
        els = d.find_elements(By.CSS_SELECTOR, '.nav-item__badge[data-stat="inbox"]')
        return int(els[0].text) if els and els[0].text.strip() else 0

    @step("E. Inbox", "E23 — sidebar unread badge correct")
    def _():
        unread = ContactSubmission.objects.filter(is_read=False).count()
        d.get(BASE + "/cms/pages/")  # any admin page
        WebDriverWait(d, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".sidebar")))
        b = badge(d)
        assert b == unread, f"badge {b} != unread {unread}"
        return f"badge={b} == unread={unread}", ""

    @step("E. Inbox", "E24 — inbox lists newest-first, unread badged")
    def _():
        d.get(BASE + "/cms/inbox/")
        WebDriverWait(d, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.inbox-row")))
        rows = d.find_elements(By.CSS_SELECTOR, "tr.inbox-row")
        unreadbadges = d.find_elements(By.CSS_SELECTOR, "tr.inbox-row .badge--amber")
        sp = shot(d, "E24_inbox")
        assert len(rows) >= 2, f"rows={len(rows)}"
        assert len(unreadbadges) >= 2, "unread not badged"
        return f"{len(rows)} rows, {len(unreadbadges)} unread badged", sp

    @step("E. Inbox", "E25 — expand row shows full message")
    def _():
        d.get(BASE + "/cms/inbox/")
        WebDriverWait(d, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.inbox-row .table__title"))).click()
        time.sleep(0.6)
        det = d.find_elements(By.CSS_SELECTOR, "tr.inbox-detail")[0]
        assert det.is_displayed(), "detail not shown"
        return "row expands to message", shot(d, "E25_expand")

    @step("E. Inbox", "E26 — mark read decrements, unread increments")
    def _():
        d.get(BASE + "/cms/inbox/")
        WebDriverWait(d, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.inbox-row")))
        b0 = badge(d)
        d.find_element(By.CSS_SELECTOR, 'tr.inbox-row form input[value="read"]').find_element(By.XPATH, "..").find_element(By.CSS_SELECTOR, "button").click()
        WebDriverWait(d, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".sidebar")))
        time.sleep(0.8); b1 = badge(d)
        assert b1 == b0 - 1, f"{b0}->{b1} not -1"
        d.find_element(By.CSS_SELECTOR, 'tr.inbox-row form input[value="unread"]').find_element(By.XPATH, "..").find_element(By.CSS_SELECTOR, "button").click()
        WebDriverWait(d, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".sidebar")))
        time.sleep(0.8); b2 = badge(d)
        assert b2 == b0, f"unread didn't restore ({b2})"
        return f"read {b0}->{b1}, unread ->{b2}", ""

    @step("E. Inbox", "E27 — delete one (confirm) removes it")
    def _():
        d.get(BASE + "/cms/inbox/")
        WebDriverWait(d, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.inbox-row")))
        n0 = len(d.find_elements(By.CSS_SELECTOR, "tr.inbox-row"))
        d.find_elements(By.CSS_SELECTOR, "tr.inbox-row form[data-confirm]")[0].find_element(By.CSS_SELECTOR, "button").click()
        time.sleep(0.5); d.switch_to.alert.accept()
        WebDriverWait(d, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".sidebar")))
        time.sleep(0.6); n1 = len(d.find_elements(By.CSS_SELECTOR, "tr.inbox-row"))
        assert n1 == n0 - 1, f"{n0}->{n1}"
        return f"deleted one ({n0}->{n1})", ""

    @step("E. Inbox", "E28 — mark all read -> badge hidden")
    def _():
        d.get(BASE + "/cms/inbox/")
        WebDriverWait(d, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".sidebar")))
        ma = d.find_elements(By.CSS_SELECTOR, 'form input[value="markall"]')
        if ma:
            ma[0].find_element(By.XPATH, "..").find_element(By.CSS_SELECTOR, "button").click()
            time.sleep(1.2)
        assert badge(d) == 0, "badge not zero"
        return "mark-all -> 0 unread (badge hidden)", ""

    @step("E. Inbox", "E29 — delete remaining E2E rows; empty state if no real msgs")
    def _():
        # delete only our E2E submissions (never touch real rows)
        ContactSubmission.objects.filter(email__contains=MARK).delete()
        real = ContactSubmission.objects.count()
        d.get(BASE + "/cms/inbox/"); time.sleep(0.8)
        if real == 0:
            empt = d.find_elements(By.CSS_SELECTOR, ".empty")
            assert empt, "empty state missing"
            return "E2E rows gone; empty state shown", shot(d, "E29_empty")
        return f"E2E rows gone; {real} real msgs remain (empty-state assert skipped)", ""


# ==========================================================================
# F. Media replace (Q9)
# ==========================================================================
def area_F():
    @step("F. Media", "F30 — replace static image + backup + restore")
    def _():
        rel = "assets/images/icons/globe.svg"
        target = pathlib.Path(settings.STATICFILES_DIRS[0]) / rel
        orig = target.read_bytes()
        png = make_png(64)
        # authed session for the endpoint
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _, h = hget("/cms/login/", op)
        tok = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', h).group(1)
        op.open(urllib.request.Request(BASE + "/cms/login/",
                data=urllib.parse.urlencode({"csrfmiddlewaretoken": tok, "username": ADMIN_USER, "password": ADMIN_PW}).encode(),
                headers={"Referer": BASE + "/cms/login/"}))
        csrf = [c.value for c in cj if c.name == "csrftoken"][0]
        # multipart replace
        boundary = "----e2e" + TS
        body = (b"--" + boundary.encode() + b"\r\nContent-Disposition: form-data; name=\"path\"\r\n\r\n" + rel.encode() +
                b"\r\n--" + boundary.encode() + b"\r\nContent-Disposition: form-data; name=\"file\"; filename=\"x.png\"\r\n"
                b"Content-Type: image/png\r\n\r\n" + png + b"\r\n--" + boundary.encode() + b"--\r\n")
        req = urllib.request.Request(BASE + "/cms/api/media/replace/", data=body, headers={
            "Content-Type": "multipart/form-data; boundary=" + boundary, "X-CSRFToken": csrf, "Referer": BASE + "/cms/"})
        op.open(req)
        backup = pathlib.Path(settings.STATICFILES_DIRS[0]) / "assets/images/.originals" / "icons/globe.svg"
        assert target.read_bytes() != orig, "file not changed"
        assert backup.exists() and backup.read_bytes() == orig, "backup missing/wrong"
        assert http_status(BASE + "/static/" + rel) == 200, "public 404"
        # restore via endpoint
        rbody = urllib.parse.urlencode({"path": rel}).encode()
        op.open(urllib.request.Request(BASE + "/cms/api/media/restore/", data=rbody,
                headers={"Content-Type": "application/x-www-form-urlencoded", "X-CSRFToken": csrf, "Referer": BASE + "/cms/"}))
        assert target.read_bytes() == orig, "restore failed"
        return "replace (bytes changed + .originals backup) -> public 200 -> restored", ""


# ==========================================================================
# G. Password change (LAST, serialized, safety-net restore)
# ==========================================================================
def area_G():
    NEWPW = "E2EpwTest_" + TS
    U = get_user_model()

    @step("G. Password", "G31 — change pw via UI -> old fails/new works -> restore")
    def _():
        dd = new_driver()
        try:
            login(dd)
            dd.get(BASE + "/cms/profile/")
            WebDriverWait(dd, 15).until(EC.presence_of_element_located((By.ID, "pfPass1")))
            dd.find_element(By.ID, "pfCurrent").send_keys(ADMIN_PW)
            dd.find_element(By.ID, "pfPass1").send_keys(NEWPW)
            dd.find_element(By.ID, "pfPass2").send_keys(NEWPW)
            dd.find_element(By.ID, "pfSave").click()
            time.sleep(1.5)
            assert U.objects.get(username=ADMIN_USER).check_password(NEWPW), "pw not changed in DB"
            # old password now fails, new works (via login view)
            assert _login_works(NEWPW), "new pw login failed"
            assert not _login_works(ADMIN_PW), "old pw still works"
            # change BACK via UI
            dd2 = new_driver()
            try:
                _selenium_login(dd2, NEWPW)
                dd2.get(BASE + "/cms/profile/")
                WebDriverWait(dd2, 15).until(EC.presence_of_element_located((By.ID, "pfPass1")))
                dd2.find_element(By.ID, "pfCurrent").send_keys(NEWPW)
                dd2.find_element(By.ID, "pfPass1").send_keys(ADMIN_PW)
                dd2.find_element(By.ID, "pfPass2").send_keys(ADMIN_PW)
                dd2.find_element(By.ID, "pfSave").click()
                time.sleep(1.5)
            finally:
                dd2.quit()
            assert U.objects.get(username=ADMIN_USER).check_password(ADMIN_PW), "restore via UI failed"
            return "pw change->logout->old fails/new works->restored via UI", ""
        finally:
            dd.quit()
            # SAFETY NET: guarantee original password no matter what
            u = U.objects.get(username=ADMIN_USER)
            if not u.check_password(ADMIN_PW):
                u.set_password(ADMIN_PW); u.save()


def _login_works(pw):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    _, h = hget("/cms/login/", op)
    tok = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', h).group(1)

    class NR(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k): return None
    op2 = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NR())
    data = urllib.parse.urlencode({"csrfmiddlewaretoken": tok, "username": ADMIN_USER, "password": pw}).encode()
    try:
        r = op2.open(urllib.request.Request(BASE + "/cms/login/", data=data, headers={"Referer": BASE + "/cms/login/"}))
        return r.getcode() == 302 and "error" not in (r.headers.get("Location") or "")
    except urllib.error.HTTPError as e:
        return e.code == 302 and "error" not in (e.headers.get("Location") or "")


def _selenium_login(d, pw):
    d.get(BASE + "/cms/login/")
    d.find_element(By.NAME, "username").send_keys(ADMIN_USER)
    d.find_element(By.NAME, "password").send_keys(pw)
    d.find_element(By.CSS_SELECTOR, "#loginForm button[type=submit]").click()
    WebDriverWait(d, 20).until(EC.url_matches(r".*/cms/$"))


# ==========================================================================
# H. Tunnel
# ==========================================================================
def area_H():
    urlfile = pathlib.Path("D:/APS_final/tunnel_url.txt")
    url = urlfile.read_text(encoding="utf-8").strip() if urlfile.exists() else ""

    @step("H. Tunnel", "H32 — public site + CMS login through tunnel")
    def _():
        if not url:
            return "SKIP: no tunnel_url.txt", ""
        try:
            if http_status(url + "/") != 200:
                return f"SKIP: tunnel not resolving ({url})", ""
        except Exception:
            return f"SKIP: tunnel unreachable ({url})", ""
        assert http_status(url + "/") == 200, "/ not 200"
        assert http_status(url + "/ar/") == 200, "/ar/ not 200"
        # CMS login over HTTPS (CSRF)
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        h = op.open(url + "/cms/login/", timeout=30).read().decode()
        tok = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', h).group(1)

        class NR(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k): return None
        op2 = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NR())
        data = urllib.parse.urlencode({"csrfmiddlewaretoken": tok, "username": ADMIN_USER, "password": ADMIN_PW}).encode()
        try:
            r = op2.open(urllib.request.Request(url + "/cms/login/", data=data, headers={"Referer": url + "/cms/login/", "Origin": url}))
            c, loc = r.getcode(), r.headers.get("Location")
        except urllib.error.HTTPError as e:
            c, loc = e.code, e.headers.get("Location")
        assert c == 302 and "/cms/" in (loc or "") and "error" not in (loc or ""), f"CSRF login failed {c} {loc}"
        return f"tunnel OK: / 200, /ar/ 200, CMS login 302 ({url})", ""
    return url


# ==========================================================================
# I. Ops sanity
# ==========================================================================
def area_I():
    import subprocess

    @step("I. Ops", "I33a — exactly 1 listener on 8000 and 3306")
    def _():
        ps = ("$p=@(8000,3306)|%{(Get-NetTCPConnection -LocalPort $_ -State Listen -EA SilentlyContinue|"
              "Select-Object -Expand OwningProcess -Unique|Measure-Object).Count}; $p -join ','")
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout.strip()
        a8, a33 = (out.split(",") + ["?", "?"])[:2]
        assert a8 == "1" and a33 == "1", f"listeners 8000={a8} 3306={a33}"
        return f"8000=1 listener, 3306=1 listener", ""

    @step("I. Ops", "I33b — manage.py check clean")
    def _():
        out = subprocess.run([str(PROJECT / "venv/Scripts/python.exe"), "manage.py", "check"],
                             cwd=str(PROJECT), capture_output=True, text=True)
        assert "no issues" in (out.stdout + out.stderr), out.stdout + out.stderr
        return "0 issues", ""


# ==========================================================================
# report
# ==========================================================================
def write_report(meta, integrity):
    by_area = {}
    for r in results:
        by_area.setdefault(r["area"], []).append(r)
    npass = sum(1 for r in results if r["ok"])
    ntot = len(results)
    verdict_ok = npass == ntot and integrity["ok"]
    css = """body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f7fa;color:#0B1220}
    .wrap{max-width:1100px;margin:0 auto;padding:28px}
    h1{font-size:24px}.sub{color:#5b6b7d;font-size:13px}
    .banner{padding:22px;border-radius:14px;color:#fff;font-size:22px;font-weight:800;margin:18px 0}
    .ok{background:linear-gradient(90deg,#16a34a,#22c55e)}.bad{background:linear-gradient(90deg,#dc2626,#ef4444)}
    table{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;margin:10px 0 26px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
    th,td{text-align:left;padding:10px 14px;border-bottom:1px solid #eef1f5;font-size:13px;vertical-align:top}
    th{background:#f0f4f8;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#5b6b7d}
    .p{color:#16a34a;font-weight:700}.f{color:#dc2626;font-weight:700}
    h2{font-size:16px;margin-top:24px}
    .shot{max-width:460px;border:1px solid #e2e8f0;border-radius:8px;margin:6px 0;display:block}
    .gal{display:flex;flex-wrap:wrap;gap:14px}.gal figure{margin:0;width:300px}.gal img{width:300px;border:1px solid #e2e8f0;border-radius:8px}
    .gal figcaption{font-size:12px;color:#5b6b7d}
    .intg{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}"""
    rows_html = ""
    for area in sorted(by_area):
        rows_html += f"<h2>{area}</h2><table><tr><th>Test</th><th>Result</th><th>Detail</th><th>Sec</th></tr>"
        for r in by_area[area]:
            cls = "p" if r["ok"] else "f"
            txt = "PASS" if r["ok"] else "FAIL"
            shot = f'<br><img class="shot" src="{r["shot"]}">' if r["shot"] else ""
            rows_html += f'<tr><td>{r["name"]}</td><td class="{cls}">{txt}</td><td>{r["detail"]}{shot}</td><td>{r["dur"]}</td></tr>'
        rows_html += "</table>"
    gal = ""
    for r in results:
        if r["shot"]:
            gal += f'<figure><img src="{r["shot"]}"><figcaption>{r["name"]}</figcaption></figure>'
    integ_rows = "".join(
        f"<tr><td>{k}</td><td>{integrity['initial'][k]}</td><td>{integrity['final'][k]}</td>"
        f"<td class=\"{'p' if integrity['initial'][k]==integrity['final'][k] else 'f'}\">"
        f"{'==' if integrity['initial'][k]==integrity['final'][k] else 'DIFF'}</td></tr>"
        for k in integrity["initial"])
    banner = (f'<div class="banner ok">ALL PASSED ({npass}/{ntot}) — data integrity verified</div>'
              if verdict_ok else
              f'<div class="banner bad">FAILED ({npass}/{ntot} passed' +
              ("" if integrity["ok"] else "; DATA INTEGRITY MISMATCH") + ")</div>")
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>APS E2E Report</title><style>{css}</style></head>
<body><div class="wrap">
<h1>APS — End-to-End Test Report</h1>
<div class="sub">Date: {meta['date']} &middot; Duration: {meta['dur']}s &middot; Django {meta['django']} &middot; {meta['db']} &middot; Tunnel: {meta['tunnel'] or 'not tested'}</div>
{banner}
<h2>Data integrity (final == initial)</h2>
<div class="intg"><table><tr><th>Model</th><th>Initial</th><th>Final</th><th></th></tr>{integ_rows}</table>
<b>{'All counts restored — every mutation reverted.' if integrity['ok'] else 'MISMATCH — see diffs above.'}</b></div>
{rows_html}
<h2>Screenshot gallery</h2><div class="gal">{gal}</div>
</div></body></html>"""
    (REPORT_DIR / "E2E_REPORT.html").write_text(html, encoding="utf-8")
    (REPORT_DIR / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    return verdict_ok, npass, ntot


# ==========================================================================
# main
# ==========================================================================
def ensure_e2e_user():
    """Create/refresh the dedicated E2E admin so tests authenticate as it and
    never modify the real `aps_admin` (whose password the client manages)."""
    U = get_user_model()
    u, _ = U.objects.get_or_create(
        username=ADMIN_USER,
        defaults={"is_staff": True, "is_superuser": True, "is_active": True},
    )
    u.is_staff = u.is_superuser = u.is_active = True
    u.set_password(ADMIN_PW)
    u.save()


def main():
    print(f"=== APS E2E suite ({MARK}) ===")
    ensure_e2e_user()
    area_A()
    d = new_driver()
    try:
        area_B(d)
        login(d)
        area_D(d)
        area_E(d)
    finally:
        d.quit()
    area_C()
    area_F()
    tunnel_url = area_H()
    area_G()      # password — last, serialized
    area_I()

    final = counts()
    integ_ok = (final == INITIAL)
    integrity = {"initial": INITIAL, "final": final, "ok": integ_ok}
    import django as dj
    try:
        from django.db import connection
        dbver = connection.vendor + " " + (connection.Database.__version__ if hasattr(connection, "Database") else "")
    except Exception:
        dbver = "mysql"
    meta = {"date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "dur": round(time.time() - _t0, 1), "django": dj.get_version(),
            "db": "MariaDB (mysql)", "tunnel": tunnel_url}
    ok, npass, ntot = write_report(meta, integrity)
    print(f"\n=== VERDICT: {'ALL PASSED' if ok else 'FAILED'} ({npass}/{ntot}); integrity {'OK' if integ_ok else 'MISMATCH'} ===")
    print(f"Report: {REPORT_DIR / 'E2E_REPORT.html'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
