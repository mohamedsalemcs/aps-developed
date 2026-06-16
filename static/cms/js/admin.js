/* APS CMS admin — functional client app. Data in Store (localStorage).
   Sections are data-driven (reorder / add / delete / hide). Bilingual content
   (AR+EN required, validated). Admin UI language switch (AR/EN). Auth guard. */
(function () {
  "use strict";
  var S = window.Store;
  function $(s, r) { return (r || document).querySelector(s); }
  function $all(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(v) { return String(v == null ? "" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }

  /* ------------------------------------------------------------ auth guard */
  // Auth gate: trust the server's real session first (window.__APS_AUTHED__ is
  // injected only on pages Django served to an authenticated user). Falling back
  // to the localStorage flag keeps the designer's standalone build working, but
  // a browser that doesn't persist localStorage (privacy mode, embedded webview)
  // must NOT bounce an authenticated admin to the login screen on every click.
  if (!window.__APS_AUTHED__ && !localStorage.getItem("aps_auth")) { location.replace("login.html"); return; }

  /* ---------------------------------------------------------------- i18n */
  var uiLang = localStorage.getItem("aps_ui_lang") || "en";  // default English (reviewer note 1)
  function L(ar, en) { return '<span data-i18n="' + esc(en) + '">' + ar + '</span>'; }
  function applyLang() {
    document.documentElement.lang = uiLang;
    document.documentElement.dir = uiLang === "ar" ? "rtl" : "ltr";
    $all("[data-i18n]").forEach(function (el) {
      if (!el.hasAttribute("data-ar")) el.setAttribute("data-ar", el.textContent);
      el.textContent = uiLang === "en" ? el.getAttribute("data-i18n") : el.getAttribute("data-ar");
    });
    $all("[data-langseg] button").forEach(function (b) { b.classList.toggle("is-active", b.getAttribute("data-uilang") === uiLang); });
  }

  /* ---------------------------------------------------------------- toast */
  function toast(msg, ok) {
    var wrap = $(".toast-wrap");
    if (!wrap) { wrap = document.createElement("div"); wrap.className = "toast-wrap"; document.body.appendChild(wrap); }
    var t = document.createElement("div"); t.className = "toast" + (ok === false ? " toast--err" : "");
    t.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">' +
      (ok === false ? '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>' : '<polyline points="20 6 9 17 4 12"/>') +
      '</svg><span>' + esc(msg) + '</span>';
    wrap.appendChild(t);
    setTimeout(function () { t.classList.add("is-out"); setTimeout(function () { t.remove(); }, 260); }, 2600);
  }

  /* ------------------------------------------------ pretty confirm / alert */
  // Drop-in, nicer replacement for native confirm()/alert(): a centered themed
  // modal (same spot the browser dialog appears). Returns a Promise<boolean>
  // (alert resolves true on OK). Exposed on window so inline page scripts use it
  // too. Call sites switch `if(!confirm(x))return;` -> apsConfirm(x).then(ok=>…).
  function apsModal(o) {
    return new Promise(function (resolve) {
      var cancelTxt = o.cancelText || (uiLang === "en" ? "Cancel" : "إلغاء");
      var okTxt = o.confirmText || (o.alert ? (uiLang === "en" ? "OK" : "حسناً") : (uiLang === "en" ? "Confirm" : "تأكيد"));
      var ov = document.createElement("div");
      ov.className = "aps-modal";
      ov.innerHTML =
        '<div class="aps-modal__box" role="alertdialog" aria-modal="true">' +
          (o.title ? '<h3 class="aps-modal__title">' + esc(o.title) + "</h3>" : "") +
          '<p class="aps-modal__msg">' + esc(o.message).replace(/\n/g, "<br>") + "</p>" +
          '<div class="aps-modal__actions">' +
            (o.alert ? "" : '<button type="button" class="btn btn--ghost" data-x="0">' + esc(cancelTxt) + "</button>") +
            '<button type="button" class="btn ' + (o.danger ? "btn--danger" : "btn--primary") + '" data-x="1">' + esc(okTxt) + "</button>" +
          "</div></div>";
      document.body.appendChild(ov);
      requestAnimationFrame(function () { ov.classList.add("is-open"); });
      var okBtn = ov.querySelector('[data-x="1"]'); if (okBtn) okBtn.focus();
      function close(val) {
        ov.classList.remove("is-open");
        document.removeEventListener("keydown", onKey);
        setTimeout(function () { ov.remove(); }, 180);
        resolve(val);
      }
      function onKey(ev) {
        if (ev.key === "Escape" && !o.alert) close(false);
        else if (ev.key === "Enter") close(true);
      }
      document.addEventListener("keydown", onKey);
      ov.addEventListener("click", function (ev) {
        if (ev.target.closest('[data-x="1"]')) return close(true);
        if (ev.target.closest('[data-x="0"]')) return close(false);
        if (ev.target === ov && !o.alert) close(false); // backdrop = cancel
      });
    });
  }
  function apsConfirm(message, o) { o = o || {}; return apsModal({ message: message, title: o.title, confirmText: o.confirmText, cancelText: o.cancelText, danger: o.danger !== false }); }
  function apsAlert(message, o) { o = o || {}; return apsModal({ message: message, title: o.title, confirmText: o.confirmText, alert: true }); }
  window.apsConfirm = apsConfirm; window.apsAlert = apsAlert;

  /* ----------------------------------------------------- dirty + save bar */
  var dirty = false;
  function setDirty(v) {
    dirty = v;
    $all(".savebar").forEach(function (b) {
      b.classList.toggle("is-dirty", v);
      var st = $(".savebar__status", b); if (st) st.textContent = v ? "تغييرات غير محفوظة · Unsaved changes" : "كل التغييرات محفوظة · All saved";
    });
  }
  window.addEventListener("beforeunload", function (e) { if (dirty) { e.preventDefault(); e.returnValue = ""; } });

  /* ------------------------------------------------------------ validation */
  function markField(input) {
    var col = input.closest(".field-bi__col[data-req]"); if (col) col.classList.toggle("is-error", !String(input.value).trim());
    var pf = input.closest(".field[data-req]"); if (pf) pf.classList.toggle("is-error", !String(input.value).trim());
  }
  function validate() {
    var bad = [];
    $all(".field-bi__col[data-req]").forEach(function (col) { var i = col.querySelector("[data-field]"); if (i && !String(i.value).trim()) { col.classList.add("is-error"); bad.push(col); } else col.classList.remove("is-error"); });
    $all(".field[data-req]").forEach(function (fl) { var i = fl.querySelector(".input,.select"); if (i && !String(i.value).trim()) { fl.classList.add("is-error"); bad.push(fl); } else fl.classList.remove("is-error"); });
    return bad;
  }
  function reveal(el) {
    var panel = el.closest("[data-tabpanel]");
    if (panel && panel.hidden) { var tab = $('.tab[data-tab="' + panel.getAttribute("data-tabpanel") + '"]'); if (tab) tab.click(); }
    var sb = el.closest(".section-block"); if (sb) sb.classList.add("is-open");
    setTimeout(function () { el.scrollIntoView({ behavior: "smooth", block: "center" }); }, 60);
  }
  function save(silent) {
    var bad = validate();
    if (bad.length) { reveal(bad[0]); toast("في " + bad.length + " حقل مطلوب فاضي — اكمل اللغتين", false); return false; }
    try { S.save(); } catch (e) { toast("تعذّر الحفظ — تأكد من تسجيل الدخول والاتصال ثم أعد المحاولة", false); return false; }
    setDirty(false); if (!silent) toast("تم حفظ التغييرات"); return true;
  }

  /* ------------------------------------------------------------ hydrate */
  function applyHidden(input) {
    if (/\.hidden$/.test(input.getAttribute("data-field") || "")) { var sb = input.closest(".section-block"); if (sb) sb.classList.toggle("is-hidden", !!input.checked); }
  }
  function hydrate(root) {
    $all("[data-field]", root || document).forEach(function (input) {
      var v = S.get(input.getAttribute("data-field"), input.getAttribute("data-lang") || null);
      if (input.type === "checkbox") { input.checked = !!v; applyHidden(input); } else input.value = v;
    });
    refreshCompleteness(root);
  }
  function refreshCompleteness(root) {
    $all("[data-completeness]", root || document).forEach(function (el) {
      var pct = S.completeness(el.getAttribute("data-completeness"));
      var bar = $(".trans-bar span", el); if (bar) bar.style.width = pct + "%";
      var val = $("[data-completeness-val]", el); if (val) val.textContent = pct + "%";
    });
  }
  function onEdit(e) {
    var input = e.target.closest("[data-field]"); if (!input) return;
    S.set(input.getAttribute("data-field"), input.getAttribute("data-lang") || null, input.type === "checkbox" ? input.checked : input.value);
    markField(input); applyHidden(input);
    if (input.closest('[data-field^="brand."]')) { applyBrand(); syncColorInputs(input); }
    refreshCompleteness(); setDirty(true);
  }
  document.addEventListener("input", onEdit);
  document.addEventListener("change", onEdit);

  /* ----------------------------------------------------------- field html */
  function biCol(labelHtml, cls, path, lang, ml) {
    var d = lang === "ar" ? "rtl" : "ltr";
    var ctrl = ml ? '<textarea class="textarea" dir="' + d + '" data-field="' + path + '" data-lang="' + lang + '"></textarea>'
                  : '<input class="input" dir="' + d + '" data-field="' + path + '" data-lang="' + lang + '" />';
    return '<div class="field-bi__col field-bi__col--' + cls + '" data-req><span class="field-bi__lang">' + labelHtml + '</span>' + ctrl + '<span class="field-bi__req">' + L("مطلوب", "Required") + '</span></div>';
  }
  function biField(labelHtml, path, ml) {
    return '<div class="field-bi"><div class="field-bi__head"><label>' + labelHtml + ' <span class="req">*</span></label></div>' +
      '<div class="field-bi__cols">' + biCol(L("عربي", "Arabic"), "ar", path, "ar", ml) + biCol(L("English", "English"), "en", path, "en", ml) + '</div></div>';
  }
  function enField(labelHtml, path) {
    return '<div class="field" data-req><label>' + labelHtml + ' <span class="en-only">' + L("إنجليزي فقط", "English only") + '</span></label><input class="input" dir="ltr" data-field="' + path + '" /></div>';
  }
  function plainField(labelHtml, path) {
    return '<div class="field"><label>' + labelHtml + '</label><input class="input" dir="ltr" data-field="' + path + '" /></div>';
  }

  /* ----------------------------------------------------------- repeaters */
  var GRIP = '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="9" cy="5" r="1.4"/><circle cx="15" cy="5" r="1.4"/><circle cx="9" cy="12" r="1.4"/><circle cx="15" cy="12" r="1.4"/><circle cx="9" cy="19" r="1.4"/><circle cx="15" cy="19" r="1.4"/></svg>';
  var TRASH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';
  var WEB = "../../website/assets/images/";
  var ARR_UP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>';
  var ARR_DN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>';
  function rTools(path, i, total) {
    return '<div class="repeat-item__tools">' +
      '<button type="button" class="sec-btn" data-repeat-move="up" data-rm-path="' + path + '" data-rm-index="' + i + '" title="لأعلى"' + (i === 0 ? " disabled" : "") + '>' + ARR_UP + '</button>' +
      '<button type="button" class="sec-btn" data-repeat-move="down" data-rm-path="' + path + '" data-rm-index="' + i + '" title="لأسفل"' + (i === total - 1 ? " disabled" : "") + '>' + ARR_DN + '</button>' +
      '<button type="button" class="repeat-item__del" data-repeat-del="' + path + '" data-repeat-index="' + i + '" title="حذف">' + TRASH + '</button></div>';
  }
  function iconSrc(v) {
    v = v || "";
    if (/^(data:|blob:)/.test(v)) return v;
    if (v.indexOf("assets/") === 0) return WEB.replace("assets/images/", "") + v;  // full path
    if (v.indexOf("uploads/") === 0) return WEB + v;                                // uploaded icon
    return WEB + "icons/" + v;                                                      // bare filename
  }
  function imgSrc(v) { return /^(data:|blob:)/.test(v || "") ? v : WEB + v; }
  var PH_IMG = "data:image/svg+xml;charset=utf-8," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="120" height="90" viewBox="0 0 120 90"><rect width="120" height="90" rx="8" fill="#eef2f7"/><g fill="none" stroke="#9fb2c8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="34" y="24" width="52" height="42" rx="5"/><circle cx="48" cy="40" r="6"/><path d="M36 60l16-14 12 10 9-8 11 12"/></g></svg>');
  function photoSrc(v) { return v ? imgSrc(v) : PH_IMG; }
  // About-page card icons are stored as a full "assets/images/..." path (not a
  // bare filename), so they only need the website root prefix for preview.
  function iconCtl(labelHtml, path, val) {
    return '<div class="field"><label>' + labelHtml + '</label><div class="iconctl">' +
      '<img class="iconctl__img" src="' + esc(iconSrc(val)) + '" alt="" data-icon-view="' + path + '" />' +
      '<button type="button" class="btn btn--ghost btn--sm" data-icon-replace="' + path + '">' + L("استبدال (صورة/SVG)", "Replace (image/SVG)") + '</button></div></div>';
  }
  var TPL = {
    feature: function (path, i, item, total) {
      return '<div class="repeat-item"><span class="repeat-item__grip">' + GRIP + '</span><span class="repeat-item__num">' + (i + 1) + '</span><div class="repeat-item__body">' +
        iconCtl(L("الأيقونة", "Icon"), path + "." + i + ".icon", item.icon) +
        biField(L("النص", "Text"), path + "." + i + ".text", false) +
        '</div>' + rTools(path, i, total) + '</div>';
    },
    project: function (path, i, item, total) {
      return '<div class="repeat-item"><span class="repeat-item__grip">' + GRIP + '</span><span class="repeat-item__num">' + (i + 1) + '</span><div class="repeat-item__body">' +
        '<div class="field"><label>' + L("صورة المشروع", "Project image") + '</label><div class="iconctl">' +
        '<img class="iconctl__img iconctl__img--photo" src="' + esc(photoSrc(item.img)) + '" alt="" data-icon-view="' + path + "." + i + '.img" />' +
        '<button type="button" class="btn btn--ghost btn--sm" data-img-replace="' + path + "." + i + '.img">' + L("استبدال الصورة", "Replace image") + '</button></div></div>' +
        biField(L("اسم المشروع", "Project title"), path + "." + i + ".title", false) +
        '</div>' + rTools(path, i, total) + '</div>';
    },
    faq: function (path, i, item, total) {
      return '<div class="repeat-item"><span class="repeat-item__grip">' + GRIP + '</span><span class="repeat-item__num">' + (i + 1 < 10 ? "0" : "") + (i + 1) + '</span><div class="repeat-item__body">' +
        biField(L("السؤال", "Question"), path + "." + i + ".q", false) + biField(L("الإجابة", "Answer"), path + "." + i + ".a", true) +
        '</div>' + rTools(path, i, total) + '</div>';
    },
    card: function (path, i, item, total) {
      return '<div class="repeat-item"><span class="repeat-item__grip">' + GRIP + '</span><span class="repeat-item__num">' + (i + 1) + '</span><div class="repeat-item__body">' +
        iconCtl(L("الأيقونة", "Icon"), path + "." + i + ".icon", item.icon) +
        biField(L("العنوان", "Title"), path + "." + i + ".title", false) +
        biField(L("النص", "Text"), path + "." + i + ".text", true) +
        '</div>' + rTools(path, i, total) + '</div>';
    },
    divcard: function (path, i, item, total) {
      return '<div class="repeat-item"><span class="repeat-item__grip">' + GRIP + '</span><span class="repeat-item__num">' + (i + 1) + '</span><div class="repeat-item__body">' +
        '<div class="field"><label>' + L("صورة الكارت", "Card image") + '</label><div class="iconctl">' +
        '<img class="iconctl__img iconctl__img--photo" src="' + esc(photoSrc(item.img)) + '" alt="" data-icon-view="' + path + "." + i + '.img" />' +
        '<button type="button" class="btn btn--ghost btn--sm" data-img-replace="' + path + "." + i + '.img">' + L("استبدال الصورة", "Replace image") + '</button></div></div>' +
        biField(L("العنوان", "Title"), path + "." + i + ".title", false) +
        biField(L("الوصف", "Description"), path + "." + i + ".text", true) +
        '</div>' + rTools(path, i, total) + '</div>';
    }
  };
  var EMPTY = {
    feature: function () { return { icon: "globe.svg", text: { en: "", ar: "" } }; },
    project: function () { return { img: "divisions/sps/projects/p1.jpg", title: { en: "", ar: "" } }; },
    faq: function () { return { q: { en: "", ar: "" }, a: { en: "", ar: "" } }; },
    card: function () { return { icon: "assets/images/icons/ic-vision.svg", rule: "inline-size: 58px", title: { en: "", ar: "" }, text: { en: "", ar: "" } }; },
    divcard: function () { return { img: "", link: "/", title: { en: "", ar: "" }, text: { en: "", ar: "" } }; }
  };
  function renderRepeater(c) {
    var path = c.getAttribute("data-repeat"), tpl = c.getAttribute("data-repeat-tpl");
    var arr = S.getArray(path);
    c.innerHTML = arr.map(function (item, i) { return TPL[tpl](path, i, item, arr.length); }).join("");
    hydrate(c); applyLang();
  }

  /* ======================================================= SECTION ENGINE */
  var IC = {
    up: '<line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>',
    down: '<line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>',
    eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    eyeoff: '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>',
    trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>', plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>'
  };
  function ico(n) { return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + IC[n] + '</svg>'; }
  function secIcon(n) {
    var P = { zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>', file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>', layers: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/>', award: '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>', phone: '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>', image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>', grid: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>', mail: '<path d="M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><polyline points="22,6 12,13 2,6"/>', map: '<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/>', shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>', users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>' };
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + (P[n] || P.file) + '</svg>';
  }
  var SCHEMAS = {
    home: { def: ["hero", "about", "divisions", "partners", "contact"], defs: {
      hero: { icon: "zap", t: ["الهيرو", "Hero"], fields: [["title", "العنوان", "Title"], ["lead", "النص التمهيدي", "Lead", 1], ["cta", "نص الزر", "Button text"]], rep: ["features", "feature", "المميزات السريعة", "Quick features"] },
      about: { icon: "file", t: ["عن APS", "About APS"], fields: [["eyebrow", "العنوان الفرعي", "Eyebrow"], ["title", "العنوان", "Title"], ["body", "النص", "Body", 1], ["cta", "نص الزر", "Button text"]] },
      divisions: { icon: "layers", t: ["الأقسام", "Divisions"], fields: [["title", "العنوان", "Title"], ["subtitle", "النص الفرعي", "Subtitle", 1]], rep: ["cards", "divcard", "كروت الأقسام (صورة + عنوان + وصف)", "Division cards (image + title + text)", true] },
      partners: { icon: "award", t: ["شركاؤنا", "Partners"], fields: [["title", "العنوان", "Title"], ["subtitle", "النص الفرعي", "Subtitle", 1]], note: ["اللوجوهات تُدار من صفحة الشركاء.", "Logos are managed in the Partners page."] },
      contact: { icon: "phone", t: ["اتصل بنا", "Contact"], fields: [["eyebrow", "التاج (فوق العنوان)", "Tag (eyebrow)"], ["title", "العنوان", "Title"], ["subtitle", "النص الفرعي", "Subtitle", 1]] }
    }},
    about: { def: ["banner", "who", "foundation", "principles"], defs: {
      banner: { icon: "image", t: ["البانر", "Banner"], fields: [["eyebrow", "العنوان الفرعي", "Eyebrow"], ["title", "العنوان", "Title"]] },
      who: { icon: "file", t: ["من نحن", "Who We Are"], fields: [["title", "العنوان", "Title"], ["body", "النص", "Body", 1]] },
      foundation: { icon: "award", t: ["الرؤية والرسالة", "Foundation"], fields: [["title", "العنوان", "Title"], ["eyebrow", "العنوان الفرعي", "Eyebrow"]], rep: ["cards", "card", "الكروت (الرؤية / الرسالة / القيم)", "Cards (Vision / Mission / Values)"] },
      principles: { icon: "zap", t: ["مبادئ العمل", "Principles"], fields: [["title", "العنوان", "Title"], ["subtitle", "النص الفرعي", "Subtitle", 1]], rep: ["cards", "card", "كروت المبادئ", "Principle cards"] }
    }},
    contact: { def: ["banner", "form", "info", "map"], defs: {
      banner: { icon: "image", t: ["البانر", "Banner"], fields: [["eyebrow", "العنوان الفرعي", "Eyebrow"], ["title", "العنوان", "Title"]] },
      form: { icon: "mail", t: ["النموذج", "Form"], fields: [["title", "عنوان القسم", "Section title"], ["subtitle", "عنوان النموذج", "Form heading", 1], ["submit", "نص زر الإرسال", "Submit label"]] },
      info: { icon: "phone", t: ["بيانات التواصل", "Contact info"], fields: [["heading", "عنوان الكارت", "Card heading"]], note: ["الهاتف والبريد والعنوان من الإعدادات.", "Phone, email and address come from Settings."] },
      map: { icon: "map", t: ["الخريطة", "Map"], fields: [["title", "عنوان القسم", "Section title"], ["office", "اسم المكتب", "Office name"], ["addr1", "العنوان (سطر 1)", "Address line 1"], ["addr2", "العنوان (سطر 2)", "Address line 2"], ["hours", "ساعات العمل", "Working hours"]], note: ["المدينة/الدولة من الإعدادات؛ الخريطة صورة ثابتة.", "City/country come from Settings; the map is a static image."] }
    }},
    division: { def: ["banner", "about", "systems", "projects", "contact"], defs: {
      banner: { icon: "image", t: ["البانر", "Banner"], name: true, fields: [["subtitle", "العنوان الفرعي", "Subtitle"]] },
      about: { icon: "file", t: ["عن القسم", "About"], fields: [["title", "العنوان", "Title"], ["body", "النص", "Body", 1]] },
      systems: { icon: "grid", t: ["القسم الرئيسي", "Main section"], fields: [["title", "العنوان", "Title"], ["subtitle", "النص الفرعي", "Subtitle", 1]] },
      projects: { icon: "image", t: ["مشاريعنا", "Our Projects"], fields: [["title", "عنوان القسم", "Section title"]], rep: ["items", "project", "المشاريع", "Projects"] },
      contact: { icon: "phone", t: ["بيانات التواصل", "Contact info"], plain: [["phone", "الهاتف", "Phone"], ["site", "الموقع الإلكتروني", "Website"], ["email", "البريد الإلكتروني", "Email"]] }
    }}
  };

  function orderOf(scope, schema) {
    var o = S.getArray(scope + ".order").filter(function (k) { return schema.defs[k]; });
    return o.length ? o : schema.def.slice();
  }
  function sectionBlock(scope, type, key, i, total) {
    var def = SCHEMAS[type].defs[key], base = scope + ".sections." + key, body = [];
    // Header label: for a division's main "systems" section, show the actual
    // saved title so the editor matches the real website section (e.g. beta
    // shows "Machinery Categories", not a generic "Systems & Solutions").
    var secLabel = L(def.t[0], def.t[1]);
    if (type === "division" && key === "systems") {
      var st = S.get(base + ".title", uiLang) || S.get(base + ".title", "en") || S.get(base + ".title", "ar");
      if (st) secLabel = st;
    }
    if (def.name) body.push(biField(L("اسم القسم (عنوان البانر)", "Division name (banner title)"), scope + ".name", false));
    (def.fields || []).forEach(function (fd) { body.push(biField(L(fd[1], fd[2]), base + "." + fd[0], fd[3])); });
    // Bespoke secondary-section headings that live next to the main section on
    // some division pages (enviro has a Suppliers block; ags has a Foundation
    // block). Editable here so they're not hardcoded on the site.
    if (type === "division" && key === "systems") {
      var dslug = (scope.split(".")[1] || "");
      if (dslug === "enviro") body.push(biField(L("عنوان قسم الموردين", "Suppliers section heading"), scope + ".extra_titles.suppliers", false));
      if (dslug === "ags") {
        body.push(biField(L("عنوان قسم الركائز", "Foundation section heading"), scope + ".extra_titles.foundation", false));
        body.push(biField(L("العنوان الفرعي للركائز", "Foundation eyebrow"), scope + ".extra_titles.foundation_eyebrow", false));
      }
    }
    (def.plain || []).forEach(function (fd) { body.push(plainField(L(fd[1], fd[2]), base + "." + fd[0])); });
    if (def.rep) { var _addBtn = def.rep[4] ? '' : ('<button class="btn btn--soft btn--sm" data-repeat-add="' + base + "." + def.rep[0] + '" style="margin-top:10px">' + ico("plus") + ' ' + L("إضافة", "Add") + '</button>'); body.push('<div class="field"><label>' + L(def.rep[2], def.rep[3]) + '</label><div data-repeat="' + base + "." + def.rep[0] + '" data-repeat-tpl="' + def.rep[1] + '"></div>' + _addBtn + '</div>'); }
    var isHidden = !!S.get(base + ".hidden");
    var tools = '<div class="section-block__tools">' +
      '<span class="section-block__flag">' + L("مخفي", "Hidden") + '</span>' +
      '<button class="sec-btn" data-sec="up" title="تحريك لأعلى"' + (i === 0 ? " disabled" : "") + '>' + ico("up") + '</button>' +
      '<button class="sec-btn" data-sec="down" title="تحريك لأسفل"' + (i === total - 1 ? " disabled" : "") + '>' + ico("down") + '</button>' +
      '<button class="sec-btn" data-sec="hide" title="إظهار/إخفاء">' + ico(isHidden ? "eyeoff" : "eye") + '</button>' +
      '<button class="sec-btn sec-btn--del" data-sec="del" title="حذف">' + ico("trash") + '</button>' +
      '</div>';
    return '<div class="section-block' + (i === 0 ? " is-open" : "") + (isHidden ? " is-hidden" : "") + '" data-section="' + key + '" id="' + key + '">' +
      '<div class="section-block__head"><span class="section-block__grip">' + GRIP + '</span><span class="section-block__icon">' + secIcon(def.icon) + '</span>' +
      '<div><div class="section-block__title">' + secLabel + '</div></div>' + tools +
      '<span class="section-block__chev"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></span></div>' +
      '<div class="section-block__body">' + body.join("") + '</div></div>';
  }
  function addSectionBar(scope, type, order) {
    var avail = SCHEMAS[type].def.filter(function (k) { return order.indexOf(k) < 0; });
    if (!avail.length) return '';  // reviewer: don't show an "all sections added" placeholder
    var menu = avail.map(function (k) { var d = SCHEMAS[type].defs[k]; return '<button class="addsec__opt" data-addsec="' + k + '">' + secIcon(d.icon) + ' ' + L(d.t[0], d.t[1]) + '</button>'; }).join("");
    return '<div class="addsec"><button class="add-block" data-addsec-toggle>' + ico("plus") + ' ' + L("إضافة قسم", "Add section") + '</button><div class="addsec__menu" hidden>' + menu + '</div></div>';
  }
  function renderSections(container) {
    var scope = container.getAttribute("data-sections"), type = container.getAttribute("data-schema");
    var order = orderOf(scope, SCHEMAS[type]);
    container.innerHTML = order.map(function (k, i) { return sectionBlock(scope, type, k, i, order.length); }).join("") + addSectionBar(scope, type, order);
    $all("[data-repeat]", container).forEach(renderRepeater);
    hydrate(container); applyLang();
  }
  function domOrder(container) { return $all("[data-section]", container).map(function (b) { return b.getAttribute("data-section"); }); }
  function persistOrder(container) { S.setArray(container.getAttribute("data-sections") + ".order", domOrder(container)); }

  /* ------------------------------------------------------- color pickers */
  function syncColorInputs(changed) {
    var key = (changed.getAttribute("data-field") || "").split(".").pop();
    var col = $('input[type=color][data-color="' + key + '"]'), hex = $('[data-color-hex="' + key + '"]');
    if (changed === hex && col && /^#[0-9a-fA-F]{6}$/.test(hex.value)) col.value = hex.value;
    if (changed === col && hex) hex.value = col.value.toUpperCase();
  }
  function applyColorInputs() { $all("input[type=color][data-color]").forEach(function (c) { c.value = S.get("brand.colors." + c.getAttribute("data-color")) || "#000000"; }); }
  function applyBrand() {
    var b = S.all().brand || {}; var c = b.colors;
    var prev = $("[data-brand-preview]");
    if (prev && c) { prev.style.setProperty("--bp-primary", c.primary); prev.style.setProperty("--bp-accent", c.accent); }
    var fa = $("[data-font-ar]"); if (fa) fa.style.fontFamily = '"' + (b.arabicFont || "Cairo") + '", sans-serif';
    var fe = $("[data-font-en]"); if (fe) fe.style.fontFamily = '"' + (b.englishFont || "Inter") + '", sans-serif';
  }
  /* Apply the chosen CMS-panel theme (brand.cmsTheme) + interface size
     (brand.fontScale) to the whole admin chrome. Palettes come from the store's
     read-only `themes` map (server-side single source). Exposed on window so the
     brand screen can re-apply it live as the user clicks a swatch. */
  var FONT_SCALE_NUM = { sm: 0.92, md: 1.0, lg: 1.12, xl: 1.25 };
  function applyCmsTheme() {
    var b = S.all().brand || {}, themes = S.all().themes || {};
    var t = themes[b.cmsTheme] || themes.aps || {};
    var root = document.documentElement;
    root.setAttribute("data-theme", t.mode === "dark" ? "dark" : "light");
    if (t.primary) {
      var ac = t.accent || t.primary;
      root.style.setProperty("--primary", ac);
      root.style.setProperty("--primary-2", t.primary);
      root.style.setProperty("--accent", ac);
      root.style.setProperty("--sidebar-active", ac);
    }
    // Tint the sidebar from the theme's dark brand colour (its footer shade), so
    // the side menu actually changes with the chosen theme — inline props beat
    // the [data-theme="dark"] stylesheet rule, so this drives light AND dark.
    if (t.footer) {
      root.style.setProperty("--sidebar", t.footer);
      root.style.setProperty("--sidebar-2", "color-mix(in srgb, " + t.footer + " 72%, #000)");
    }
    root.style.setProperty("--admin-font-scale", FONT_SCALE_NUM[b.fontScale] || 1);
  }
  window.__APS_applyCmsTheme = applyCmsTheme;
  document.addEventListener("input", function (e) {
    var col = e.target.closest('input[type=color][data-color]');
    if (col) { var hex = $('[data-color-hex="' + col.getAttribute("data-color") + '"]'); if (hex) { hex.value = col.value.toUpperCase(); hex.dispatchEvent(new Event("input", { bubbles: true })); } }
  });

  /* --------------------------------------------------------- click wiring */
  document.addEventListener("click", function (e) {
    var t;
    if (e.target.closest("[data-sidebar-toggle]")) { $(".sidebar").classList.toggle("is-open"); return; }

    // profile dropdown
    if ((t = e.target.closest("[data-profile-toggle]"))) { e.stopPropagation(); var m = $(".profile-menu"); if (m) m.classList.toggle("is-open"); return; }
    if (e.target.closest("[data-logout]")) { localStorage.removeItem("aps_auth"); location.replace("login.html"); return; }
    var pm = $(".profile-menu.is-open"); if (pm && !e.target.closest(".profile")) pm.classList.remove("is-open");

    // ui language switch
    if ((t = e.target.closest("[data-uilang]"))) { uiLang = t.getAttribute("data-uilang"); localStorage.setItem("aps_ui_lang", uiLang); applyLang(); return; }

    if ((t = e.target.closest(".nav-parent__toggle"))) { e.preventDefault(); t.closest(".nav-parent").classList.toggle("is-open"); return; }

    // section controls
    if ((t = e.target.closest(".sec-btn"))) {
      e.stopPropagation();
      var block = t.closest(".section-block"), cont = t.closest("[data-sections]"), act = t.getAttribute("data-sec");
      if (act === "up" || act === "down") {
        var order = domOrder(cont), k = block.getAttribute("data-section"), idx = order.indexOf(k), j = act === "up" ? idx - 1 : idx + 1;
        if (j < 0 || j >= order.length) return;
        order.splice(idx, 1); order.splice(j, 0, k); S.setArray(cont.getAttribute("data-sections") + ".order", order);
        renderSections(cont); setDirty(true); return;
      }
      if (act === "hide") {
        var base = cont.getAttribute("data-sections") + ".sections." + block.getAttribute("data-section");
        S.set(base + ".hidden", null, !S.get(base + ".hidden")); renderSections(cont); setDirty(true); toast(S.get(base + ".hidden") ? "اتخفى من الموقع" : "ظهر على الموقع"); return;
      }
      if (act === "del") {
        apsConfirm("حذف هذا القسم من الصفحة؟ (المحتوى بيتحفظ ويمكن إضافته تاني)").then(function (ok) {
          if (!ok) return;
          var ord = domOrder(cont).filter(function (x) { return x !== block.getAttribute("data-section"); });
          S.setArray(cont.getAttribute("data-sections") + ".order", ord); renderSections(cont); setDirty(true); toast("اتحذف القسم");
        });
        return;
      }
    }
    if ((t = e.target.closest("[data-addsec-toggle]"))) { var menu = $(".addsec__menu", t.closest(".addsec")); if (menu) menu.hidden = !menu.hidden; return; }
    if ((t = e.target.closest("[data-addsec]"))) {
      var c2 = t.closest("[data-sections]"), ord2 = domOrder(c2); ord2.push(t.getAttribute("data-addsec"));
      S.setArray(c2.getAttribute("data-sections") + ".order", ord2); renderSections(c2); setDirty(true); toast("اتضاف القسم"); return;
    }

    var head = e.target.closest(".section-block__head");
    if (head && !e.target.closest(".section-block__tools")) { head.parentElement.classList.toggle("is-open"); return; }

    if ((t = e.target.closest(".tab"))) {
      var grp = t.closest(".tabs"); $all(".tab", grp).forEach(function (x) { x.classList.remove("is-active"); }); t.classList.add("is-active");
      var nm = t.getAttribute("data-tab"); if (nm) $all("[data-tabpanel]").forEach(function (p) { p.hidden = p.getAttribute("data-tabpanel") !== nm; }); return;
    }
    if ((t = e.target.closest("[data-repeat-move]"))) {
      var mp = t.getAttribute("data-rm-path"), mi = parseInt(t.getAttribute("data-rm-index"), 10);
      var mj = mi + (t.getAttribute("data-repeat-move") === "up" ? -1 : 1);
      var ma = S.getArray(mp); if (mj < 0 || mj >= ma.length) return;
      var tmp = ma[mi]; ma[mi] = ma[mj]; ma[mj] = tmp; S.setArray(mp, ma);
      if (mp === "settings.social") renderSocial(); else renderRepeater($('[data-repeat="' + mp + '"]'));
      setDirty(true); return;
    }
    if ((t = e.target.closest("[data-repeat-add]"))) {
      var ap = t.getAttribute("data-repeat-add"), cn = $('[data-repeat="' + ap + '"]'); var a = S.getArray(ap); a.push(EMPTY[cn.getAttribute("data-repeat-tpl")]()); S.setArray(ap, a); renderRepeater(cn); refreshCompleteness(); setDirty(true); toast("تمت الإضافة"); return;
    }
    if ((t = e.target.closest("[data-repeat-del]"))) {
      var dp = t.getAttribute("data-repeat-del"), ix = parseInt(t.getAttribute("data-repeat-index"), 10); var da = S.getArray(dp); da.splice(ix, 1); S.setArray(dp, da);
      if (dp === "settings.social") renderSocial(); else renderRepeater($('[data-repeat="' + dp + '"]'));
      refreshCompleteness(); setDirty(true); toast("تم الحذف"); return;
    }
    if (e.target.closest("[data-save]")) { save(); return; }
    if (e.target.closest("[data-discard]")) {
      var doDiscard = function () { S.reload(); $all("[data-sections]").forEach(renderSections); $all("[data-repeat]").forEach(function (c) { if (!c.closest("[data-sections]")) renderRepeater(c); }); renderPartners(); hydrate(); applyColorInputs(); refreshIconViews(); fillDashboard(); $all(".is-error").forEach(function (x) { x.classList.remove("is-error"); }); setDirty(false); toast("اترجعت آخر نسخة محفوظة"); };
      if (!dirty) doDiscard(); else apsConfirm("تجاهل كل التغييرات غير المحفوظة؟").then(function (ok) { if (ok) doDiscard(); });
      return;
    }
    if ((t = e.target.closest("[data-preview]"))) { e.preventDefault(); if (!save(true)) return; window.open("preview.html?page=" + t.getAttribute("data-preview"), "aps_preview"); toast("تم الحفظ — فتح المعاينة"); return; }
    if (e.target.closest("[data-reset]")) { apsConfirm("استرجاع القيم الافتراضية؟").then(function (ok) { if (!ok) return; S.reset(); $all("[data-sections]").forEach(renderSections); renderPartners(); hydrate(); applyColorInputs(); refreshIconViews(); fillDashboard(); setDirty(false); toast("اترجعت الافتراضية"); }); return; }
    // restore THIS page's content to the approved factory defaults (server-side)
    if ((t = e.target.closest("[data-factory-reset]"))) {
      var scope = t.getAttribute("data-factory-reset");
      apsConfirm("عودة لمحتوى هذه الصفحة الأصلي المعتمد؟\nده هيلغي كل تعديلاتك على الصفحة دي ويرجّعها زي البداية.").then(function (ok) {
        if (!ok) return;
        try {
          var fx = new XMLHttpRequest();
          fx.open("POST", "/cms/api/factory-reset/", false);
          fx.setRequestHeader("Content-Type", "application/json");
          fx.setRequestHeader("X-CSRFToken", (window.__APS_CSRF__ || ""));
          fx.setRequestHeader("ngrok-skip-browser-warning", "1");
          fx.send(JSON.stringify({ scope: scope }));
          if (fx.status >= 200 && fx.status < 300 && fx.responseText.indexOf('"ok": true') >= 0) {
            toast("اترجعت النسخة الأصلية"); setTimeout(function () { location.reload(); }, 700);
          } else { toast("تعذّر الإرجاع — تأكد من تسجيل الدخول والاتصال", false); }
        } catch (err) { toast("تعذّر الإرجاع", false); }
      });
      return;
    }
    // social: add network
    if (e.target.closest("[data-social-add]")) {
      var sarr = S.getArray("settings.social");
      sarr.push({ name: "", url: "", icon: "globe.svg" });
      S.setArray("settings.social", sarr); renderSocial(); setDirty(true); toast("اتضافت شبكة جديدة"); return;
    }

    // divisions: add / delete
    if (e.target.closest("[data-division-add]")) {
      var nid = "d" + Date.now().toString(36);
      S.set("divisions." + nid, null, {
        name: { en: "New Division", ar: "قسم جديد" }, slug: "/new-division", status: "draft", updated: "الآن",
        sections: {
          banner: { subtitle: { en: "", ar: "" } },
          about: { title: { en: "", ar: "" }, body: { en: "", ar: "" } },
          systems: { title: { en: "", ar: "" }, subtitle: { en: "", ar: "" } },
          projects: { title: { en: "Our Projects", ar: "مشاريعنا" }, items: [] },
          contact: { phone: "", site: "", email: "" }
        }
      });
      S.save();
      location.href = "division-edit.html?div=" + nid; return;
    }
    if ((t = e.target.closest("[data-division-del]"))) {
      var did = t.getAttribute("data-division-del");
      var dnm = S.get("divisions." + did + ".name", uiLang) || S.get("divisions." + did + ".name", "en");
      apsConfirm('حذف قسم "' + dnm + '" نهائياً؟ كل محتواه هيتمسح.').then(function (ok) {
        if (!ok) return;
        S.removeKey("divisions." + did); S.save();
        renderDivisionsPage(); renderNavDivisions(); renderPagesRows(); fillDashboard();
        toast("اتحذف القسم");
      });
      return;
    }

    // partners: add / delete
    if (e.target.closest("[data-partner-add]")) {
      var pfi = document.createElement("input"); pfi.type = "file"; pfi.accept = "image/svg+xml,image/png,image/jpeg,image/webp,.svg";
      pfi.addEventListener("change", function () {
        var file = pfi.files[0]; if (!file) return;
        var push = function (url) {
          var arr = S.getArray("partners.items");
          arr.push({ name: file.name.replace(/\.[^.]+$/, ""), img: url });
          S.setArray("partners.items", arr);
          renderPartners(); fillDashboard(); setDirty(true);
          toast("اتضاف الشريك — عدّل الاسم واضغط حفظ");
        };
        if (file.size <= 5 * 1024 * 1024) { var r = new FileReader(); r.onload = function () { push(r.result); }; r.readAsDataURL(file); }
        else { toast("اللوجو أكبر من 400KB — اختر ملف أصغر", false); }
      });
      pfi.click(); return;
    }
    if ((t = e.target.closest("[data-partner-del]"))) {
      var pdelIdx = parseInt(t.getAttribute("data-partner-del"), 10);
      apsConfirm("حذف هذا الشريك من شريط الموقع؟").then(function (ok) {
        if (!ok) return;
        var parr = S.getArray("partners.items"); parr.splice(pdelIdx, 1);
        S.setArray("partners.items", parr);
        renderPartners(); fillDashboard(); setDirty(true); toast("اتحذف الشريك");
      });
      return;
    }

    // replace an icon (small svg/png -> persisted as data URL) or a photo
    var rep = e.target.closest("[data-icon-replace],[data-img-replace]");
    if (rep) {
      var isIcon = rep.hasAttribute("data-icon-replace");
      var rpath = rep.getAttribute(isIcon ? "data-icon-replace" : "data-img-replace");
      var fi = document.createElement("input"); fi.type = "file";
      fi.accept = isIcon ? "image/svg+xml,image/png,image/jpeg,image/webp,.svg" : "image/*";
      fi.addEventListener("change", function () {
        var file = fi.files[0]; if (!file) return;
        var done = function (url, persisted) {
          if (rpath) {
            if (persisted) S.set(rpath, null, url);
            var view = $('[data-icon-view="' + rpath + '"]'); if (view) view.src = url;
            if (persisted) setDirty(true);
            toast(persisted ? "اتبدّلت — اضغط حفظ لتثبيتها" : "اتبدّلت للمعاينة (الملف كبير — هيترفع للسيرفر في مرحلة الربط)");
          } else {
            // media-library tile (no bound field): visual swap demo
            var tile = rep.closest(".media-tile"); var im = tile && tile.querySelector(".media-tile__img");
            if (im) { if (im.tagName === "IMG") im.src = url; else im.style.backgroundImage = "url(" + url + ")"; }
            toast("اتبدّلت الصورة (معاينة) — في النسخة النهائية بتتكتب فوق الملف على السيرفر");
          }
        };
        if (file.size <= 5 * 1024 * 1024) { var r = new FileReader(); r.onload = function () { done(r.result, !!rpath); }; r.readAsDataURL(file); }
        else done(URL.createObjectURL(file), false);
      });
      fi.click(); return;
    }

    // profile save
    if (e.target.closest("[data-profile-save]")) {
      var prof = { name: ($("#pfName") || {}).value, email: ($("#pfEmail") || {}).value, phone: ($("#pfPhone") || {}).value };
      localStorage.setItem("aps_profile", JSON.stringify(prof));
      var p1 = ($("#pfPass1") || {}).value, p2 = ($("#pfPass2") || {}).value;
      if (p1 || p2) { if (p1 !== p2) { toast("كلمتا المرور غير متطابقتين", false); return; } toast("اتغيّرت كلمة المرور واتحفظ الملف الشخصي"); }
      else toast("اتحفظ الملف الشخصي");
      return;
    }
  });

  /* ---------------------------------------------------- division editor */
  function initDivision() {
    if (!$("[data-div-title]")) return;
    var div = new URLSearchParams(location.search).get("div") || "sps";
    var allDivs = S.all().divisions || {};
    if (!allDivs[div]) div = Object.keys(allDivs)[0];
    var ATTRS = ["data-field", "data-repeat", "data-completeness", "data-preview", "data-sections", "data-factory-reset"];
    $all("[data-field],[data-repeat],[data-completeness],[data-preview],[data-sections],[data-factory-reset]").forEach(function (el) {
      ATTRS.forEach(function (a) { var v = el.getAttribute(a); if (v && v.indexOf("@") >= 0) el.setAttribute(a, v.replace(/@div/g, "divisions." + div).replace(/@id/g, div)); });
    });
    var nmAr = S.get("divisions." + div + ".name", "ar"), nmEn = S.get("divisions." + div + ".name", "en");
    var name = (uiLang === "ar" ? (nmAr || nmEn) : (nmEn || nmAr)) || div;
    $all("[data-div-title]").forEach(function (e) { e.textContent = name; e.setAttribute("dir", "auto"); });
    document.title = "تعديل: " + name + " — لوحة تحكم APS";
    $all("[data-div-slug]").forEach(function (e) { e.textContent = S.get("divisions." + div + ".slug"); });
    var draft = S.get("divisions." + div + ".status") === "draft";
    $all("[data-div-status]").forEach(function (e) { e.className = "badge " + (draft ? "badge--amber" : "badge--green"); e.textContent = draft ? "مسودة" : "منشور"; });
    $all(".sidebar__nav .is-active").forEach(function (e) { e.classList.remove("is-active"); });
    $all(".sidebar__nav .nav-parent.is-open").forEach(function (e) { e.classList.remove("is-open"); });
    var link = $('.sidebar__nav a[href*="div=' + div + '"]'); if (link) { link.classList.add("is-active"); var par = link.closest(".nav-parent"); if (par) par.classList.add("is-open"); }
  }

  /* divisions are data-driven: nav group, cards page, pages list, add/delete */
  var EDIT_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4z"/></svg>';
  var CHEV_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
  var DIV_SUBS = [["البانر", "Banner", "banner"], ["عن القسم", "About", "about"], ["Systems & Solutions", "Systems & Solutions", "systems"], ["مشاريعنا", "Our Projects", "projects"], ["التواصل", "Contact", "contact"]];
  function divName(d) { return '<span data-i18n="' + esc(d.name.en) + '" dir="auto">' + esc(d.name.ar || d.name.en) + '</span>'; }
  function renderNavDivisions() {
    var listLink = $('.sidebar__nav a[href="divisions.html"]'); if (!listLink) return;
    var group = listLink.closest(".sidebar__group");
    $all(".nav-parent", group).forEach(function (el) { el.remove(); });
    $all("a.nav-item", group).forEach(function (el) { if ((el.getAttribute("href") || "").indexOf("division-edit.html") === 0) el.remove(); });
    var layers = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>';
    var html = Object.keys(S.all().divisions || {}).map(function (id) {
      var d = S.all().divisions[id], href = "division-edit.html?div=" + id;
      var subs = DIV_SUBS.map(function (x) { return '<a class="nav-subitem" href="' + href + '#' + x[2] + '">' + L(x[0], x[1]) + '</a>'; }).join("");
      return '<div class="nav-parent"><a class="nav-item" href="' + href + '">' + layers + divName(d) +
        '<span class="nav-parent__toggle">' + CHEV_SVG + '</span></a><div class="nav-sub">' + subs + '</div></div>';
    }).join("");
    group.insertAdjacentHTML("beforeend", html);
  }
  function renderDivisionsPage() {
    var c = $("[data-divisions]"); if (!c) return;
    var divs = S.all().divisions || {};
    c.innerHTML = Object.keys(divs).map(function (id) {
      var d = divs[id], draft = d.status === "draft";
      return '<div class="card"><div class="card__body">' +
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px"><span class="stat__icon">' + secIcon("layers") + '</span>' +
        '<span class="badge ' + (draft ? "badge--amber" : "badge--green") + '">' + (draft ? L("مسودة", "Draft") : L("منشور", "Published")) + '</span></div>' +
        '<h3 style="font-size:16px;font-weight:700">' + divName(d) + '</h3>' +
        '<p class="table__sub" style="margin-top:2px" dir="ltr">' + esc(d.slug) + '</p>' +
        '<div style="display:flex;gap:8px;margin-top:16px;flex-wrap:wrap">' +
        '<a class="btn btn--ghost btn--sm" href="division-edit.html?div=' + id + '">' + EDIT_SVG + ' ' + L("تعديل", "Edit") + '</a>' +
        '<a class="btn btn--ghost btn--sm" href="preview.html?page=division&div=' + id + '" target="aps_preview">' + L("معاينة", "Preview") + '</a>' +
        '<button type="button" class="btn btn--danger btn--sm" data-division-del="' + id + '" style="margin-inline-start:auto">' + L("حذف", "Delete") + '</button>' +
        '</div></div></div>';
    }).join("");
    applyLang();
  }
  function renderPagesRows() {
    var tb = $("[data-pages-tbody]"); if (!tb) return;
    $all("tr[data-div-row]", tb).forEach(function (r) { r.remove(); });
    Object.keys(S.all().divisions || {}).forEach(function (id) {
      var d = S.all().divisions[id], draft = d.status === "draft";
      var tr = document.createElement("tr");
      tr.setAttribute("data-div-row", id);
      tr.innerHTML = '<td><a class="table__title" href="division-edit.html?div=' + id + '">' + divName(d) + '</a><div class="table__sub" dir="ltr">' + esc(d.slug) + '</div></td>' +
        '<td><span class="badge badge--gray">' + L("قسم", "Division") + '</span></td>' +
        '<td><span class="badge ' + (draft ? "badge--amber" : "badge--green") + '">' + (draft ? L("مسودة", "Draft") : L("منشور", "Published")) + '</span></td>' +
        '<td><div class="row-actions"><a class="icon-btn" href="division-edit.html?div=' + id + '" title="تعديل">' + EDIT_SVG + '</a></div></td>';
      tb.appendChild(tr);
    });
    applyLang();
  }

  function fillDashboard() {
    $all("[data-stat='faq']").forEach(function (f) { f.textContent = S.getArray("faq.items").length; });
    $all('.sidebar__nav a[href="partners.html"] .nav-item__badge').forEach(function (b) { b.textContent = S.getArray("partners.items").length; });
    $all("[data-stat='divs']").forEach(function (f) { f.textContent = Object.keys(S.all().divisions || {}).length; });
  }

  /* -------------------------------------------------------- partners list */
  function renderPartners() {
    var c = $("[data-partners]"); if (!c) return;
    var items = S.getArray("partners.items");
    c.innerHTML = items.map(function (it, i) {
      return '<div class="media-tile">' +
        '<img class="media-tile__img" style="object-fit:contain;padding:14px;background:#fff" src="' + esc(imgSrc(it.img)) + '" data-icon-view="partners.items.' + i + '.img" alt="" />' +
        '<div class="media-tile__meta">' +
        '<input class="input" style="margin-bottom:8px;padding:8px 10px;font-size:13px" dir="ltr" data-field="partners.items.' + i + '.name" placeholder="Partner name" />' +
        '<div style="display:flex;gap:8px">' +
        '<button type="button" class="btn btn--ghost btn--sm" style="flex:1" data-icon-replace="partners.items.' + i + '.img">' + L("استبدال", "Replace") + '</button>' +
        '<button type="button" class="btn btn--danger btn--sm" data-partner-del="' + i + '">' + L("حذف", "Delete") + '</button>' +
        '</div></div></div>';
    }).join("") +
      '<button type="button" class="media-tile media-tile--add" data-partner-add>' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
      '<span>' + L("إضافة شريك", "Add partner") + '</span></button>';
    hydrate(c); refreshIconViews(); applyLang();
  }

  /* social networks: managed list (add / edit / delete / reorder) */
  function renderSocial() {
    var c = $("[data-social]"); if (!c) return;
    var items = S.getArray("settings.social");
    c.innerHTML = items.map(function (it, i) {
      return '<div class="repeat-item"><span class="repeat-item__num">' + (i + 1) + '</span><div class="repeat-item__body">' +
        '<div class="field-row">' +
        '<div class="field"><label>' + L("الاسم", "Name") + '</label><input class="input" dir="ltr" data-field="settings.social.' + i + '.name" placeholder="LinkedIn" /></div>' +
        '<div class="field"><label>' + L("الرابط", "URL") + '</label><input class="input" dir="ltr" data-field="settings.social.' + i + '.url" placeholder="https://" /></div></div>' +
        iconCtl(L("الأيقونة", "Icon"), "settings.social." + i + ".icon", it.icon) +
        '</div>' + rTools("settings.social", i, items.length) + '</div>';
    }).join("");
    hydrate(c); refreshIconViews(); applyLang();
  }

  /* profile page */
  function initProfile() {
    if (!$("#pfName")) return;
    try {
      var p = JSON.parse(localStorage.getItem("aps_profile") || "null");
      if (p) { $("#pfName").value = p.name || $("#pfName").value; $("#pfEmail").value = p.email || $("#pfEmail").value; $("#pfPhone").value = p.phone || ""; }
    } catch (err) {}
  }

  /* restore persisted uploaded images (logo, icons saved as data URLs) */
  function refreshIconViews() {
    $all("img[data-icon-view]").forEach(function (im) {
      var v = S.get(im.getAttribute("data-icon-view"));
      if (/^(data:|blob:)/.test(v || "")) im.src = v;
    });
  }

  /* open + scroll to the section in the URL hash (sidebar sub-links) */
  function gotoHash() {
    var k = location.hash.replace("#", ""); if (!k) return;
    var sb = document.getElementById(k); if (!sb || !sb.classList.contains("section-block")) return;
    sb.classList.add("is-open");
    setTimeout(function () { sb.scrollIntoView({ behavior: "smooth", block: "start" }); }, 80);
  }
  window.addEventListener("hashchange", gotoHash);

  /* ------------------------------------------------------------------ init */
  renderNavDivisions();
  initDivision();
  renderSocial();
  initProfile();
  renderPartners();
  renderDivisionsPage();
  renderPagesRows();
  $all("[data-sections]").forEach(renderSections);
  $all("[data-repeat]").forEach(function (c) { if (!c.closest("[data-sections]")) renderRepeater(c); });
  hydrate();
  applyBrand(); applyColorInputs(); applyCmsTheme(); fillDashboard();
  refreshIconViews();
  applyLang();
  setDirty(false);
  gotoHash();
})();
