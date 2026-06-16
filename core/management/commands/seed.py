# -*- coding: utf-8 -*-
"""Idempotent seed of the REAL approved APS content.

Source of truth = the designer's HTML pages (the real content) cross-checked
against cms/admin/js/store.js (the bilingual blueprint). Running this twice
does not duplicate — every row is keyed by a natural key via update_or_create.
ContactSubmission rows are never touched.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

import json
import pathlib

from core.models import SiteSettings, SocialLink, Partner, Brand
from pages.models import Page, PageSection
from divisions.models import Division, DivisionProject, DivisionCard
from faq.models import FAQItem

CARDS_JSON = pathlib.Path(__file__).resolve().parent / "cards_seed.json"


def bi(en, ar):
    return {"en": en, "ar": ar}


# ----------------------------------------------------------------- partners
# names from store.js partners.items[]; image paths from index.html marquee.
PARTNERS = [
    ("Audica", "assets/images/clinets/audica 1.png"),
    ("CDVI", "assets/images/clinets/cdvi 2.png"),
    ("Samsung", "assets/images/clinets/samsung 1.png"),
    ("Vimpex", "assets/images/clinets/vimpex 2.png"),
    ("Esser", "assets/images/clinets/upscale_image [Upscaled].png"),
    ("CIAS", "assets/images/clinets/تنزيل 1.png"),
]

SOCIAL = [
    ("LinkedIn", "https://linkedin.com/company/aps", "linkedin.svg"),
    ("X (Twitter)", "#", "globe.svg"),
    ("Instagram", "#", "instagram.svg"),
]

# ----------------------------------------------------------------- divisions
# headings/summaries from store.js; ALL set published (incl. AZOLIS — its page
# is complete; the draft flag in store.js is a designer decision pending review).
DIVISIONS = [
    dict(slug="sps", order=1,
         name_en="Saudi Projects & Supplies Co. (SPS)", name_ar="السعودية للمشاريع والتوريدات (SPS)",
         banner_subtitle_en="SPS Division", banner_subtitle_ar="قسم SPS",
         about_title_en="About Saudi Projects & Supplies Co.", about_title_ar="عن العربية للمشاريع والتوريدات",
         about_body_en="Established in 2001 as a security, safety, and control systems integrator across Saudi Arabia.",
         about_body_ar="تأسست عام 2001 كمتكامل لأنظمة الأمن والسلامة والتحكم في كل أنحاء السعودية.",
         systems_title_en="Systems & Solutions", systems_title_ar="الأنظمة والحلول",
         systems_subtitle_en="A comprehensive portfolio of integrated systems for safety and facility management.",
         systems_subtitle_ar="محفظة شاملة من الأنظمة المتكاملة للسلامة وإدارة المنشآت.",
         contact_phone="+966 9200 14 515", contact_website="www.spsc.com.sa", contact_email="sales.sps@aps.com.sa"),
    dict(slug="beta", order=2,
         name_en="Beta Machinery", name_ar="بيتا للآلات",
         banner_subtitle_en="Beta Machinery Division", banner_subtitle_ar="قسم Beta Machinery",
         about_title_en="About Beta Machinery", about_title_ar="عن Beta Machinery",
         about_body_en="Supplies high-tech industrial machinery with installation, commissioning, training, and after-sales support.",
         about_body_ar="توريد آلات صناعية عالية التقنية مع التركيب والتشغيل والتدريب ودعم ما بعد البيع.",
         systems_title_en="Machinery Categories", systems_title_ar="فئات الآلات",
         systems_subtitle_en="A broad range of industrial machinery across sectors.",
         systems_subtitle_ar="نطاق واسع من الآلات الصناعية عبر القطاعات.",
         contact_phone="+966 11 242 8467", contact_website="www.Beta-machinery.net", contact_email="sales@betamachinery.com.sa"),
    dict(slug="enviro", order=3,
         name_en="Envirosystems", name_ar="إنفيروسيستمز",
         banner_subtitle_en="Envirosystems Division", banner_subtitle_ar="قسم Envirosystems",
         about_title_en="About Envirosystems", about_title_ar="عن Envirosystems",
         about_body_en="Security, safety, and control systems integration for industrial, governmental, and commercial facilities.",
         about_body_ar="تكامل أنظمة الأمن والسلامة والتحكم للمنشآت الصناعية والحكومية والتجارية.",
         systems_title_en="Solutions", systems_title_ar="الحلول",
         systems_subtitle_en="Integrated environmental and control solutions.",
         systems_subtitle_ar="حلول بيئية وتحكم متكاملة.",
         contact_phone="+966 12 661 7470", contact_website="www.envirosystems.com.sa", contact_email="info@envirosystems.com.sa"),
    dict(slug="ags", order=4,
         name_en="Advanced Green Solutions", name_ar="الحلول الخضراء المتقدمة",
         banner_subtitle_en="AGS Division", banner_subtitle_ar="قسم AGS",
         about_title_en="About Advanced Green Solutions", about_title_ar="عن Advanced Green Solutions",
         about_body_en="Sustainable and energy-efficient solutions supporting green projects and eco-friendly developments.",
         about_body_ar="حلول مستدامة وموفّرة للطاقة تدعم المشاريع الخضراء والتطويرات الصديقة للبيئة.",
         systems_title_en="Product Range", systems_title_ar="مجموعة المنتجات",
         systems_subtitle_en="Solar, wind, and energy-efficiency products.",
         systems_subtitle_ar="منتجات الطاقة الشمسية والرياح وكفاءة الطاقة.",
         contact_phone="+966 9200 14 515", contact_website="www.ags-ae.com", contact_email="ags@aps.com.sa"),
    dict(slug="azolis", order=5,
         name_en="AZOLIS Middle East", name_ar="أزوليس الشرق الأوسط",
         banner_subtitle_en="AZOLIS Division", banner_subtitle_ar="قسم AZOLIS",
         about_title_en="About AZOLIS Middle East", about_title_ar="عن AZOLIS Middle East",
         about_body_en="Specialized chemical solutions and technical services for water and industrial treatment.",
         about_body_ar="حلول كيميائية متخصصة وخدمات فنية لمعالجة المياه والمعالجة الصناعية.",
         systems_title_en="Lifecycle", systems_title_ar="دورة الحياة",
         systems_subtitle_en="End-to-end chemical treatment lifecycle.",
         systems_subtitle_ar="دورة حياة معالجة كيميائية متكاملة.",
         contact_phone="+966 9200 14 515", contact_website="www.azolis.com", contact_email="sales.azolis@aps.com.sa"),
]

# SPS projects: (img, title_en, title_ar) — titles from en/sps.html + ar/sps.html
SPS_PROJECTS = [
    ("p1.jpg", "Ajdan Waterfront in the Heart of Khobar", "واجهة أجدان البحرية في قلب الخبر"),
    ("p2.jpg", "Ajdan Rise Residential Tower", "برج أجدان رايز السكني"),
    ("p3.jpg", "Administrative Court", "المحكمة الإدارية"),
    ("p4.jpg", "King Saud University (KSU)", "جامعة الملك سعود (KSU)"),
    ("p5.jpg", "King Abdulaziz University (KAAU)", "جامعة الملك عبدالعزيز (KAAU)"),
    ("p6.jpg", "Four Points", "فندق فور بوينتس"),
]

# AZOLIS projects: name + 4 specs, both languages (from en/ar azolis-middle-east.html).
# NOTE: project 1 "installed power" = "PV carport" is a faithful copy of a Figma
# data-entry error (flagged for the designer). &rsquo; normalized to ’.
AZOLIS_PROJECTS = [
    dict(img="p1.jpg", title_en="Royal Mansour M’dieq", title_ar="رويال منصور المضيق",
         location_en="Morocco", location_ar="المغرب",
         typology_en="PV carport", typology_ar="مظلّة وقوف كهروضوئية",
         installed_power_en="PV carport", installed_power_ar="PV carport",
         contract_en="EPC self-production", contract_ar="EPC للإنتاج الذاتي"),
    dict(img="p2.jpg", title_en="Confidential (Industrial)", title_ar="مشروع سرّي (صناعي)",
         location_en="Morocco", location_ar="المغرب",
         typology_en="PV rooftop", typology_ar="PV على الأسطح",
         installed_power_en="6 MWp", installed_power_ar="6 MWp",
         contract_en="PSA", contract_ar="PSA"),
    dict(img="p3.jpg", title_en="Marjane Menara", title_ar="مرجان المنارة",
         location_en="Morocco", location_ar="المغرب",
         typology_en="PV rooftop", typology_ar="PV على الأسطح",
         installed_power_en="665 kWp", installed_power_ar="665 kWp",
         contract_en="EPC self-production", contract_ar="EPC للإنتاج الذاتي"),
    dict(img="p4.jpg", title_en="Total Energies", title_ar="Total Energies",
         location_en="Morocco", location_ar="المغرب",
         typology_en="PV rooftop (multi-site)", typology_ar="PV على الأسطح (مواقع متعددة)",
         installed_power_en="30 x 12 kWp", installed_power_ar="30 x 12 kWp",
         contract_en="EPC self-production", contract_ar="EPC للإنتاج الذاتي"),
    dict(img="p5.jpg", title_en="Vertical Green", title_ar="Vertical Green",
         location_en="Morocco", location_ar="المغرب",
         typology_en="Solar pumping", typology_ar="الضخّ بالطاقة الشمسية",
         installed_power_en="287 kWp", installed_power_ar="287 kWp",
         contract_en="EPC self-production", contract_ar="EPC للإنتاج الذاتي"),
    dict(img="p6.jpg", title_en="Lasfar Gaz", title_ar="Lasfar Gaz",
         location_en="Morocco", location_ar="المغرب",
         typology_en="Ground-mounted solar plant", typology_ar="محطة شمسية أرضية",
         installed_power_en="50 kWp", installed_power_ar="50 kWp",
         contract_en="EPC en Autoproduction", contract_ar="EPC للإنتاج الذاتي"),
]

# 16 FAQ items: (question_en, answer_en, question_ar, answer_ar) from en/ar faq.html
FAQS = [
    ("What does APS specialize in?",
     "APS is a diversified group covering trading, supply, and the installation of electro-mechanical plants, delivered through five specialized divisions.",
     "ما هو مجال تخصّص APS؟",
     "‏APS مجموعة متنوّعة الأنشطة تغطّي التجارة والتوريد وتركيب المنشآت الكهروميكانيكية، عبر خمسة أقسام متخصّصة."),
    ("Which industries does APS support?",
     "Industrial, governmental, residential, healthcare, and educational facilities across Saudi Arabia.",
     "ما القطاعات التي تخدمها APS؟",
     "المنشآت الصناعية والحكومية والسكنية والصحية والتعليمية في جميع أنحاء المملكة العربية السعودية."),
    ("Where is APS headquartered and where does it operate?",
     "APS is headquartered in Jeddah and operates nationwide through regional offices, including Riyadh and Al Khobar.",
     "أين يقع المقر الرئيسي لـ APS وأين تعمل؟",
     "يقع المقر الرئيسي لـ APS في جدة، وتعمل في جميع أنحاء المملكة من خلال مكاتب إقليمية، تشمل الرياض والخبر."),
    ("How long has APS been in operation?",
     "APS has built strong business relationships across Saudi Arabia since its inception, with divisions such as SPS established in 2001.",
     "منذ متى تعمل APS؟",
     "بنت APS علاقات عمل قوية في جميع أنحاء المملكة العربية السعودية منذ تأسيسها، مع أقسام مثل SPS التي تأسّست عام 2001."),
    ("Does APS provide installation services?",
     "Yes — APS delivers complete solutions including system integration, installation, commissioning, training, and after-sales support.",
     "هل تقدّم APS خدمات التركيب؟",
     "نعم — تقدّم APS حلولاً متكاملة تشمل تكامل الأنظمة والتركيب والتشغيل والتدريب والدعم بعد البيع."),
    ("What engineering disciplines does APS cover?",
     "In-house process, mechanical, and electrical engineering, supported by detailed design and layout optimization.",
     "ما التخصّصات الهندسية التي تغطّيها APS؟",
     "هندسة العمليات والهندسة الميكانيكية والكهربائية داخلياً، مدعومة بالتصميم التفصيلي وتحسين المخطّطات."),
    ("Can APS provide turnkey EPC services?",
     "Yes — APS delivers turnkey EPC projects from design and supply through installation, commissioning, and handover.",
     "هل يمكن لـ APS تقديم خدمات EPC بنظام تسليم المفتاح؟",
     "نعم — تنفّذ APS مشاريع EPC بنظام تسليم المفتاح، من التصميم والتوريد وصولاً إلى التركيب والتشغيل والتسليم."),
    ("Does APS offer after-sales support and maintenance?",
     "Yes — APS provides reliable after-sales support, preventive and corrective maintenance, and long-term asset management.",
     "هل توفّر APS الدعم بعد البيع والصيانة؟",
     "نعم — توفّر APS دعماً موثوقاً بعد البيع، وصيانة وقائية وتصحيحية، وإدارة طويلة الأمد للأصول."),
    ("Can APS handle large-scale projects?",
     "Yes — APS has delivered major projects across Saudi Arabia for leading institutions and commercial clients.",
     "هل تستطيع APS تنفيذ المشاريع واسعة النطاق؟",
     "نعم — نفّذت APS مشاريع كبرى في جميع أنحاء المملكة العربية السعودية لصالح مؤسسات رائدة وعملاء تجاريين."),
    ("What solar and renewable energy projects has APS delivered?",
     "Through its AZOLIS division, APS develops, finances, builds, and maintains solar power plants for the commercial and industrial segment.",
     "ما مشاريع الطاقة الشمسية والمتجدّدة التي نفّذتها APS؟",
     "من خلال قسم أزوليس، تتولّى APS تطوير محطّات الطاقة الشمسية وتمويلها وبناءها وصيانتها لصالح القطاعين التجاري والصناعي."),
    ("How does APS manage quality across its projects?",
     "APS operates with integrity and professionalism, prioritizing safety, quality, and accountability on every project it undertakes.",
     "كيف تدير APS الجودة في مشاريعها؟",
     "تعمل APS بنزاهة واحترافية، مع إعطاء الأولوية للسلامة والجودة والمساءلة في كل مشروع تتولّاه."),
    ("How can I submit a project inquiry or RFP?",
     "You can reach our team through the contact details below, and we will respond promptly with solutions tailored to your needs.",
     "كيف يمكنني تقديم استفسار عن مشروع أو طلب عرض أسعار (RFP)؟",
     "يمكنك التواصل مع فريقنا عبر بيانات الاتصال أدناه، وسنردّ عليك سريعاً بحلول مصمّمة وفق احتياجاتك."),
    ("Does APS work with international partners?",
     "Yes — APS collaborates with leading international manufacturers and technology providers.",
     "هل تعمل APS مع شركاء دوليين؟",
     "نعم — تتعاون APS مع كبرى الشركات المصنّعة ومزوّدي التقنيات على المستوى الدولي."),
    ("How does APS approach strategic partnerships?",
     "APS builds long-term partnerships based on trust, transparency, and consistent performance.",
     "كيف تتعامل APS مع الشراكات الاستراتيجية؟",
     "تبني APS شراكات طويلة الأمد قائمة على الثقة والشفافية والأداء المتّسق."),
    ("Does APS engage in subcontracting or joint ventures?",
     "Yes — APS works through specialized companies and partnerships to deliver integrated solutions.",
     "هل تعمل APS في التعاقد من الباطن أو المشاريع المشتركة؟",
     "نعم — تعمل APS من خلال شركات متخصّصة وشراكات لتقديم حلول متكاملة."),
    ("What certifications and compliance standards does APS hold?",
     "APS adheres to recognized industry standards and a governance-driven framework across all of its operations.",
     "ما الشهادات ومعايير الامتثال التي تلتزم بها APS؟",
     "تلتزم APS بمعايير الصناعة المعتمدة وبإطار قائم على الحوكمة في جميع عملياتها."),
]

# Pages (home/about/contact) — titles from store.js; SEO seeded lightly for Phase 4.
PAGES = [
    dict(slug="home", title_en="Home", title_ar="الرئيسية",
         seo_title_en="APS — Arabian Projects & Supplies", seo_title_ar="APS — العربية للمشاريع والتوريدات",
         seo_desc_en="Integrity-led supply & installation across Saudi Arabia.",
         seo_desc_ar="توريد وتركيب مبني على النزاهة في كل أنحاء السعودية."),
    dict(slug="about", title_en="About", title_ar="عن الشركة",
         seo_title_en="About APS Group", seo_title_ar="عن مجموعة APS",
         seo_desc_en="A diversified Saudi group delivering electro-mechanical and industrial solutions.",
         seo_desc_ar="مجموعة سعودية متنوعة تقدّم حلولاً كهروميكانيكية وصناعية."),
    dict(slug="contact", title_en="Contact us", title_ar="اتصل بنا",
         seo_title_en="Contact APS", seo_title_ar="تواصل مع APS",
         seo_desc_en="Get in touch with the APS team.", seo_desc_ar="تواصل مع فريق APS."),
]


# Page sections (home/about/contact) — bilingual content mirroring his store.js
# seed. Stored in PageSection.data so his admin page editors show real content.
# Order matches his schema defaults.
PAGE_SECTIONS = {
    "home": [
        ("hero", {
            "title": bi("Integrity-led supply & installation across Saudi Arabia",
                        "توريد وتركيب مبني على النزاهة في كل أنحاء السعودية"),
            "lead": bi("APS delivers trading, supply, and electro-mechanical installation through specialized companies and global partners.",
                       "تقدّم APS التجارة والتوريد والتركيب الكهروميكانيكي عبر شركات متخصصة وشركاء عالميين."),
            "cta": bi("Explore Divisions", "استكشف الأقسام"),
            "features": [
                {"icon": "secure.svg", "text": bi("Integrity-led operations", "عمليات قائمة على النزاهة")},
                {"icon": "checkhand.svg", "text": bi("Global partners", "شركاء عالميون")},
                {"icon": "Icon-6.svg", "text": bi("Nationwide coverage", "تغطية على مستوى المملكة")},
            ],
        }),
        ("about", {
            "eyebrow": bi("About", "عن الشركة"),
            "title": bi("About APS Group", "عن مجموعة APS"),
            "body": bi("Arabian Projects and Supplies (APS) is a diversified group of businesses covering a wide spectrum of activities from trading to the supply and installation of electro-mechanical plants.",
                       "العربية للمشاريع والتوريدات (APS) مجموعة أعمال متنوعة تغطي نطاقاً واسعاً من الأنشطة من التجارة إلى توريد وتركيب المنشآت الكهروميكانيكية."),
            "cta": bi("Learn More", "اعرف المزيد"),
        }),
        ("divisions", {
            "title": bi("Specialized Divisions. Unified Excellence.", "أقسام متخصصة. تميّز موحّد."),
            "subtitle": bi("Explore APS's specialized companies across security systems, industrial machinery, environmental solutions, and technology.",
                           "استكشف شركات APS المتخصصة في أنظمة الأمن والآلات الصناعية والحلول البيئية والتقنية."),
        }),
        ("partners", {
            "title": bi("OUR PARTNERS", "شركاؤنا"),
            "subtitle": bi("Arabian Projects and Supplies works alongside trusted global manufacturers and brands.",
                           "تعمل العربية للمشاريع والتوريدات مع مصنّعين وعلامات عالمية موثوقة."),
        }),
        ("contact", {
            "title": bi("Get in touch", "تواصل معنا"),
            "subtitle": bi("Tell us about your project and our team will get back to you.",
                           "احكِ لنا عن مشروعك وفريقنا هيرجعلك."),
        }),
    ],
    "about": [
        ("banner", {"eyebrow": bi("About (APS)", "عن (APS)"),
                    "title": bi("About Arabian Projects & Supplies", "عن العربية للمشاريع والتوريدات")}),
        ("who", {"title": bi("Who We Are", "من نحن"),
                 "body": bi("APS is a diversified group delivering electro-mechanical and industrial solutions across Saudi Arabia, guided by integrity and professionalism.",
                            "APS مجموعة متنوعة تقدّم حلولاً كهروميكانيكية وصناعية في كل أنحاء السعودية، تقودها النزاهة والاحترافية.")}),
        ("foundation", {"title": bi("Our Foundation", "أساسنا"),
                        "body": bi("Built on integrity, professionalism, and a governance-driven framework.",
                                   "مبني على النزاهة والاحترافية وإطار قائم على الحوكمة.")}),
        ("principles", {"title": bi("Business Principles", "مبادئ العمل"),
                        "body": bi("We operate with transparency, accountability, and long-term partnership in mind.",
                                   "نعمل بشفافية ومسؤولية وبعقلية الشراكة طويلة المدى.")}),
    ],
    "contact": [
        ("banner", {"eyebrow": bi("Contact (APS)", "تواصل (APS)"),
                    "title": bi("Get in touch with APS", "تواصل مع APS")}),
        ("form", {"heading": bi("Send us a message", "ابعتلنا رسالة"),
                  "submit": bi("Send message", "إرسال")}),
        ("info", {"heading": bi("Reach us directly", "تواصل معنا مباشرة")}),
        ("map", {"caption": bi("Our location in Jeddah", "موقعنا في جدة")}),
    ],
}

DIVISION_ORDER = ["banner", "about", "systems", "projects", "contact"]

# Real, per-division section order (each division's actual public sections, in
# display order). Drives the public page render loop + the CMS section reorder.
# Partners are managed globally from /cms/partners/ (one shared marquee read by
# every page), so divisions no longer carry their own partners section.
DIV_SECTION_ORDER = {
    "sps":    ["banner", "about", "systems", "projects", "contact"],
    "beta":   ["banner", "about", "categories", "contact"],
    "enviro": ["banner", "about", "suppliers", "solutions", "contact"],
    "ags":    ["banner", "about", "foundation", "products", "contact"],
    "azolis": ["banner", "about", "lifecycle", "projects", "contact"],
}

# his store.js division.slug is the public path, not the object key
PUBLIC_SLUG = {
    "sps": "/sps", "beta": "/beta-machinery", "enviro": "/envirosystems",
    "ags": "/advanced-green-solutions", "azolis": "/azolis-middle-east",
}

# exact nav/footer menu labels (these differ from the full division name and are
# identical between the header dropdown and the footer "Our Divisions" list)
MENU_LABEL = {
    "sps": ("Saudi Projects & Supplies", "السعودية للمشاريع والتوريدات"),
    "beta": ("Beta Machinery", "بيتا للمعدّات"),
    "enviro": ("Envirosystems", "إنفايروسيستمز"),
    "ags": ("Advanced Green Solutions", "الحلول الخضراء المتقدّمة"),
    "azolis": ("AZOLIS Middle East", "أزوليس الشرق الأوسط"),
}


class Command(BaseCommand):
    help = "Seed the real approved APS content (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        # ---- SiteSettings (matches his footer + store.js settings)
        s = SiteSettings.load()
        s.site_name_en = "Arabian Projects & Supplies (APS)"
        s.site_name_ar = "العربية للمشاريع والتوريدات (APS)"
        s.tagline_en = "Integrity-led supply & installation across Saudi Arabia"
        s.tagline_ar = "توريد وتركيب مبني على النزاهة في كل أنحاء السعودية"
        s.phone = "+966 12 345 6789"
        s.email = "info@aps-sa.com"
        s.address_en = "Jeddah, Saudi Arabia"
        s.address_ar = "جدة، المملكة العربية السعودية"  # matches his footer (content source of truth)
        s.maintenance_mode = False
        s.save()

        # Brand tokens — set to the EXACT values in his variables.css so the
        # public :root override renders identically by default.
        b = Brand.load()
        b.color_primary = "#558BAD"; b.color_hover = "#477694"; b.color_accent = "#1A6DA2"
        b.color_text = "#0B1220"; b.color_muted = "#475569"; b.color_bg = "#F7FAFC"
        b.color_footer = "#0B1220"  # matches --color-footer-bg
        b.arabic_font = "Cairo"; b.english_font = "Inter"
        b.save()

        for i, (platform, url, icon) in enumerate(SOCIAL):
            SocialLink.objects.update_or_create(
                platform=platform, defaults=dict(url=url, icon=icon, order=i))

        for i, (name, image) in enumerate(PARTNERS):
            Partner.objects.update_or_create(
                order=i, defaults=dict(name=name, image=image))

        for p in PAGES:
            page, _ = Page.objects.update_or_create(slug=p["slug"], defaults={
                k: v for k, v in p.items() if k != "slug"} | {"status": "published"})
            for i, (key, data) in enumerate(PAGE_SECTIONS[page.slug]):
                PageSection.objects.update_or_create(
                    page=page, key=key, defaults=dict(order=i, hidden=False, data=data))

        for d in DIVISIONS:
            div, _ = Division.objects.update_or_create(
                slug=d["slug"], defaults={**{k: v for k, v in d.items() if k != "slug"},
                                          "status": "published",
                                          "cms_extra": {
                                              "projects_title": bi("Our Projects", "مشاريعنا"),
                                              "public_slug": PUBLIC_SLUG.get(d["slug"], "/" + d["slug"]),
                                              "menu_en": MENU_LABEL.get(d["slug"], (d["slug"], d["slug"]))[0],
                                              "menu_ar": MENU_LABEL.get(d["slug"], (d["slug"], d["slug"]))[1],
                                              "order": list(DIV_SECTION_ORDER.get(d["slug"], DIVISION_ORDER)),
                                              "hidden": {}}})
            if d["slug"] == "sps":
                for i, (img, te, ta) in enumerate(SPS_PROJECTS):
                    DivisionProject.objects.update_or_create(
                        division=div, order=i,
                        defaults=dict(image=f"assets/images/divisions/sps/projects/{img}",
                                      title_en=te, title_ar=ta))
            elif d["slug"] == "azolis":
                for i, pr in enumerate(AZOLIS_PROJECTS):
                    DivisionProject.objects.update_or_create(
                        division=div, order=i,
                        defaults=dict(
                            image=f"assets/images/divisions/azolis/projects/{pr['img']}",
                            title_en=pr["title_en"], title_ar=pr["title_ar"],
                            location_en=pr["location_en"], location_ar=pr["location_ar"],
                            typology_en=pr["typology_en"], typology_ar=pr["typology_ar"],
                            installed_power_en=pr["installed_power_en"], installed_power_ar=pr["installed_power_ar"],
                            contract_en=pr["contract_en"], contract_ar=pr["contract_ar"]))

        for i, (qe, ae, qa, aa) in enumerate(FAQS):
            FAQItem.objects.update_or_create(
                order=i, defaults=dict(question_en=qe, answer_en=ae,
                                       question_ar=qa, answer_ar=aa))

        # division middle-section cards (extracted byte-exact from his HTML)
        divs_by_slug = {d.slug: d for d in Division.objects.all()}
        cards = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
        keep_cards = []
        for c in cards:
            div = divs_by_slug.get(c["division"])
            if not div:
                continue
            obj, _ = DivisionCard.objects.update_or_create(
                division=div, section_key=c["section_key"], order=c["order"],
                defaults=dict(icon=c["icon"], title_en=c["title_en"], title_ar=c["title_ar"],
                              body_en=c["body_en"], body_ar=c["body_ar"], extra=c["extra"]))
            keep_cards.append(obj.pk)
        DivisionCard.objects.exclude(pk__in=keep_cards).delete()

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: {Page.objects.count()} pages, {Division.objects.count()} divisions, "
            f"{DivisionProject.objects.count()} projects, {FAQItem.objects.count()} FAQ, "
            f"{Partner.objects.count()} partners, {SocialLink.objects.count()} social, "
            f"{DivisionCard.objects.count()} cards, settings+brand."))
