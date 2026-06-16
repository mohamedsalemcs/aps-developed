"""CMS admin views — serve the designer's admin pages, auth, and the Store API.

Phase 4 Step 2 adds real Django session auth. The store-JSON bootstrap (Step 4)
and APIs (Step 3/5) are layered on top.
"""
import base64
import json
import re
import shutil
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth import (authenticate, login as auth_login, logout as auth_logout,
                                 get_user_model, update_session_auth_hash)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseBadRequest, Http404
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404

from submissions.models import ContactSubmission
from core.models import EditLog
from .store_api import build_store, apply_store

# referer path -> (en, ar) label for the dashboard "Recent edits" log
_EDIT_LABELS = {
    "/cms/faq/": ("FAQ", "الأسئلة الشائعة"),
    "/cms/settings/": ("Settings", "الإعدادات"),
    "/cms/brand/": ("Brand & theme", "الهوية والتصميم"),
    "/cms/partners/": ("Partners", "الشركاء"),
    "/cms/page-edit/": ("Home page", "الصفحة الرئيسية"),
    "/cms/about-edit/": ("About page", "صفحة عن الشركة"),
    "/cms/contact-edit/": ("Contact page", "صفحة اتصل بنا"),
    "/cms/division-edit/": ("Division", "قسم"),
}


def _edit_label(referer):
    from urllib.parse import urlparse
    p = urlparse(referer or "").path
    for k, v in _EDIT_LABELS.items():
        if p.startswith(k):
            return v
    return ("Content", "محتوى")


class CmsPageView(LoginRequiredMixin, TemplateView):
    """Serves one admin page and injects the full store JSON (built from the DB)
    so our store.js can bootstrap synchronously before admin.js runs. Also
    exposes the unread-message count so every page's sidebar Inbox badge shows it.
    """
    login_url = "/cms/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["store_data"] = build_store()
        ctx["unread_count"] = ContactSubmission.objects.filter(is_read=False).count()
        ctx["msg_total"] = ContactSubmission.objects.count()
        ctx["recent_edits"] = EditLog.objects.all()[:5]
        # admin identity for the chrome (sidebar/topbar/profile) — rendered from
        # the real Django user so a name/email change in the profile reflects.
        u = self.request.user
        name = ((u.get_full_name() or u.first_name or u.get_username()).strip()
                if u.is_authenticated else "")
        ctx["admin_name"] = name
        ctx["admin_email"] = (u.email or "") if u.is_authenticated else ""
        ctx["admin_initial"] = (name[:1].upper() if name else "A")
        # the dashboard greeting uses the real first name if the admin set one,
        # else a generic "welcome back".
        ctx["admin_first"] = (u.first_name.strip() if u.is_authenticated else "")
        return ctx


class InboxView(CmsPageView):
    """Contact-submissions inbox — server-rendered (transactional data, not the
    store). Inherits store_data + unread_count from CmsPageView for the chrome."""
    template_name = "cms/inbox.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = ContactSubmission.objects.all()  # model Meta orders by -created_at
        paginator = Paginator(qs, 10)  # reviewer: paginate after 10 rows
        page = paginator.get_page(self.request.GET.get("page"))
        ctx["page_obj"] = page
        ctx["submissions"] = page.object_list
        return ctx


@login_required(login_url="/cms/login/")
@require_POST
def inbox_action(request):
    """Mark read/unread, delete, or mark-all-read; redirect back (PRG)."""
    op = request.POST.get("op")
    page = request.POST.get("page", "")
    if op == "markall":
        ContactSubmission.objects.filter(is_read=False).update(is_read=True)
    elif op == "bulkdelete":
        ids = [i for i in request.POST.getlist("ids") if i.isdigit()]
        if ids:
            ContactSubmission.objects.filter(pk__in=ids).delete()
    elif op in ("read", "unread", "delete"):
        sub = get_object_or_404(ContactSubmission, pk=request.POST.get("id"))
        if op == "delete":
            sub.delete()
        else:
            sub.is_read = (op == "read")
            sub.save(update_fields=["is_read"])
    back = "/cms/inbox/"
    if page:
        back += f"?page={page}"
    return redirect(back)

# /cms/ url name -> admin template
CMS_PAGES = {
    "index": "cms/index.html",
    "pages": "cms/pages.html",
    "page-edit": "cms/page-edit.html",
    "about-edit": "cms/about-edit.html",
    "contact-edit": "cms/contact-edit.html",
    "divisions": "cms/divisions.html",
    "division-edit": "cms/division-edit.html",
    "faq": "cms/faq.html",
    "partners": "cms/partners.html",
    "media": "cms/media.html",
    "settings": "cms/settings.html",
    "brand": "cms/brand.html",
    "profile": "cms/profile.html",
    "preview": "cms/preview.html",
    "qa-tests": "cms/qa-tests.html",
}


_REDIRECT_NAMES = set(CMS_PAGES.keys()) | {"login", "index"}


def cms_html_redirect(request, name):
    """301 the designer's relative '<name>.html' admin links (which admin.js
    builds dynamically, e.g. /cms/divisions/division-edit.html?div=...) to the
    real /cms/<name>/ route, preserving the querystring. Unknown names -> 404.
    Lets us fix the links WITHOUT touching admin.js."""
    if name not in _REDIRECT_NAMES:
        raise Http404("unknown cms page")
    target = "/cms/" if name == "index" else f"/cms/{name}/"
    qs = request.META.get("QUERY_STRING", "")
    return redirect(target + ("?" + qs if qs else ""), permanent=True)


def cms_login(request):
    """Real session login for the designer's login.html.

    POST authenticates (by username or email) and redirects to /cms/.
    GET logs out any active session — the designer's logout button (handled in
    his untouched admin.js) navigates here, so this is also the logout seam.
    """
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if user is None and username:
            U = get_user_model()
            match = U.objects.filter(email__iexact=username).first()
            if match:
                user = authenticate(request, username=match.get_username(), password=password)
        if user is not None and user.is_active:
            auth_login(request, user)
            return redirect("/cms/")
        return redirect("/cms/login/?error=1")

    # GET: terminate any active session (logout seam) then show the form.
    if request.user.is_authenticated:
        auth_logout(request)
    return render(request, "cms/login.html", {"error": request.GET.get("error") == "1"})


@login_required(login_url="/cms/login/")
@require_GET
def store_get(request):
    """Full store JSON built from the DB, in his store.js shape."""
    return JsonResponse(build_store())


@login_required(login_url="/cms/login/")
@require_POST
def store_save(request):
    """Persist the full store tree posted by our store.js (CSRF-protected)."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest("invalid JSON")
    apply_store(data)
    en, ar = _edit_label(request.META.get("HTTP_REFERER"))
    EditLog.objects.create(user=request.user.get_username(), label_en=en, label_ar=ar)
    return JsonResponse({"ok": True})


_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg",
        "image/svg+xml": "svg", "image/webp": "webp", "image/gif": "gif"}

# Uploads land in the static assets tree (not MEDIA_ROOT): his unedited admin.js
# previews images as ../../website/assets/images/<value> and the public site
# renders {% static 'assets/images/'+value %} — this dir is the only path both
# resolve to. Returned value is "uploads/<file>" (relative, his schema).
UPLOAD_DIR = Path(settings.STATICFILES_DIRS[0]) / "assets" / "images" / "uploads"


@login_required(login_url="/cms/login/")
@require_POST
def media_upload(request):
    """Persist an uploaded image to disk and return its store value.

    Accepts JSON {dataurl: "data:<mime>;base64,..."} (the form our store.js
    sends when materializing the data-URLs his admin produces) or a multipart
    'file'. Returns {"value": "uploads/<file>"}.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    if "application/json" in (request.content_type or ""):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return HttpResponseBadRequest("invalid JSON")
        m = re.match(r"data:([^;]+);base64,(.*)$", payload.get("dataurl", ""), re.DOTALL)
        if not m:
            return HttpResponseBadRequest("expected a base64 data URL")
        mime, b64 = m.group(1).lower(), m.group(2)
        try:
            raw = base64.b64decode(b64)
        except Exception:
            return HttpResponseBadRequest("bad base64")
        ext = _EXT.get(mime, "bin")
    else:
        f = request.FILES.get("file")
        if not f:
            return HttpResponseBadRequest("no file")
        raw = f.read()
        ext = _EXT.get((f.content_type or "").lower(), (f.name.rsplit(".", 1)[-1] or "bin").lower())

    fname = f"{uuid.uuid4().hex}.{ext}"
    (UPLOAD_DIR / fname).write_bytes(raw)
    return JsonResponse({"value": f"uploads/{fname}"})


_STATIC_IMG = Path(settings.STATICFILES_DIRS[0]).resolve() / "assets" / "images"
_ORIGINALS = _STATIC_IMG / ".originals"


def _safe_asset(rel):
    """Resolve a path under assets/images/, refusing traversal. rel is the
    'assets/images/...'-style path used in the site. Returns abs Path or None."""
    if not rel:
        return None
    rel = rel[len("assets/images/"):] if rel.startswith("assets/images/") else rel
    target = (_STATIC_IMG / rel).resolve()
    try:
        target.relative_to(_STATIC_IMG)
    except ValueError:
        return None
    return target


@login_required(login_url="/cms/login/")
@require_POST
def media_replace(request):
    """Replace an existing static design image in place, backing up the original
    once to assets/images/.originals/ so it can be restored."""
    rel = request.POST.get("path", "")
    f = request.FILES.get("file")
    if not f:
        return HttpResponseBadRequest("file required")
    target = _safe_asset(rel)
    if not target or not target.exists():
        return HttpResponseBadRequest("no such asset")
    suffix = str(target.relative_to(_STATIC_IMG))
    backup = _ORIGINALS / suffix
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(target, backup)
    target.write_bytes(f.read())
    return JsonResponse({"ok": True, "backup": "assets/images/.originals/" + suffix.replace("\\", "/")})


@login_required(login_url="/cms/login/")
@require_POST
def media_restore(request):
    """Restore a previously-replaced image from its .originals backup."""
    rel = request.POST.get("path", "")
    target = _safe_asset(rel)
    if not target:
        return HttpResponseBadRequest("bad path")
    backup = _ORIGINALS / str(target.relative_to(_STATIC_IMG))
    if not backup.exists():
        return HttpResponseBadRequest("no backup")
    shutil.copy2(backup, target)
    return JsonResponse({"ok": True})


@login_required(login_url="/cms/login/")
@require_POST
def profile_password(request):
    """Change the logged-in admin's password (real Django auth), keeping the
    session alive. Wired from profile.html via a contained script."""
    new = request.POST.get("password") or ""
    if len(new) < 8:
        return JsonResponse({"ok": False, "error": "min 8 chars"}, status=400)
    request.user.set_password(new)
    request.user.save()
    update_session_auth_hash(request, request.user)
    return JsonResponse({"ok": True})


@login_required(login_url="/cms/login/")
@require_POST
def profile_save(request):
    """Save the admin profile to the real Django user: display name + email
    always; password only when a new one is supplied AND the current password
    checks out. Replaces the designer's localStorage-only save (which silently
    lost changes), so edits actually persist and the name reflects across the UI.
    """
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError as _VErr

    u = request.user
    name = (request.POST.get("name") or "").strip()
    email = (request.POST.get("email") or "").strip()
    current = request.POST.get("current_password") or ""
    new = request.POST.get("new_password") or ""

    if email:
        try:
            validate_email(email)
        except _VErr:
            return JsonResponse({"ok": False, "error": "البريد الإلكتروني غير صحيح"}, status=400)

    if new:
        if not u.check_password(current):
            return JsonResponse({"ok": False, "error": "كلمة المرور الحالية غير صحيحة"}, status=400)
        if len(new) < 8:
            return JsonResponse({"ok": False, "error": "كلمة المرور الجديدة قصيرة (8 أحرف على الأقل)"}, status=400)
        u.set_password(new)

    if name:
        u.first_name = name
    if email:
        u.email = email
    u.save()
    if new:
        update_session_auth_hash(request, u)
    return JsonResponse({"ok": True})


# --- Forgot-password: emailed one-time code (self-service from the login page) ---
import secrets as _secrets


@require_POST
def forgot_request(request):
    """Step 1: the user enters their email; if it matches the admin account we
    generate a 6-digit code, store it, and email it. Not login-required (the
    user is locked out). CSRF-protected like every POST."""
    from core.models import PasswordResetCode
    from django.core.mail import send_mail
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest("invalid JSON")
    email = (data.get("email") or "").strip()
    U = get_user_model()
    user = U.objects.filter(email__iexact=email).first() if email else None
    if not user:
        return JsonResponse({"ok": False, "error": "البريد الإلكتروني غير مسجّل."}, status=400)

    code = "".join(_secrets.choice("0123456789") for _ in range(6))
    # supersede any previous outstanding codes for this user
    PasswordResetCode.objects.filter(username=user.get_username(), used=False).update(used=True)
    PasswordResetCode.objects.create(username=user.get_username(), code=code)
    try:
        send_mail(
            subject="كود إعادة تعيين كلمة المرور — APS CMS",
            message=("كود إعادة تعيين كلمة المرور الخاص بك هو: %s\n"
                     "صالح لمدة 15 دقيقة. لو مش إنت اللي طلبته، تجاهل الرسالة.\n\n"
                     "Your APS CMS password reset code is: %s (valid for 15 minutes)." % (code, code)),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:
        return JsonResponse({"ok": False, "error": "تعذّر إرسال البريد — تأكد من إعداد الإيميل."}, status=500)
    return JsonResponse({"ok": True})


@require_POST
def forgot_verify(request):
    """Step 2: verify email + code, then set the new password."""
    from core.models import PasswordResetCode
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest("invalid JSON")
    email = (data.get("email") or "").strip()
    code = (data.get("code") or "").strip()
    new = data.get("password") or ""
    U = get_user_model()
    user = U.objects.filter(email__iexact=email).first() if email else None
    if not user:
        return JsonResponse({"ok": False, "error": "البريد الإلكتروني غير مسجّل."}, status=400)
    if len(new) < 8:
        return JsonResponse({"ok": False, "error": "كلمة المرور الجديدة قصيرة (8 أحرف على الأقل)."}, status=400)
    prc = PasswordResetCode.objects.filter(
        username=user.get_username(), code=code, used=False).first()
    if not prc or not prc.is_valid():
        return JsonResponse({"ok": False, "error": "الكود غير صحيح أو منتهي الصلاحية."}, status=400)
    user.set_password(new)
    user.save()
    PasswordResetCode.objects.filter(username=user.get_username(), used=False).update(used=True)
    return JsonResponse({"ok": True})


@require_POST
def forgot_check(request):
    """Step 2 (its own screen): validate the emailed code WITHOUT consuming it,
    so the user confirms the code before being shown the new-password screen."""
    from core.models import PasswordResetCode
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest("invalid JSON")
    email = (data.get("email") or "").strip()
    code = (data.get("code") or "").strip()
    U = get_user_model()
    user = U.objects.filter(email__iexact=email).first() if email else None
    if not user:
        return JsonResponse({"ok": False, "error": "البريد الإلكتروني غير مسجّل."}, status=400)
    prc = PasswordResetCode.objects.filter(
        username=user.get_username(), code=code, used=False).first()
    if not prc or not prc.is_valid():
        return JsonResponse({"ok": False, "error": "الكود غير صحيح أو منتهي الصلاحية."}, status=400)
    return JsonResponse({"ok": True})


# --- Restore-to-factory-defaults (per edit page) -------------------------------
_FACTORY_PATH = Path(__file__).resolve().parent / "factory_defaults.json"


def _path_get(tree, dotted):
    cur = tree
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _path_set(tree, dotted, value):
    keys = dotted.split(".")
    cur = tree
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value


@login_required(login_url="/cms/login/")
@require_POST
def factory_reset(request):
    """Restore ONE scope (the current edit page) to the approved factory content.
    Takes {scope}: settings | brand | partners | faq | pages.<slug> | divisions.<slug>.
    Loads the captured factory snapshot, swaps just that scope into the live
    store, and re-saves — so other pages are untouched (the 'undo everything I
    did to THIS page' safety net)."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest("invalid JSON")
    scope = (data.get("scope") or "").strip()
    ok_scope = (scope in ("settings", "brand", "partners", "faq")
                or scope.startswith("pages.") or scope.startswith("divisions."))
    if not ok_scope:
        return JsonResponse({"ok": False, "error": "نطاق غير معروف"}, status=400)
    try:
        factory = json.loads(_FACTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "لا توجد نسخة افتراضية محفوظة"}, status=500)
    fval = _path_get(factory, scope)
    if fval is None:
        return JsonResponse({"ok": False, "error": "لا توجد قيمة افتراضية لهذا النطاق"}, status=400)
    live = build_store()
    _path_set(live, scope, fval)
    apply_store(live)
    EditLog.objects.create(user=request.user.get_username(),
                           label_en="Restore defaults", label_ar="عودة للافتراضية")
    return JsonResponse({"ok": True})
