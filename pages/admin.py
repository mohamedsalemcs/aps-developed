from django.contrib import admin
from .models import Page, PageSection


class PageSectionInline(admin.TabularInline):
    model = PageSection
    extra = 0


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("slug", "title_en", "status")
    inlines = [PageSectionInline]


@admin.register(PageSection)
class PageSectionAdmin(admin.ModelAdmin):
    list_display = ("page", "key", "order", "hidden")
    list_filter = ("page",)
