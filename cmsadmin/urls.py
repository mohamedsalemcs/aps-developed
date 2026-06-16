"""URLs for the CMS admin at /cms/.

All admin pages are login_required (redirect to /cms/login/). The Store/media
APIs are added in later steps.
"""
from django.urls import path, re_path

from .views import (CMS_PAGES, CmsPageView, InboxView, inbox_action,
                    cms_login, cms_html_redirect, store_get, store_save, media_upload,
                    media_replace, media_restore, profile_password, profile_save,
                    forgot_request, forgot_verify, forgot_check, factory_reset)

urlpatterns = [
    path("login/", cms_login, name="cms-login"),
    path("inbox/", InboxView.as_view(), name="cms-inbox"),
    path("inbox/action/", inbox_action, name="cms-inbox-action"),
    path("api/store/", store_get, name="cms-store-get"),
    path("api/store/save/", store_save, name="cms-store-save"),
    path("api/media/upload/", media_upload, name="cms-media-upload"),
    path("api/media/replace/", media_replace, name="cms-media-replace"),
    path("api/media/restore/", media_restore, name="cms-media-restore"),
    path("api/profile/password/", profile_password, name="cms-profile-password"),
    path("api/profile/save/", profile_save, name="cms-profile-save"),
    path("forgot/request/", forgot_request, name="cms-forgot-request"),
    path("forgot/verify/", forgot_verify, name="cms-forgot-verify"),
    path("forgot/check/", forgot_check, name="cms-forgot-check"),
    path("api/factory-reset/", factory_reset, name="cms-factory-reset"),
]

for name, template in CMS_PAGES.items():
    route = "" if name == "index" else f"{name}/"
    urlpatterns.append(
        path(route, CmsPageView.as_view(template_name=template), name=f"cms-{name}"))

# Catch the designer's relative '<name>.html' admin links (incl. nested like
# divisions/division-edit.html) and 301 to the real route, querystring kept.
urlpatterns.append(
    re_path(r"^(?:[\w./-]+/)?(?P<name>[a-z0-9-]+)\.html$", cms_html_redirect, name="cms-html-redirect"))
