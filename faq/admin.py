from django.contrib import admin
from .models import FAQItem


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ("order", "question_en")
    ordering = ("order",)
