from django.contrib import admin
from .models import SiteSettings, SocialLink, Partner, Brand


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    pass


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("platform", "url", "order")
    list_editable = ("order",)


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "image", "order")
    list_editable = ("order",)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    pass
