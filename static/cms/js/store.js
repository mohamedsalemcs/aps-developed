/* APS CMS — server-backed data store (Phase 4).
   DROP-IN REPLACEMENT for the designer's localStorage store.js: SAME public
   Store API and SAME bilingual {en,ar} data shape, but persistence is the
   Django backend instead of localStorage.
     - load: reads the store JSON injected server-side (#aps-store-data), built
             from the DB by /cms/api/store/ (so it's synchronous before admin.js)
     - save: synchronous CSRF'd POST to /cms/api/store/save/
   His admin.js is UNCHANGED — it only ever talks to window.Store. */
(function (global) {
  "use strict";
  var KEY = "aps_cms_v7";
  var SAVE_URL = "/cms/api/store/save/";
  var LOAD_URL = "/cms/api/store/";

  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  function bootstrap() {
    var el = global.document && global.document.getElementById("aps-store-data");
    if (el) { try { return JSON.parse(el.textContent); } catch (e) {} }
    if (global.__APS_STORE__) return clone(global.__APS_STORE__);
    return {};
  }

  function csrf() { return global.__APS_CSRF__ || ""; }

  // ngrok's free tier serves a browser-warning interstitial to requests without
  // this header; sending it guarantees our XHRs reach Django, not the warning.
  function skip(xhr) { xhr.setRequestHeader("ngrok-skip-browser-warning", "1"); }

  function serverGet() {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", LOAD_URL, false);
    skip(xhr);
    xhr.send(null);
    if (xhr.status >= 200 && xhr.status < 300) return JSON.parse(xhr.responseText);
    throw new Error("store load failed: " + xhr.status);
  }

  function serverSave(payload) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", SAVE_URL, false); // sync: admin.js saves then sometimes navigates
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.setRequestHeader("X-CSRFToken", csrf());
    skip(xhr);
    xhr.send(JSON.stringify(payload));
    // A 2xx is not enough: if the session lapsed the request is redirected to the
    // login page (also 200 HTML), so verify Django actually returned {"ok":true}.
    // Otherwise the save silently failed and we must NOT report success.
    if (xhr.status < 200 || xhr.status >= 300 || xhr.responseText.indexOf('"ok"') < 0) {
      throw new Error("store save failed: " + xhr.status);
    }
  }

  var UPLOAD_URL = "/cms/api/media/upload/";

  // Decode a data: URL to a Blob in the browser. We upload as multipart (below)
  // rather than POSTing the data URL as JSON, because Django caps a JSON request
  // body at DATA_UPLOAD_MAX_MEMORY_SIZE (2.5 MB by default) — base64 inflates an
  // image by ~33%, so a ~1.9 MB logo already exceeds it and the save fails with
  // a generic error. Multipart FILE parts are exempt from that cap, and letting
  // the browser decode also sidesteps the server's strict data-URL regex.
  function dataUrlToBlob(dataurl) {
    var m = /^data:([^;,]*)(;base64)?,([\s\S]*)$/.exec(dataurl || "");
    if (!m) return null;
    var mime = m[1] || "application/octet-stream";
    var body = m[3];
    var bytes;
    if (m[2]) { // base64
      var bin = global.atob(body);
      bytes = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    } else {    // percent-encoded text (e.g. inline SVG)
      var txt = decodeURIComponent(body);
      bytes = new Uint8Array(txt.length);
      for (var j = 0; j < txt.length; j++) bytes[j] = txt.charCodeAt(j) & 0xff;
    }
    return new Blob([bytes], { type: mime });
  }

  function uploadDataUrl(dataurl) {
    var blob = dataUrlToBlob(dataurl);
    var xhr = new XMLHttpRequest();
    xhr.open("POST", UPLOAD_URL, false);
    xhr.setRequestHeader("X-CSRFToken", csrf());
    skip(xhr);
    if (blob) {
      // ext from "image/svg+xml" -> "svg"; the server maps content_type anyway.
      var ext = ((blob.type.split("/")[1] || "bin").split("+")[0]) || "bin";
      var fd = new FormData();
      fd.append("file", blob, "upload." + ext); // browser sets the multipart boundary
      xhr.send(fd);
    } else {
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.send(JSON.stringify({ dataurl: dataurl }));
    }
    if (xhr.status >= 200 && xhr.status < 300) return JSON.parse(xhr.responseText).value;
    throw new Error("media upload failed: " + xhr.status);
  }

  // The designer's admin stores small image uploads as data: URLs in the tree.
  // Before saving, turn each into a real file and swap in its "uploads/<file>"
  // path — so his admin.js needs no edit and the public site gets real files.
  function materializeUploads(node) {
    if (Array.isArray(node)) {
      for (var i = 0; i < node.length; i++) {
        if (typeof node[i] === "string" && node[i].indexOf("data:") === 0) node[i] = uploadDataUrl(node[i]);
        else materializeUploads(node[i]);
      }
    } else if (node && typeof node === "object") {
      Object.keys(node).forEach(function (k) {
        if (typeof node[k] === "string" && node[k].indexOf("data:") === 0) node[k] = uploadDataUrl(node[k]);
        else materializeUploads(node[k]);
      });
    }
  }

  var data = bootstrap();

  function resolve(path, create) {
    var parts = String(path).split(".");
    var node = data;
    for (var i = 0; i < parts.length - 1; i++) {
      var k = parts[i];
      if (node[k] == null) {
        if (!create) return { node: null, key: parts[parts.length - 1] };
        node[k] = /^\d+$/.test(parts[i + 1]) ? [] : {};
      }
      node = node[k];
    }
    return { node: node, key: parts[parts.length - 1] };
  }

  var Store = {
    KEY: KEY,
    all: function () { return data; },
    get: function (path, lang) {
      var r = resolve(path, false); if (!r.node) return "";
      var v = r.node[r.key]; if (v == null) return "";
      if (lang && typeof v === "object") return v[lang] || "";
      return v;
    },
    set: function (path, lang, val) {
      var r = resolve(path, true);
      if (lang) {
        if (typeof r.node[r.key] !== "object" || r.node[r.key] == null) r.node[r.key] = { en: "", ar: "" };
        r.node[r.key][lang] = val;
      } else r.node[r.key] = val;
      return this;
    },
    getArray: function (path) { var v = this.get(path); return Array.isArray(v) ? v : []; },
    removeKey: function (path) { var r = resolve(path, false); if (r.node) delete r.node[r.key]; return this; },
    setArray: function (path, arr) { var r = resolve(path, true); r.node[r.key] = arr; return this; },
    save: function () { materializeUploads(data); serverSave(data); return this; },
    reload: function () { data = serverGet(); return this; },
    reset: function () { data = serverGet(); return this; }, // re-fetch server state (not factory seed)
    completeness: function (scopePath) {
      var r = resolve(scopePath, false);
      var scope = r.node ? r.node[r.key] : null; if (scope == null) return 0;
      var total = 0, filled = 0;
      (function walk(o) {
        if (o == null || typeof o !== "object") return;
        if (typeof o.en === "string" && typeof o.ar === "string") { total += 2; if (o.en.trim()) filled++; if (o.ar.trim()) filled++; return; }
        Object.keys(o).forEach(function (k) { walk(o[k]); });
      })(scope);
      return total ? Math.round((filled / total) * 100) : 100;
    }
  };
  global.Store = Store;
})(window);
