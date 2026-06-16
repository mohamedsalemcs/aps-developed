import re

from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from .models import ContactSubmission

# Per-language field-error messages, rendered inline under the offending field.
_MSGS = {
    "en": {
        "name": "Please enter your full name.",
        "email": "Please enter a valid email address (e.g. you@example.com).",
        "phone": "Please enter a valid phone number.",
        "message": "Please enter your message.",
    },
    "ar": {
        "name": "من فضلك اكتب اسمك بالكامل.",
        "email": "من فضلك اكتب بريدًا إلكترونيًا صحيحًا (مثل you@example.com).",
        "phone": "من فضلك اكتب رقم هاتف صحيح.",
        "message": "من فضلك اكتب رسالتك.",
    },
}


def _validate(name, email, phone, message, M):
    """Return a dict of field -> message for every invalid field (empty = OK).
    This is the source of truth: a bad email never reaches the database even
    if the browser-side checks are bypassed."""
    errors = {}
    if len(name) < 2:
        errors["name"] = M["name"]
    try:
        validate_email(email)
    except ValidationError:
        errors["email"] = M["email"]
    if len(re.sub(r"\D", "", phone)) < 7:
        errors["phone"] = M["phone"]
    if len(message) < 5:
        errors["message"] = M["message"]
    return errors


@require_POST
def contact_submit(request):
    """Handle the contact form (shared by EN + AR). Validates server-side; on
    error re-renders the contact page with inline field messages and the user's
    values preserved. On success saves a ContactSubmission and redirects back
    with ?sent=1 (Post/Redirect/Get).

    Language is inferred from the Referer (so no extra markup is added to the
    designer's form beyond action + {% csrf_token %}); defaults to EN.
    """
    name = (request.POST.get("name") or "").strip()
    email = (request.POST.get("email") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    company = (request.POST.get("company") or "").strip()
    message = (request.POST.get("message") or "").strip()

    is_ar = "/ar/" in (request.META.get("HTTP_REFERER") or "")
    lang = "ar" if is_ar else "en"

    errors = _validate(name, email, phone, message, _MSGS[lang])
    if errors:
        # re-render the same page with errors + the values the user typed so
        # nothing is lost and each problem shows under its field.
        ctx = {
            "form_errors": errors,
            "form_old": {"name": name, "email": email, "phone": phone,
                         "company": company, "message": message},
        }
        return render(request, f"{lang}/contact.html", ctx, status=400)

    ContactSubmission.objects.create(
        name=name, email=email, phone=phone, company=company, message=message)
    back = "/ar/contact/" if is_ar else "/contact/"
    return redirect(f"{back}?sent=1")
