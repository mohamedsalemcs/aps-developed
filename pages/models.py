from django.db import models

STATUS_CHOICES = [("published", "Published"), ("draft", "Draft")]


class Page(models.Model):
    """Mirrors store.js `pages.{home,about,contact}` top-level — title, status,
    plus the SEO tab fields his page-edit.html exposes (pages.<id>.seo.title/desc).
    """
    slug = models.SlugField(unique=True)
    title_en = models.CharField(max_length=200, default="")
    title_ar = models.CharField(max_length=200, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="published")
    seo_title_en = models.CharField(max_length=200, blank=True, default="")
    seo_title_ar = models.CharField(max_length=200, blank=True, default="")
    seo_desc_en = models.TextField(blank=True, default="")
    seo_desc_ar = models.TextField(blank=True, default="")

    def __str__(self):
        return self.slug


class PageSection(models.Model):
    """Mirrors store.js `pages.<id>.sections.<key>` — a bilingual content blob.

    `data` keeps the exact {en:{...}, ar:{...}} shape his admin JS reads/writes,
    so Phase 4 can bind his section engine to this without reshaping.
    """
    page = models.ForeignKey(Page, related_name="sections", on_delete=models.CASCADE)
    key = models.CharField(max_length=60)            # e.g. hero, about, divisions
    order = models.PositiveIntegerField(default=0)
    hidden = models.BooleanField(default=False)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("page", "key")

    def __str__(self):
        return f"{self.page.slug}.{self.key}"
