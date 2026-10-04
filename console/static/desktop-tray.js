/* Desktop tray → JS. Loaded only for the in-shell page; no-ops in a browser.
   Emits session state to Rust (header + mute check). Actions arrive via eval
   into ConsoleAgents.trayAction — see agents.js. */
(function () {
  "use strict";

  function emitSession(backend) {
    var t = window.__TAURI__;
    if (!t || !t.event || typeof t.event.emit !== "function") return;
    var muted = true;
    try {
      if (window.ConsoleVoice && ConsoleVoice.prefs) {
        muted = !ConsoleVoice.prefs().autoRead;
      }
    } catch (e) { /* keep muted default */ }
    var label = backend && String(backend).trim() ? String(backend).trim() : "—";
    t.event.emit("desktop-session", { backend: label, muted: muted });
  }

  window.ConsoleDesktopTray = { emitSession: emitSession };
})();
