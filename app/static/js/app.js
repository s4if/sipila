/* Shared Sipila front-end helpers. */
(function () {
  "use strict";

  /* ---------- Sidebar drawer (mobile) ---------- */
  function openSidebar() {
    var sb = document.getElementById("appSidebar");
    var bd = document.getElementById("sidebarBackdrop");
    if (sb) sb.classList.add("open");
    if (bd) bd.classList.add("show");
  }

  function closeSidebar() {
    var sb = document.getElementById("appSidebar");
    var bd = document.getElementById("sidebarBackdrop");
    if (sb) sb.classList.remove("open");
    if (bd) bd.classList.remove("show");
  }

  /* ---------- Active-link sync ---------- *
   * The sidebar lives outside #hx_content, so HTMX content swaps do not
   * re-render it. Derive the active section from the URL and toggle
   * .active on the matching [data-nav-key] after every navigation.
   *
   * Sipila blueprints sit under /admin, /supervisor, /siswa, so the
   * meaningful segment is the second one (e.g. /admin/siswa -> siswa),
   * with /admin (or /admin/) mapping to beranda. */
  function currentNavKey() {
    var parts = location.pathname.replace(/\/+$/, "").split("/").filter(Boolean);
    if (!parts.length) return "";
    if (parts[0] === "admin") {
      return parts.length > 1 ? parts[1] : "beranda";
    }
    if (parts[0] === "supervisor") {
      return parts.length > 1 ? parts[1] : "monitor";
    }
    if (parts[0] === "siswa") {
      return "beranda";
    }
    return parts[0];
  }

  function syncSidebarActive() {
    var sidebar = document.getElementById("appSidebar");
    if (!sidebar) return;
    var key = currentNavKey();
    sidebar.querySelectorAll("[data-nav-key]").forEach(function (link) {
      link.classList.toggle("active", link.getAttribute("data-nav-key") === key);
    });
  }

  function wireSidebar() {
    var toggle = document.getElementById("sidebarToggle");
    if (toggle) {
      toggle.addEventListener("click", function () {
        var sb = document.getElementById("appSidebar");
        if (sb && sb.classList.contains("open")) closeSidebar();
        else openSidebar();
      });
    }
    var bd = document.getElementById("sidebarBackdrop");
    if (bd) bd.addEventListener("click", closeSidebar);
    var sb = document.getElementById("appSidebar");
    if (sb) {
      /* Auto-close drawer after a real navigation link is clicked (mobile). */
      sb.addEventListener("click", function (e) {
        if (e.target.closest("a[data-nav-key]")) closeSidebar();
      });
    }
    syncSidebarActive();
  }

  document.addEventListener("DOMContentLoaded", function () {
    wireSidebar();

    /* DataTables Indonesian defaults so every list page stays consistent. */
    if (window.jQuery && jQuery.fn && jQuery.fn.dataTable) {
      jQuery.extend(true, jQuery.fn.dataTable.defaults, {
        language: {
          search: "Cari:",
          lengthMenu: "Tampilkan _MENU_ data",
          info: "Menampilkan _START_ - _END_ dari _TOTAL_ data",
          infoEmpty: "Belum ada data",
          emptyTable: "Belum ada data",
          zeroRecords: "Tidak ditemukan data yang cocok",
          paginate: { previous: "Sebelumnya", next: "Selanjutnya" },
        },
      });
    }

    /* HTMX request spinner overlay. */
    var spinner = document.getElementById("hx-spinner");
    if (spinner) {
      document.addEventListener("htmx:beforeRequest", function () {
        spinner.classList.add("show");
      });
      document.addEventListener("htmx:afterRequest", function () {
        spinner.classList.remove("show");
      });
      document.addEventListener("htmx:afterSwap", function () {
        spinner.classList.remove("show");
      });
    }
  });

  /* ---------- Confirm-modal body builder (XSS-safe) ---------- *
   * Builds "<prefix><strong>{label}</strong><suffix>" without
   * innerHTML + string concatenation, so user-controlled text is
   * always inserted as inert text (textContent), never parsed as HTML. */
  window.setConfirmBody = function (targetId, prefix, label, suffix) {
    var body = document.getElementById(targetId);
    if (!body) return;
    body.innerHTML = "";
    body.appendChild(document.createTextNode(prefix));
    var strong = document.createElement("strong");
    strong.textContent = label;
    body.appendChild(strong);
    body.appendChild(document.createTextNode(suffix || ""));
  };

  /* Make HTMX swap 4xx/5xx bodies so server-side error pages actually
   * render into #hx_content instead of being silently dropped —
   * HTMX only swaps 2xx/3xx by default. */
  document.body.addEventListener("htmx:beforeSwap", function (evt) {
    var status = evt.detail.xhr.status;
    if (status === 403 || status === 404 || status >= 500) {
      evt.detail.shouldSwap = true;
      evt.detail.target = document.getElementById("hx_content");
    }
  });

  /* Re-sync the sidebar active state after HTMX content swaps. */
  document.body.addEventListener("htmx:afterSettle", syncSidebarActive);
})();
