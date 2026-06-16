# APS Website + CMS — Project Handoff / Chat Summary

> **TL;DR (بالعربي):** موقع APS ثنائي اللغة (عربي/إنجليزي) + لوحة تحكم Django. اتطبّق محتوى العميل (شيتات الاكسيل) واتسلّم، وبعدين اترجّع محلياً لنسخة ما قبل الاكسيل بسبب أخطاء. **الريبو على GitHub لسه فيه نسخة التسليم الكاملة (بالاكسيل).** التفاصيل تحت — الأهم: قسم "Current State" + "How to run".

Repo: **https://github.com/mohamed21othman2003-lang/APS_NOB**

---

## 1. What the project is
- **Bilingual (EN `/` + AR `/ar/`) corporate website** for *Arabian Projects & Supplies (APS)* — a Saudi group with **5 divisions**: SPS (security/safety), Beta Machinery, Envirosystems (water/env), Advanced Green Solutions (agronomy), AZOLIS (solar).
- **Custom Django CMS at `/cms/`** — every section/text/image/translation is editable; has a per-page **“Restore defaults”** safety net.
- **Stack:** Python 3.12 · Django 5.2 · **MariaDB/MySQL** (utf8mb4) · server-rendered templates (no JS framework).
- Project root (Django) = `D:\APS_final\aps_backend`. Full setup steps are in the repo **`README.md`**.

---

## 2. What was done (this engagement)
1. **Applied all client CSV/Excel content** (EN + AR, same meaning) across: Home, About, the 5 divisions, FAQ.
2. **Built new features** from the CSVs:
   - **Careers**: `/careers/` page + per‑job detail pages `/careers/<slug>/` + **application form** (CV upload → CMS Inbox).
   - **FAQ categories** (grouped 16 Qs into 4 categories; added `category` field).
   - **New sections** on Home (stats, why‑APS, projects, industries, careers) and About (HSE, Leadership), and per division (Complete Solutions, Quality, Why, Industries, Global‑Partners intro).
   - **Arabic logo** support (separate AR header/footer logo, CMS‑uploadable) + login‑logo cleanup.
3. **Delivered to client + pushed to GitHub** (the commit `8810c36` “Apply all client CSV content…”, then `add21ce` “Add README + loadfactory”).
4. **Client reported errors → full ROLLBACK** (local) to the pre‑Excel version (`95275de`).

---

## 3. ⚠️ Current State (read this carefully)
| Where | State |
|---|---|
| **GitHub `origin/master`** | `add21ce` = **full Excel/delivered version** (all CSV content + Careers + AR logo). **This is what a clone gets.** |
| **Local `master`** | `95275de` = **pre‑Excel** code (rolled back). Working tree clean. |
| **Local branch `safety/current-2026-06-16`** | `3730ba6` = snapshot of the **Excel/delivered** code (safety copy). |
| **Local MariaDB (`aps_db`)** | Pre‑Excel content rebuilt via `seed`, **+ partial “content‑only” re‑apply in progress** (Home, About, and division fields updated in the DB; not committed/pushed). |

- **Nothing local is pushed** beyond `add21ce`. The rollback and the in‑progress content edits live only on this machine.
- **Backups (Desktop):** `APS_SAFETY_BACKUP_2026-06-16\aps_db_current.sql` = full MariaDB dump of the delivered (Excel) DB. To restore that DB: `mysql ... aps_db < aps_db_current.sql`.

### In‑progress task (was running when handed off)
Re‑applying the client content **content‑only** onto the **pre‑Excel design** — i.e. swap text in **existing** slots only, **without** adding any new page/section/button. Done so far (DB): Home (hero/about/divisions/partners/contact), About (banner/who + foundation & principles cards), division fields (name/about/systems + fixed wrong copy on AGS/Enviro/AZOLIS + AZOLIS contact). **Skipped** (would add structure): Careers, Home new sections, About HSE/Leadership, division new sections, project‑list expansion.

---

## 4. How to run (fresh clone)
From `README.md` (summary):
```bash
git clone https://github.com/mohamed21othman2003-lang/APS_NOB.git
cd APS_NOB
python -m venv venv && venv\Scripts\activate          # Windows
pip install -r requirements.txt
# create MariaDB/MySQL db `aps_db` + user (or set APS_DB_* env vars)
python manage.py migrate
python manage.py loadfactory      # loads the delivered content snapshot
python manage.py createsuperuser  # CMS login at /cms/login/
python manage.py runserver
```
- Public: `http://127.0.0.1:8000/` (AR: `/ar/`) · CMS: `/cms/login/`
- `python manage.py seed` = original baseline content; `loadfactory` = the delivered (factory_defaults.json) content.

---

## 5. Git restore points
- `95275de` — **pre‑Excel** (current local master).
- `8810c36` — Excel content delivery.
- `add21ce` — + README + `loadfactory` (origin/master tip).
- `3730ba6` — safety snapshot of the delivered state (branch `safety/current-2026-06-16`, local only).

Switch to the delivered code: `git checkout safety/current-2026-06-16` (or `git checkout add21ce`). Restore its DB from the Desktop `.sql` dump.

---

## 6. Key rules & gotchas (important)
- **Every EN content change must have a matching AR translation (same meaning).** All content fields are bilingual `{en, ar}`.
- **Never reset/change the `aps_admin` password** — the client owns it. (E2E uses a separate `e2e_admin`.)
- **MariaDB is a portable user process** — after a reboot it must be (re)started; if Django shows `(2006, server has gone away)`, MariaDB isn’t up.
- **CMS stale‑tab gotcha:** PageSection pages rebuild from `order`+`sections` on save; editing with an old browser tab can drop sections — hard‑refresh (Ctrl+Shift+R) the CMS before saving after any schema change.
- **ngrok** tunnel (`brusque-interpolative-selma.ngrok-free.dev`) is **not** auto‑managed — start manually: `ngrok http --domain=brusque-interpolative-selma.ngrok-free.dev 8000`.
- **Commit messages:** do NOT add a `Co-Authored-By` trailer (client wants solo authorship).
- **E2E suite:** `python ops/e2e/run_e2e.py` (Selenium headless Edge) — should be green; the E27 inbox test can show a false fail when the inbox has >10 real messages (pagination artifact, not a bug).

---

## 7. App / endpoint map
- Public (EN root, AR under `/ar/`): `/`, `/about/`, `/sps/`, `/beta-machinery/`, `/envirosystems/`, `/advanced-green-solutions/`, `/azolis-middle-east/`, `/faq/`, `/contact/` (+ `/careers/` only in the delivered version).
- Forms: `POST /contact/submit/` (+ `POST /careers/apply/` in delivered version) → CMS Inbox.
- CMS: `/cms/login/`, `/cms/` dashboard, `/cms/pages/`, `/cms/page-edit/`, `/cms/about-edit/`, `/cms/contact-edit/`, `/cms/divisions/` + `/cms/division-edit/?div=<sps|beta|enviro|ags|azolis>`, `/cms/faq/`, `/cms/partners/`, `/cms/media/`, `/cms/brand/`, `/cms/settings/`, `/cms/inbox/`.

---

## 8. Project structure (apps)
`aps_backend/` (settings/urls/root views) · `core/` (SiteSettings, Brand, context processors, mgmt cmds: `seed`, `loadfactory`) · `pages/` (Page + PageSection) · `divisions/` (Division + DivisionCard + DivisionProject) · `faq/` (FAQItem) · `submissions/` (contact + job apps) · `cmsadmin/` (the `/cms/` admin + store API + `factory_defaults.json`) · `templates/en|ar` (public) · `templates/cms` (admin) · `static/` · `ops/` (run scripts + E2E).

---

*Generated as a handoff summary of the working session. Questions: the README + this file cover setup, state, and the safety backups.*
