from django.db import models

STATUS_CHOICES = [("published", "Published"), ("draft", "Draft")]


class Division(models.Model):
    """Mirrors store.js `divisions.<id>` — name, slug, status + the section
    headings his division schema edits (banner/about/systems) and the contact
    block. Long-form middle-section card grids stay in the template for now
    (Phase 4 / pending designer decision on card-grid editability).
    """
    slug = models.SlugField(unique=True)            # e.g. sps, beta, enviro, ags, azolis
    name_en = models.CharField(max_length=200)
    name_ar = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="published")
    order = models.PositiveIntegerField(default=0)

    banner_subtitle_en = models.CharField(max_length=200, blank=True, default="")
    banner_subtitle_ar = models.CharField(max_length=200, blank=True, default="")
    about_title_en = models.CharField(max_length=200, blank=True, default="")
    about_title_ar = models.CharField(max_length=200, blank=True, default="")
    about_body_en = models.TextField(blank=True, default="")
    about_body_ar = models.TextField(blank=True, default="")
    systems_title_en = models.CharField(max_length=200, blank=True, default="")
    systems_title_ar = models.CharField(max_length=200, blank=True, default="")
    systems_subtitle_en = models.CharField(max_length=300, blank=True, default="")
    systems_subtitle_ar = models.CharField(max_length=300, blank=True, default="")

    contact_phone = models.CharField(max_length=60, blank=True, default="")
    contact_website = models.CharField(max_length=200, blank=True, default="")
    contact_email = models.CharField(max_length=200, blank=True, default="")

    # Holds the bits of his admin's division tree that the flat fields above
    # don't capture: the "Our Projects" section title, section order, and
    # per-section hidden flags. Keeps the store round-trip lossless.
    cms_extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name_en


class DivisionProject(models.Model):
    """Mirrors store.js division `projects.items[]` ({img, title}) and also
    carries the AZOLIS spec fields his azolis cards render (location, typology,
    installed power, contract). Spec fields stay blank for simple SPS cards.
    """
    division = models.ForeignKey(Division, related_name="projects", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    image = models.CharField(max_length=300,
                             help_text="Static-relative path, e.g. assets/images/divisions/sps/projects/p1.jpg")
    title_en = models.CharField(max_length=200)
    title_ar = models.CharField(max_length=200, blank=True, default="")

    # AZOLIS spec card fields (bilingual values; labels live in the template)
    location_en = models.CharField(max_length=120, blank=True, default="")
    location_ar = models.CharField(max_length=120, blank=True, default="")
    typology_en = models.CharField(max_length=120, blank=True, default="")
    typology_ar = models.CharField(max_length=120, blank=True, default="")
    installed_power_en = models.CharField(max_length=120, blank=True, default="")
    installed_power_ar = models.CharField(max_length=120, blank=True, default="")
    contract_en = models.CharField(max_length=120, blank=True, default="")
    contract_ar = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.division.slug}: {self.title_en}"


class DivisionCard(models.Model):
    """Generic card for a division's middle-section grids (systems, categories,
    products, pills, foundation, suppliers, solutions, lifecycle). `extra` holds
    the shape-specific oddballs: supplier badge, vcard rule width, lifecycle
    label/footer/milestones. 0-based `order` (matches apply_store)."""
    division = models.ForeignKey(Division, related_name="cards", on_delete=models.CASCADE)
    section_key = models.CharField(max_length=40)  # systems|categories|products|pills|foundation|suppliers|solutions|lifecycle
    order = models.PositiveIntegerField(default=0)
    icon = models.CharField(max_length=300, blank=True, default="",
                            help_text="Static-relative path, e.g. assets/images/icons/sys/sps-1.svg")
    title_en = models.CharField(max_length=300, blank=True, default="")
    title_ar = models.CharField(max_length=300, blank=True, default="")
    body_en = models.TextField(blank=True, default="")
    body_ar = models.TextField(blank=True, default="")
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["section_key", "order", "id"]

    def __str__(self):
        return f"{self.division.slug}.{self.section_key}[{self.order}]: {self.title_en}"
