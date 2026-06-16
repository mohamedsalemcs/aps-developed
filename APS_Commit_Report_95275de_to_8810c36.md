# APS — Detailed Change Report: `95275de` → `8810c36`

Repo: **https://github.com/mohamed21othman2003-lang/APS_NOB**

| Commit | SHA | Meaning |
|---|---|---|
| **Base (before)** | `de3d27b4901f1717e1ef31d13d5553c4dcf95275` (`95275de`) | *“Remove duplicate page title…”* — last commit **before** any client‑CSV content work (pre‑Excel baseline). |
| **Target (after)** | `8810c36b92647c18210bd7bf7c47210cb6c13110` (`8810c36`) | *“Apply all client CSV content + Careers feature + FAQ categories (final delivery)”* — the big delivery commit. |

**Diff size:** `git diff 95275de 8810c36` → **67 files changed, +5,988 / −2,548**.

> ⚠️ **Read first:** the *actual bilingual text content* the client asked for is **NOT** in the code files — it lives in the **MariaDB database** (PageSection / Division / DivisionCard / FAQItem rows), which is **not in git**. This commit ships the **structure** (new sections, fields, features, templates, CMS editors, CSS) plus a **content snapshot baked into `cmsadmin/factory_defaults.json`** (used by `loadfactory` and the CMS “Restore defaults”). To reproduce the delivered content on a clone: `migrate` → `loadfactory`.

---

## 1. Context — what this commit set out to do
Apply the client’s Excel/CSV content across the whole bilingual (EN/AR) site **and** build the structure the content needed:
- **Home**: 5 new sections — stats, “What sets APS apart”, projects, industries, careers teaser (+ hero 2nd button).
- **About**: new HSE & Leadership sections; populated Foundation (Vision/Mission/Values) + Business Principles cards.
- **5 Divisions** (SPS, Beta, Envirosystems, AGS, AZOLIS): updated about/systems copy; new card sections (Complete Solutions, Quality Commitment, Why‑us, Industries‑We‑Power) + Global‑Partners intro; AZOLIS projects expanded with full specs.
- **Careers** (new feature): `/careers/` page + per‑job detail pages `/careers/<slug>/` + an **application form with CV upload** that lands in the CMS Inbox.
- **FAQ**: grouped into 4 categories (new `category` field).
- Everything **bilingual** (EN + AR same meaning) and **CMS‑editable**, with `factory_defaults.json` rebaselined so “Restore defaults” returns this delivered state.

---

## 2. Changes grouped by area

### A. Backend — routing, views, models, migrations
| File | Δ | What changed |
|---|---|---|
| `aps_backend/urls.py` | +18 | Registered the Careers page route, per‑job detail routes `careers/<slug>/` (EN+AR), `careers/apply/` endpoint, and MEDIA serving (for CV uploads). |
| `aps_backend/views.py` | +50 | Added `JobDetailView` (resolves a job by slug from the careers `jobs` section); `FAQView` now groups items by category. |
| `core/models.py` | +1 | `Brand.logo_footer` field. |
| `core/migrations/0005_brand_logo_footer.py` | **new** | Adds `logo_footer` to Brand. |
| `faq/models.py` | +2 | `FAQItem.category_en` / `category_ar` fields. |
| `faq/migrations/0002_faqitem_category_*` | **new** | Adds the FAQ category columns. |
| `core/context_processors.py` | +40 | Brand header/footer logo URL helpers (single‑image logos + defaults). |
| `cmsadmin/store_api.py` | +34 | `build_store`/`apply_store` round‑trip: FAQ `category`, brand `logoFooter`, division `extra_titles` + per‑section `cards`. |
| `cmsadmin/views.py` | +20 | `CMS_PAGES`/labels add `careers-edit`; Inbox view parses “Job Application” messages for nicer rendering. |
| `submissions/views.py` | +87 | `careers_apply` — validates the application, saves the CV to `MEDIA/cvs`, records it as a ContactSubmission (shows in Inbox). |
| `requirements.txt` | **new (+26)** | Pinned dependency list (Django 5.2, mysqlclient, Pillow, selenium, …). |
| `cmsadmin/admin.py`, `*/views.py`, `*/tests.py` (core/faq/pages/divisions/submissions/cmsadmin) | −3 each | Removed empty Django boilerplate stub files (unused). |

### B. CMS admin (editor UI)
| File | Δ | What changed |
|---|---|---|
| `static/cms/js/admin.js` | +117 | New section SCHEMAS (home stats/whyaps/projects/industries/careers; about HSE/leadership; careers hero/environment/jobs) + repeater templates (`stat`, `industry`, `point`, `member`, `job`) + division‑editor card sections + sidebar icons. |
| `templates/cms/division-edit.html` | +169 | Per‑division new card sections (integrated/quality/why/industries) + Global‑Partners intro + “footer line”/no‑icon support. |
| `templates/cms/careers-edit.html` | **new (+73)** | The Careers page CMS editor. |
| `templates/cms/inbox.html` | +23 | Job applications render with **Download CV** + **LinkedIn** buttons and a clean cover‑message box. |
| `templates/cms/{pages,login,settings,about-edit,contact-edit,brand,divisions,faq,media,page-edit,index,partners,profile}.html` | small | Careers sidebar link / pages‑list row; login uses the real brand logo; minor wiring. |

### C. Public templates (EN + AR) — content + new sections
| File | Δ | What changed |
|---|---|---|
| `templates/{en,ar}/index.html` | ~+110 each | Home: 5 new sections + hero/about/divisions/partners/contact content; Careers nav link. |
| `templates/{en,ar}/about.html` | +88 each | HSE + Leadership sections; Foundation/Principles card grids; updated banner/who copy. |
| `templates/{en,ar}/sps.html` | +108 each | SPS: name/about/systems copy + Complete Integrated Solutions + Quality Commitment + Global‑Partners intro. |
| `templates/{en,ar}/beta-machinery.html` | +123 each | Beta: about + Complete Machinery Solutions + Why‑Beta + Industries‑We‑Power. |
| `templates/{en,ar}/envirosystems.html` | +121 each | Enviro: fixed copy + solutions + Complete Env Solutions + Why + Industries. |
| `templates/{en,ar}/advanced-green-solutions.html` | +69 each | AGS: corrected agronomy copy + Vision/Mission. |
| `templates/{en,ar}/azolis-middle-east.html` | +86 each | AZOLIS: solar copy + Industries section; projects/specs. |
| `templates/{en,ar}/faq.html` | ~+62 each | FAQ grouped by category + new heading/lead. |
| `templates/{en,ar}/contact.html` | +65 each | Careers nav link + content tweaks. |
| `templates/{en,ar}/careers.html` | **new (+166 each)** | Careers page (hero + work environment + jobs). |
| `templates/{en,ar}/job-detail.html` | **new (+141 each)** | Single‑job page + application form. |

### D. Styling & assets
| File | Δ | What changed |
|---|---|---|
| `static/css/main.css` | +150 | Styles for all new sections (stats, why‑grid, industries cards, careers, job cards, quality/vcard grids, integrated lists, FAQ groups, etc.). |
| `static/cms/css/admin.css` | +5 | Minor admin tweaks. |
| `static/assets/images/brand/aps-logo.png` | **new (114 KB)** | Header logo image. |
| `static/assets/images/brand/aps-logo.svg` | updated | Full logo SVG. |

### E. Delivered content snapshot
| File | Δ | What changed |
|---|---|---|
| `cmsadmin/factory_defaults.json` | **+5,313 / heavy** | Rebaselined to the full delivered content (all pages, divisions, FAQ, partners, settings, brand) — this is what `loadfactory` and CMS “Restore defaults” use. |

### F. Tests
| File | Δ | What changed |
|---|---|---|
| `ops/e2e/run_e2e.py` | +14 | Updated content‑count assertions (e.g. Enviro solutions 4→8, AZOLIS projects 6→14) + route list. |

---

## 3. Migrations introduced in this commit
1. `core/0005_brand_logo_footer` — `Brand.logo_footer`.
2. `faq/0002_faqitem_category_ar_faqitem_category_en` — FAQ `category_en` / `category_ar`.

(A later commit, not part of this pair, added `core/0006` for the Arabic logo.)

---

## 4. How to inspect / reproduce locally
```bash
# see the full patch
git diff 95275de 8810c36
# or just one file, e.g.:
git diff 95275de 8810c36 -- templates/en/index.html
# get the delivered content into a DB after migrate:
python manage.py migrate && python manage.py loadfactory
```

---

## 5. Notes / gotchas the engineer should know
- **Content lives in the DB**, not in templates. Templates render `pg.*` / `division.*` / `cards.*` from MariaDB. Editing copy = CMS (or DB), not code. The committed `factory_defaults.json` is the snapshot.
- **Bilingual rule:** every EN field has a matching AR field (`{en, ar}`). Keep both in sync.
- **Do not change the `aps_admin` password** (client owns it). E2E uses `e2e_admin`.
- **MariaDB** is a portable process — must be running (`(2006, server has gone away)` ⇒ it’s down).
- **Commit messages:** no `Co-Authored-By` trailer (client preference).
- After CMS schema changes, hard‑refresh the admin (Ctrl+Shift+R) before saving to avoid a stale‑tab overwrite.

*Report generated from `git diff --stat 95275de 8810c36` + working‑session context. For full line‑level detail, run the `git diff` commands above.*
