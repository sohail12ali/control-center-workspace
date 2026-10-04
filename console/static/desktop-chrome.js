/* Window chrome for the Tauri shell. No-ops in a normal browser.
   The host injects html.in-shell before this file runs. Buttons call
   window.__TAURI__.window only — no shell/fs. */
(function () {
  "use strict";

  function tauriWindow() {
    var t = window.__TAURI__;
    if (!t) return null;
    if (t.window && typeof t.window.getCurrentWindow === "function") {
      return t.window.getCurrentWindow();
    }
    if (t.webviewWindow && typeof t.webviewWindow.getCurrentWebviewWindow === "function") {
      return t.webviewWindow.getCurrentWebviewWindow();
    }
    return null;
  }

  function isInteractive(el) {
    if (!el || !el.closest) return false;
    return !!el.closest(
      "a, button, input, textarea, select, label, .tabs, .win-controls, .searchwrap, .statuspill"
    );
  }

  function isMac() {
    var p = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || "";
    return /mac/i.test(p);
  }

  var root = document.documentElement;
  var win = tauriWindow();
  if (win) root.classList.add("in-shell");
  if (!root.classList.contains("in-shell")) return;
  if (isMac()) root.classList.add("os-mac");

  var controls = document.getElementById("winControls");
  if (controls && !root.classList.contains("os-mac")) {
    controls.removeAttribute("hidden");
    if (window.ConsoleIcons) {
      var minEl = document.getElementById("winMin");
      var maxEl = document.getElementById("winMax");
      var closeEl = document.getElementById("winClose");
      if (minEl && !minEl.firstChild) minEl.appendChild(ConsoleIcons.svg("winMin"));
      if (maxEl && !maxEl.firstChild) maxEl.appendChild(ConsoleIcons.svg("winMax"));
      if (closeEl && !closeEl.firstChild) closeEl.appendChild(ConsoleIcons.svg("x"));
    }
  }

  if (!win) return;

  function setMaxIcon(maximized) {
    var btn = document.getElementById("winMax");
    if (!btn || !window.ConsoleIcons) return;
    btn.replaceChildren(ConsoleIcons.svg(maximized ? "winRestore" : "winMax"));
    btn.setAttribute("aria-label", maximized ? "Restore" : "Maximize");
    btn.title = maximized ? "Restore" : "Maximize";
  }

  function syncMax() {
    if (typeof win.isMaximized !== "function") return;
    Promise.resolve(win.isMaximized()).then(function (m) { setMaxIcon(!!m); }).catch(function () {});
  }

  var minBtn = document.getElementById("winMin");
  var maxBtn = document.getElementById("winMax");
  var closeBtn = document.getElementById("winClose");
  if (minBtn) minBtn.addEventListener("click", function () { win.minimize(); });
  if (maxBtn) maxBtn.addEventListener("click", function () {
    Promise.resolve(win.toggleMaximize()).then(syncMax).catch(function () {});
  });
  if (closeBtn) closeBtn.addEventListener("click", function () { win.close(); });

  var brand = document.querySelector(".brandrow");
  if (brand) {
    brand.addEventListener("mousedown", function (e) {
      if (e.button !== 0) return;
      if (isInteractive(e.target)) return;
      if (e.detail === 2) {
        Promise.resolve(win.toggleMaximize()).then(syncMax).catch(function () {});
        return;
      }
      if (typeof win.startDragging === "function") win.startDragging();
    });
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "F11") {
      e.preventDefault();
      Promise.resolve(win.toggleMaximize()).then(syncMax).catch(function () {});
    }
  });

  syncMax();
  window.addEventListener("resize", syncMax);
})();
