from django.contrib import admin
from .models import Division, DivisionProject


class DivisionProjectInline(admin.TabularInline):
    model = DivisionProject
    extra = 0


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("name_en", "slug", "status", "order")
    inlines = [DivisionProjectInline]


@admin.register(DivisionProject)
class DivisionProjectAdmin(admin.ModelAdmin):
    list_display = ("title_en", "division", "order")
    list_filter = ("division",)
