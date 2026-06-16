# -*- coding: utf-8 -*-
"""Apply the client's APS Website Content Development (Excel) — CONTENT ONLY,
into EXISTING Home + About slots. Per the client's scope:

  * Source = the "NOB's Development" column of the Excel (English).
  * Arabic = translated here (the Excel had no Arabic column).
  * ONLY fields that already exist in the current site are updated. Nothing new
    is added. Content for removed sections (stats / why-APS / projects /
    industries / careers / HSE / leadership / division card-sections / FAQ
    categories) is NOT applied — see the "SKIPPED / NOT APPLIED" note printed
    at the end (do those in the CMS if wanted).
  * Idempotent: writes specific keys; safe to re-run. Run AFTER `seed`.

Usage:  python manage.py apply_client_content
"""
from django.core.management.base import BaseCommand
from pages.models import Page, PageSection
from divisions.models import Division


def bi(en, ar):
    return {"en": en, "ar": ar}


# page -> section key -> {field: {en, ar}}  (only existing, template-rendered keys)
UPDATES = {
    "home": {
        "hero": {
            "title": bi("Powering Industry with Premium Supplies & Expert Installation.",
                        "نُمكّن الصناعة بتوريدات متميّزة وتركيب احترافي."),
            "lead": bi("APS is your strategic partner for industrial trading, premium supply, and expert electro-mechanical solutions.",
                       "‏APS شريكك الاستراتيجي في التجارة الصناعية والتوريد المتميّز والحلول الكهروميكانيكية الاحترافية."),
        },
        "about": {
            "title": bi("APS Group at a Glance", "لمحة عن مجموعة APS"),
            "body": bi("Arabian Projects & Supplies (APS) is a diversified industrial group delivering trading, premium supply, and electro-mechanical installation services across Saudi Arabia through specialized companies and strong global partnerships.",
                       "العربية للمشاريع والتوريدات (APS) مجموعة صناعية متنوّعة تقدّم خدمات التجارة والتوريد المتميّز والتركيب الكهروميكانيكي في كل أنحاء المملكة العربية السعودية عبر شركات متخصّصة وشراكات عالمية قوية."),
        },
        "divisions": {
            "title": bi("Specialized Divisions, All Under One Roof.", "أقسام متخصّصة، تحت سقف واحد."),
            "subtitle": bi("Explore APS companies serving the security systems, industrial machinery, environmental solutions, and technology sectors.",
                           "استكشف شركات APS في قطاعات أنظمة الأمن والآلات الصناعية والحلول البيئية والتقنية."),
        },
        "partners": {
            "title": bi("Our Partners", "شركاؤنا"),
            "subtitle": bi("APS partners with leading global manufacturers and technology providers to deliver reliable industrial solutions across Saudi Arabia.",
                           "تتشارك APS مع كبرى الشركات المصنّعة ومزوّدي التقنيات عالميًا لتقديم حلول صناعية موثوقة في كل أنحاء المملكة العربية السعودية."),
        },
        "contact": {
            "title": bi("Get in Touch", "تواصل معنا"),
            "subtitle": bi("Our team responds with fast, reliable support tailored to your industrial and electro-mechanical needs.",
                           "يردّ فريقنا بدعم سريع وموثوق مصمّم وفق احتياجاتك الصناعية والكهروميكانيكية."),
        },
    },
    "about": {
        "banner": {
            "title": bi("Get to Know APS", "تعرّف على APS"),
        },
        "who": {
            "title": bi("Built to Deliver", "بُنينا للإنجاز"),
            "body": bi("APS is a diversified Saudi group delivering integrated electro-mechanical, industrial, and environmental solutions across the Kingdom. Through specialized divisions and global partnerships, we deliver reliable systems for infrastructure, industry, and secure environments, covering the full project lifecycle from design to after-sales support, with a focus on quality, safety, and performance.",
                       "‏APS مجموعة سعودية متنوّعة تقدّم حلولاً كهروميكانيكية وصناعية وبيئية متكاملة في كل أنحاء المملكة. من خلال أقسام متخصّصة وشراكات عالمية، نقدّم أنظمة موثوقة للبنية التحتية والصناعة والبيئات الآمنة، تغطّي دورة المشروع الكاملة من التصميم إلى دعم ما بعد البيع، مع التركيز على الجودة والسلامة والأداء."),
        },
        "foundation": {
            "title": bi("Our Guiding Principles", "مبادئنا التوجيهية"),
        },
        "principles": {
            # the about template renders principles.subtitle (not body) — write there so it shows
            "subtitle": bi("A governance-driven framework guiding how APS operates, delivers, and grows.",
                           "إطار قائم على الحوكمة يوجّه كيف تعمل APS وتُنجز وتنمو."),
        },
    },
}

# hero quick-feature chip texts (icons kept as-is); from Homepage row 5.
HERO_FEATURES = [
    bi("Built on Trust", "مبنيّ على الثقة"),
    bi("Global Partners", "شركاء عالميون"),
    bi("Across the Kingdom", "في كل أنحاء المملكة"),
]


def _card(icon, t_en, t_ar, b_en, b_ar):
    return {"icon": "assets/images/icons/" + icon, "rule": "inline-size: 58px",
            "title": bi(t_en, t_ar), "text": bi(b_en, b_ar)}


# About → Foundation (Vision/Mission/Values) + Principles (6) cards. These
# sections render `cards` but the seed never populated them (so they showed
# empty). Vision + the last 2 principles = original text (Excel marked "no
# change"); the rest = the client's "NOB's Development". Arabic translated here.
ABOUT_CARDS = {
    "foundation": [
        _card("ic-vision.svg", "Vision", "الرؤية",
              "To be a leading and trusted provider of integrated electro-mechanical and industrial solutions in Saudi Arabia, supporting national infrastructure and sustainable development.",
              "أن نكون مزوّدًا رائدًا وموثوقًا لحلول كهروميكانيكية وصناعية متكاملة في المملكة العربية السعودية، داعمين للبنية التحتية الوطنية والتنمية المستدامة."),
        _card("ic-mission.svg", "Mission", "الرسالة",
              "To deliver high-performance, reliable systems through technical expertise, global partnerships, and integrity, creating lasting value for our clients.",
              "أن نقدّم أنظمة موثوقة وعالية الأداء عبر الخبرة الفنية والشراكات العالمية والنزاهة، لنخلق قيمة دائمة لعملائنا."),
        _card("ic-values.svg", "Core Values", "قيمنا الأساسية",
              "Guided by integrity, professionalism, and accountability, we prioritize safety, quality, and long-term partnerships in every project we undertake.",
              "نسترشد بالنزاهة والاحترافية والمساءلة، ونعطي الأولوية للسلامة والجودة والشراكات طويلة الأمد في كل مشروع نتولّاه."),
    ],
    "principles": [
        _card("ic-quality.svg", "Quality & Excellence", "الجودة والتميّز",
              "Delivering reliable products and superior service across every project and engagement.",
              "تقديم منتجات موثوقة وخدمة متميّزة في كل مشروع وتعامل."),
        _card("ic-handshake2.svg", "Customer Commitment", "الالتزام تجاه العميل",
              "Building long-term partnerships founded on trust, transparency, and consistent performance.",
              "بناء شراكات طويلة الأمد قائمة على الثقة والشفافية والأداء المتّسق."),
        _card("ic-dashboard.svg", "Professional Management", "الإدارة الاحترافية",
              "Structured governance supporting sustainable growth and disciplined execution.",
              "حوكمة منظَّمة تدعم النمو المستدام والتنفيذ المنضبط."),
        _card("ic-trending.svg", "Market Leadership", "الريادة في السوق",
              "Advancing through continuous improvement and innovation to maintain a competitive position across Saudi sectors.",
              "التقدّم عبر التحسين المستمر والابتكار للحفاظ على موقع تنافسي في القطاعات السعودية."),
        _card("ic-layers.svg", "Diversified Portfolio", "محفظة متنوّعة",
              "Balanced operations across trading, professional services, and contracting divisions.",
              "عمليات متوازنة عبر أقسام التجارة والخدمات المهنية والمقاولات."),
        _card("ic-hierarchy.svg", "Structured Organization", "تنظيم مُحكم",
              "Clear reporting lines, defined accountability, and centralized corporate support functions.",
              "خطوط مسؤولية واضحة، ومساءلة محدّدة، ووظائف دعم مؤسسي مركزية."),
    ],
}


# Division "About / at a Glance" content (the cleanly-mappable division field).
# Each division's about section = title + body (body renders with |linebreaks).
# NOT applied: systems/categories items, projects, the removed card sections
# (Complete Solutions / Why / Industries / Quality / Global Partners) — those
# aren't in the sheet as clean per-slot content.
DIVISIONS_ABOUT = {
    "sps": {  # SPS sheet gives no "at a Glance" heading -> keep title, update body
        "about_body": bi(
            "SPS was established in 2001 as a provider of integrated security, safety, and control systems across the Kingdom.\n\nServing industrial, governmental, residential, healthcare, and educational sectors, SPS delivers advanced solutions tailored to diverse operational needs.\n\nOperating nationwide, SPS supports projects across the Kingdom with a strong reputation for quality and reliability. Each project is delivered with precision and professionalism to ensure long-term performance.\n\nContinuous investment in talent and technology enables SPS to remain a forward-looking, solutions-driven partner.",
            "تأسست SPS عام 2001 كمزوّد لأنظمة الأمن والسلامة والتحكم المتكاملة في كل أنحاء المملكة.\n\nوخدمةً للقطاعات الصناعية والحكومية والسكنية والصحية والتعليمية، تقدّم SPS حلولاً متقدّمة مصمّمة وفق الاحتياجات التشغيلية المتنوّعة.\n\nوبتغطية على مستوى المملكة، تدعم SPS المشاريع في كل أنحاء البلاد بسمعة قوية في الجودة والموثوقية، ويُنفَّذ كل مشروع بدقة واحترافية لضمان أداء طويل الأمد.\n\nوالاستثمار المستمر في الكفاءات والتقنية يمكّن SPS من أن تظل شريكًا استشرافيًا قائمًا على الحلول."),
    },
    "beta": {
        "about_title": bi("Beta Machinery at a Glance", "لمحة عن بيتا للآلات"),
        "about_body": bi(
            "Beta Machinery, established in 1996, is a specialized division of APS focused on delivering advanced industrial machinery solutions.\n\nWe support industrial operations through complete solutions, from equipment supply and installation to commissioning, tailored to meet specific operational requirements and ensure long-term performance.\n\nOur engineering team delivers full production line installations, supported by training and ongoing technical expertise.",
            "بيتا للآلات، التي تأسست عام 1996، قسم متخصّص من APS يركّز على تقديم حلول آلات صناعية متقدّمة.\n\nندعم العمليات الصناعية عبر حلول متكاملة، من توريد المعدّات وتركيبها إلى التشغيل، مصمّمة لتلبية المتطلبات التشغيلية المحدّدة وضمان أداء طويل الأمد.\n\nويقدّم فريقنا الهندسي تركيب خطوط إنتاج كاملة، مدعومًا بالتدريب والخبرة الفنية المستمرة."),
    },
    "enviro": {
        "about_title": bi("Envirosystems at a Glance", "لمحة عن إنفيروسيستمز"),
        "about_body": bi(
            "Envirosystems delivers solutions for the water, wastewater, and ventilation sectors across Saudi Arabia.\n\nThrough partnerships with leading international manufacturers, the division provides advanced, cost-effective solutions for municipal and industrial applications.\n\nFrom initial assessment to turnkey implementation, Envirosystems supports projects with strong engineering capabilities, including process design and mechanical and electrical engineering.",
            "تقدّم إنفيروسيستمز حلولاً لقطاعات المياه والصرف الصحي والتهوية في كل أنحاء المملكة العربية السعودية.\n\nومن خلال شراكات مع كبرى الشركات المصنّعة عالميًا، يوفّر القسم حلولاً متقدّمة وفعّالة من حيث التكلفة للتطبيقات البلدية والصناعية.\n\nومن التقييم المبدئي إلى التنفيذ المتكامل التسليم، تدعم إنفيروسيستمز المشاريع بقدرات هندسية قوية تشمل تصميم العمليات والهندسة الميكانيكية والكهربائية."),
    },
    "ags": {
        "about_title": bi("Advanced Green Solutions at a Glance", "لمحة عن الحلول الخضراء المتقدمة"),
        "about_body": bi(
            "Advanced Green Solutions is a Dubai-based company delivering practical, sustainable solutions for agriculture and turfcare.\n\nBuilt on industry expertise, we work closely with clients to address real field challenges, enhancing crop performance, improving plant health, and supporting long-term productivity through tailored solutions, products, and technical guidance.",
            "الحلول الخضراء المتقدمة شركة مقرّها دبي تقدّم حلولاً عملية ومستدامة للزراعة والعناية بالمسطّحات الخضراء.\n\nوانطلاقًا من خبرة في القطاع، نعمل عن قرب مع العملاء لمعالجة تحدّيات الميدان الحقيقية، وتحسين أداء المحاصيل وصحة النبات، ودعم الإنتاجية طويلة الأمد عبر حلول ومنتجات وإرشاد فني مصمّم وفق الاحتياج."),
    },
    "azolis": {
        "about_title": bi("AZOLIS at a Glance", "لمحة عن أزوليس"),
        "about_body": bi(
            "AZOLIS is an independent solar power producer specializing in the development, financing, engineering, construction, and maintenance of solar power plants for the Commercial and Industrial (C&I) segment.\n\nAZOLIS has delivered +200 projects across three continents and operates offices in Paris (France) and Casablanca (Morocco).",
            "أزوليس منتج مستقل للطاقة الشمسية متخصّص في تطوير وتمويل وهندسة وبناء وصيانة محطّات الطاقة الشمسية لقطاع التجاري والصناعي (C&I).\n\nنفّذت أزوليس أكثر من 200 مشروع عبر ثلاث قارات، ولها مكاتب في باريس (فرنسا) والدار البيضاء (المغرب)."),
    },
}


class Command(BaseCommand):
    help = "Apply client Excel content (NOB's Development) into existing Home + About slots (EN + AR)."

    def handle(self, *args, **opts):
        changed, skipped = [], []

        for page_slug, sections in UPDATES.items():
            page = Page.objects.filter(slug=page_slug).first()
            if not page:
                skipped.append(f"page '{page_slug}' not found"); continue
            for key, fields in sections.items():
                sec = PageSection.objects.filter(page=page, key=key).first()
                if not sec:
                    skipped.append(f"{page_slug}/{key} (section missing)"); continue
                data = dict(sec.data or {})
                for field, val in fields.items():
                    old = data.get(field)
                    data[field] = val
                    changed.append(f"{page_slug}.{key}.{field}: {self._short(old)} -> {self._short(val)}")
                # hero quick-feature chip texts (keep each feature's icon)
                if page_slug == "home" and key == "hero" and isinstance(data.get("features"), list):
                    for i, txt in enumerate(HERO_FEATURES):
                        if i < len(data["features"]) and isinstance(data["features"][i], dict):
                            old = data["features"][i].get("text")
                            data["features"][i]["text"] = txt
                            changed.append(f"home.hero.features[{i}].text: {self._short(old)} -> {self._short(txt)}")
                # about Foundation / Principles cards (were empty — never seeded)
                if page_slug == "about" and key in ABOUT_CARDS:
                    data["cards"] = ABOUT_CARDS[key]
                    changed.append(f"about.{key}.cards: populated {len(ABOUT_CARDS[key])} cards (icons + EN/AR)")
                sec.data = data
                sec.save()

        # ---- divisions: About / at a Glance (title + body, EN + AR)
        for slug, fields in DIVISIONS_ABOUT.items():
            div = Division.objects.filter(slug=slug).first()
            if not div:
                skipped.append(f"division '{slug}' not found"); continue
            for field, val in fields.items():
                setattr(div, field + "_en", val["en"])
                setattr(div, field + "_ar", val["ar"])
                changed.append(f"division[{slug}].{field}: EN/AR updated ({self._short(val)})")
            div.save()

        self.stdout.write(self.style.SUCCESS(f"\nApplied {len(changed)} field updates (EN + AR):"))
        for c in changed:
            self.stdout.write("  + " + c)
        self.stdout.write(self.style.WARNING(
            "\nNOT APPLIED (by design — do in the CMS if wanted):\n"
            "  - Home hero second CTA 'Get a Quote' (the 2nd hero button was removed; kept 'Explore Divisions').\n"
            "  - Home: stats / What-Sets-APS-Apart / projects / Industries / careers teaser (sections were removed).\n"
            "  - About: HSE & Leadership sections (were removed in the revert).\n"
            "  - Divisions: About text applied; NOT applied = systems/categories items, projects lists, and the removed card-sections (Complete Solutions / Why / Industries / Quality / Global Partners) — not clean per-slot content in the sheet.\n"
            "  - FAQ sheet (built around removed categories + mashed Q&A + hardcoded banner).\n"
            "  - 'Delete'/'no-change'/'belongs on contact page'/structural-suggestion rows."))

    @staticmethod
    def _short(v):
        if isinstance(v, dict):
            v = v.get("en", "")
        return (str(v)[:45] + "…") if v and len(str(v)) > 45 else repr(v)
