from django.db import models


class SiteSettings(models.Model):
    """Singleton — global site content (footer/contact/brand text).

    Mirrors store.js `settings`: bilingual {en,ar} for text, plain for
    phone/email. Use SiteSettings.load() to fetch the single row.
    """
    site_name_en = models.CharField(max_length=200, default="")
    site_name_ar = models.CharField(max_length=200, default="")
    tagline_en = models.CharField(max_length=300, default="")
    tagline_ar = models.CharField(max_length=300, default="")
    phone = models.CharField(max_length=60, default="")
    email = models.EmailField(default="")
    website = models.CharField(max_length=200, default="", blank=True)
    address_en = models.CharField(max_length=300, default="")
    address_ar = models.CharField(max_length=300, default="")
    maintenance_mode = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SocialLink(models.Model):
    """Mirrors store.js settings.social[] — {name, url, icon}."""
    platform = models.CharField(max_length=80)
    url = models.URLField(blank=True, default="")
    icon = models.CharField(max_length=120, default="", blank=True,
                            help_text="Static path under assets/images/icons/, e.g. linkedin.svg")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.platform


class Partner(models.Model):
    """Mirrors store.js partners.items[] — {name, img}.

    `image` holds the static-relative path (e.g. assets/images/clinets/audica 1.png)
    so the marquee renders byte-identically via {% static partner.image %}.
    Phase 4 (admin uploads) can migrate this to an upload field.
    """
    name = models.CharField(max_length=120)
    image = models.CharField(max_length=300,
                             help_text="Static-relative path, e.g. assets/images/clinets/audica 1.png")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


class EditLog(models.Model):
    """Lightweight real activity log — one row per content Save — so the
    dashboard 'Recent edits' table shows real history instead of demo rows."""
    when = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=150, blank=True, default="")
    label_en = models.CharField(max_length=120, default="")
    label_ar = models.CharField(max_length=120, default="")

    class Meta:
        ordering = ["-when"]

    def __str__(self):
        return f"{self.when:%Y-%m-%d %H:%M} {self.label_en} ({self.user})"


class PasswordResetCode(models.Model):
    """One-time numeric code emailed to the admin for self-service password
    reset from the login page (forgot-password). Short-lived; single-use."""
    username = models.CharField(max_length=150)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def is_valid(self):
        from django.utils import timezone
        from datetime import timedelta
        return (not self.used) and (timezone.now() - self.created_at <= timedelta(minutes=15))


class Brand(models.Model):
    """Singleton — mirrors store.js brand (colors, fonts, logo)."""
    color_primary = models.CharField(max_length=9, default="#558BAD")
    color_accent = models.CharField(max_length=9, default="#1A6DA2")
    color_hover = models.CharField(max_length=9, default="#477694")
    color_text = models.CharField(max_length=9, default="#0B1220")
    color_muted = models.CharField(max_length=9, default="#475569")
    color_bg = models.CharField(max_length=9, default="#F7FAFC")
    color_footer = models.CharField(max_length=9, default="#263F4E")
    logo = models.CharField(max_length=300, blank=True, default="")
    logo_footer = models.CharField(max_length=300, blank=True, default="")
    # Browser-tab favicon (separate from header/footer logos). Stored like the
    # logos: a CMS upload data-URL, an "assets/..."/relative path, or "" -> the
    # bundled square APS mark default (see context_processors._brand_favicon_url).
    favicon = models.CharField(max_length=300, blank=True, default="")
    arabic_font = models.CharField(max_length=80, default="Cairo")
    english_font = models.CharField(max_length=80, default="Inter")
    # Coordinated theme preset key (see core.themes.THEMES) + global font-size
    # scale key (see core.themes.FONT_SCALES). These drive the public site AND
    # the CMS panel chrome. The legacy color_* fields above stay as the source
    # of truth only for the "custom" theme; a known preset overrides them.
    theme = models.CharField(max_length=40, default="aps")
    font_scale = models.CharField(max_length=8, default="md")
    # The CMS panel's own theme (independent of the public-site `theme`), so the
    # admin can run a dark dashboard while the public site stays light.
    cms_theme = models.CharField(max_length=40, default="aps")

    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brand"

    def __str__(self):
        return "Brand"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
