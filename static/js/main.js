/* APS Website — lightweight progressive enhancement (no dependencies).
   Phase 1 only handles the mobile navigation toggle. Keep logic minimal;
   richer interactivity can be layered in once the CMS is wired up. */
(function () {
  "use strict";

  var toggle = document.getElementById("navToggle");
  var nav = document.getElementById("mainNav");
  if (!toggle || !nav) return;

  toggle.addEventListener("click", function () {
    var open = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(open));
  });

  // Close the menu after picking a link (mobile).
  nav.addEventListener("click", function (e) {
    if (e.target.closest("a") && nav.classList.contains("is-open")) {
      nav.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
    }
  });

  // Divisions dropdown — toggle on click (works for keyboard & touch;
  // desktop also opens it on hover via CSS).
  var ddToggle = nav.querySelector(".nav-dropdown-toggle");
  var ddMenu = document.getElementById("divisionsMenu");
  if (ddToggle && ddMenu) {
    ddToggle.addEventListener("click", function () {
      var open = ddMenu.classList.toggle("is-open");
      ddToggle.setAttribute("aria-expanded", String(open));
    });

    // Close when clicking outside the dropdown.
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".has-dropdown")) {
        ddMenu.classList.remove("is-open");
        ddToggle.setAttribute("aria-expanded", "false");
      }
    });

    // Close on Escape.
    ddToggle.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        ddMenu.classList.remove("is-open");
        ddToggle.setAttribute("aria-expanded", "false");
      }
    });
  }
})();
