"""Single source of truth for the CMS theme presets + font-size scale.

A "theme" is a coordinated palette (not individual colours): the client picks
one in /cms/brand/ and it drives BOTH the public website (via
context_processors._brand_css) and the CMS panel chrome (via admin.js +
admin.css). Each preset carries the full set of public-site tokens — including
`surface`/`border`/`footer_text` — so the dark presets actually render dark
(cards + borders flip, not just the accent colour).

Keep this file as the ONLY place palettes live; the brand page renders its
swatches from THEMES and the save path validates against it.
"""

# Public-site font-size multiplier per scale key (applied to the --fs-* tokens).
FONT_SCALES = {
    "sm": 0.92,
    "md": 1.0,
    "lg": 1.12,
    "xl": 1.25,
}
DEFAULT_FONT_SCALE = "md"

# mode: "light" | "dark"  (drives the CMS panel light/dark chrome)
# Every palette defines the same keys so the renderers can stay dumb.
THEMES = {
    # ---------------------------------------------------------------- light
    "aps": {
        "label_en": "APS Blue", "label_ar": "أزرق APS", "mode": "light",
        "primary": "#558BAD", "accent": "#1A6DA2", "hover": "#477694",
        "text": "#0B1220", "muted": "#475569", "bg": "#F7FAFC",
        "footer": "#263F4E", "surface": "#FFFFFF", "border": "#E2E8F0",
        "footer_text": "#CBD5E1",
    },
    "emerald": {
        "label_en": "Emerald", "label_ar": "زمردي", "mode": "light",
        "primary": "#2E9E6B", "accent": "#1F8A5B", "hover": "#277F56",
        "text": "#0B1A14", "muted": "#4B5D54", "bg": "#F4FAF7",
        "footer": "#143027", "surface": "#FFFFFF", "border": "#DCEAE3",
        "footer_text": "#C9E2D5",
    },
    "sand": {
        "label_en": "Desert Sand", "label_ar": "رملي", "mode": "light",
        "primary": "#C2883B", "accent": "#A66A1F", "hover": "#A8772F",
        "text": "#211A10", "muted": "#5C5345", "bg": "#FBF8F2",
        "footer": "#3A2E1C", "surface": "#FFFFFF", "border": "#ECE4D6",
        "footer_text": "#E6DAC4",
    },
    # ----------------------------------------------------------------- dark
    "midnight": {
        "label_en": "Midnight", "label_ar": "أزرق ليلي", "mode": "dark",
        "primary": "#4F9BD0", "accent": "#5AA9DE", "hover": "#6FB4E4",
        "text": "#E6EDF5", "muted": "#9FB2C7", "bg": "#0E1726",
        "footer": "#060B14", "surface": "#16243A", "border": "#25364F",
        "footer_text": "#9FB2C7",
    },
    "carbon": {
        "label_en": "Carbon", "label_ar": "كربوني", "mode": "dark",
        "primary": "#6CA8C9", "accent": "#7DB6D6", "hover": "#8AC0DC",
        "text": "#E8ECF1", "muted": "#A2AEBC", "bg": "#121417",
        "footer": "#0A0C0F", "surface": "#1B1F25", "border": "#2C333C",
        "footer_text": "#A2AEBC",
    },
    "forest": {
        "label_en": "Deep Forest", "label_ar": "أخضر داكن", "mode": "dark",
        "primary": "#46B587", "accent": "#54C295", "hover": "#63CBA1",
        "text": "#E4F1EA", "muted": "#9DB7AC", "bg": "#0D1A14",
        "footer": "#06120D", "surface": "#142620", "border": "#213A30",
        "footer_text": "#9DB7AC",
    },
}

DEFAULT_THEME = "aps"


# Injected into the public <head> (after main.css) ONLY when the active site
# theme is dark. It is a purely ADDITIVE layer: the designer's main.css is never
# edited, so the default/light themes render exactly as before. It re-points the
# many hardcoded light literals (white card/section surfaces, light gradients,
# grey text, light borders) at the theme tokens so a dark palette reads right.
# Sections (full-width) -> --color-background; cards (elevated) -> --color-surface.
DARK_OVERRIDE_CSS = """
/* full-width sections that hardcode a white / light-gradient background */
.partners,.who,.dabout,.systems,.solutions,.lfoundation,
.hero,.contact,.lifecycle{background:var(--color-background)!important;}
/* elevated cards / panels that hardcode white */
.site-header,.nav-dropdown,.lang-switch,.nav-toggle,.division-card,.vcard,
.project-card,.lcard,.azproject-card,.faq-item,.cform,.cinfo-card,.cinfo-mini,
.cmap__card,.contact-card{background:var(--color-surface)!important;}
/* light tint chips inside cards -> slightly lifted from the surface */
.vcard__icon,.faq__head-icon,.faq-item__num,.faq-item__chevron,
.cmap__card-icon,.dabout-pill__icon{
  background:color-mix(in srgb,var(--color-surface) 78%,#000)!important;}
/* form fields + tinted card headers */
.cfield input,.cfield textarea{
  background:var(--color-surface)!important;color:var(--color-text-primary)!important;}
.cinfo-card__header,.coffice{
  background:color-mix(in srgb,var(--color-surface) 88%,#000)!important;}
/* hardcoded grey TEXT -> theme text tokens */
.system-card__label,.coffice__name,.faq__head-title,.cmap__title,
.azproject-card__name,.azspec__value,.milestone__title,.cinfo-mini__value,
.faq-item__text{color:var(--color-text-primary)!important;}
.milestone__desc,.azspec__label,.cmap__card-sub,.faq-item__a,.supplier__desc,
.cform__eyebrow,.cinfo-card__header{color:var(--color-text-secondary)!important;}
/* hardcoded light borders -> theme border */
.faq-item,.cform,.cinfo-card,.cmap__card,.system-card,.cmap__frame,
.lcard__footer,.solution,.cinfo-card__header,.cmap__card-lines{
  border-color:var(--color-border)!important;}
"""


def get_theme(key):
    """Return the palette dict for `key`, falling back to the default preset."""
    return THEMES.get(key) or THEMES[DEFAULT_THEME]


def get_font_scale(key):
    """Return the numeric multiplier for a font-scale key (default 1.0)."""
    return FONT_SCALES.get(key, FONT_SCALES[DEFAULT_FONT_SCALE])
