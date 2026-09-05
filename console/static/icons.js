/* Inline SVG icons. No sprite file, no icon font — the static export has to
   work from file:// with no network, and an <svg> built in JS themes itself
   via currentColor for free.

   All paths are 24x24, stroke-based, so one stroke-width reads consistently
   at every size. Add an icon by adding a key; nothing else changes. */
window.ConsoleIcons = (function () {
  "use strict";

  var P = {
    layout:     "M3 3h18v18H3z M3 9h18 M9 21V9",
    columns:    "M3 3h6v18H3z M15 3h6v18h-6z",
    scope:      "M12 3v3 M12 18v3 M3 12h3 M18 12h3 M12 8a4 4 0 100 8 4 4 0 000-8z",
    arrowRight: "M5 12h14 M13 6l6 6-6 6",
    package:    "M21 8l-9-5-9 5 9 5 9-5z M3 8v8l9 5 9-5V8",
    cpu:        "M5 5h14v14H5z M9 9h6v6H9z M9 1v3 M15 1v3 M9 20v3 M15 20v3 M1 9h3 M1 15h3 M20 9h3 M20 15h3",
    clock:      "M12 3a9 9 0 100 18 9 9 0 000-18z M12 7v5l4 2",
    chart:      "M4 20V10 M10 20V4 M16 20v-7 M22 20H2",
    list:       "M8 6h13 M8 12h13 M8 18h13 M3 6h.01 M3 12h.01 M3 18h.01",
    graph:      "M6 6a2.5 2.5 0 100 5 2.5 2.5 0 000-5z M18 4a2.5 2.5 0 100 5 2.5 2.5 0 000-5z M17 15a2.5 2.5 0 100 5 2.5 2.5 0 000-5z M8.2 9.4l7.4-2.6 M8.4 10.9l7.2 4.3",
    info:       "M12 3a9 9 0 100 18 9 9 0 000-18z M12 11v5 M12 8h.01",
    sliders:    "M4 21v-7 M4 10V3 M12 21v-9 M12 8V3 M20 21v-5 M20 12V3 M1 14h6 M9 8h6 M17 16h6",
    search:     "M11 4a7 7 0 100 14 7 7 0 000-14z M20 20l-4.2-4.2",
    x:          "M18 6L6 18 M6 6l12 12",
    winMin:     "M5 16h14",
    winMax:     "M6 6h12v12H6z",
    winRestore: "M8 8h10v10H8z M6 6h8v2 M6 6v8h2",
    chevLeft:   "M15 18l-6-6 6-6",
    chevRight:  "M9 18l6-6-6-6",
    chevDown:   "M6 9l6 6 6-6",
    folder:     "M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z",
    file:       "M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5z M14 3v5h5",
    play:       "M6 4l14 8-14 8V4z",
    stop:       "M6 6h12v12H6z",
    refresh:    "M21 12a9 9 0 11-3-6.7 M21 4v5h-5",
    check:      "M20 6L9 17l-5-5",
    alert:      "M12 3l9 16H3l9-16z M12 9v4 M12 16h.01",
    inbox:      "M3 12h5l2 3h4l2-3h5 M3 12l2.5-7h13L21 12v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6z",
    user:       "M12 12a4 4 0 100-8 4 4 0 000 8z M4 21v-1a5 5 0 015-5h6a5 5 0 015 5v1",
    filter:     "M3 5h18 M6 12h12 M10 19h4",
    external:   "M14 4h6v6 M20 4l-9 9 M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5",
    mic:        "M12 3a3 3 0 00-3 3v6a3 3 0 006 0V6a3 3 0 00-3-3z M5 11a7 7 0 0014 0 M12 18v3 M8 21h8",
    speaker:    "M11 5L6 9H3v6h3l5 4V5z M16 9a3.5 3.5 0 010 6 M19 6.5a7 7 0 010 11",
    send:       "M4 12l16-8-6 8 6 8-16-8z",
    steer:      "M12 3a9 9 0 100 18 9 9 0 000-18z M12 8l4 4-4 4-4-4 4-4z",
    queue:      "M4 6h16 M4 12h16 M4 18h10 M18 15v6 M15 18h6",
    trash:      "M4 7h16 M9 7V4h6v3 M6 7l1 13h10l1-13 M10 11v6 M14 11v6",
    brain:      "M9 4a3 3 0 00-3 3 3 3 0 00-1 5.8V16a3 3 0 003 3h1V4H9z M15 4a3 3 0 013 3 3 3 0 011 5.8V16a3 3 0 01-3 3h-1V4h0z",
    wrench:     "M14.7 6.3a4 4 0 105.4 5.4l-2-2-1.4-1.4-2-2z M13.3 7.7L4 17v3h3l9.3-9.3",
    pencil:     "M15 4l5 5L9 20H4v-5L15 4z",
    circle:     "M12 4a8 8 0 100 16 8 8 0 000-16z",
    // Priority: direction and count carry the meaning, so they stay legible
    // in monochrome and for anyone who can't separate the colours.
    prioLow:    "M12 5v11 M7 12l5 5 5-5",
    prioMed:    "M5 12h14",
    prioHigh:   "M12 19V8 M7 12l5-5 5 5",
    prioCrit:   "M12 20v-9 M7 11l5-5 5 5 M7 16l5-5 5 5",
  };

  function svg(name, cls) {
    var d = P[name];
    var el = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    el.setAttribute("class", "ico" + (cls ? " " + cls : ""));
    el.setAttribute("viewBox", "0 0 24 24");
    el.setAttribute("fill", "none");
    el.setAttribute("stroke", "currentColor");
    el.setAttribute("stroke-linecap", "round");
    el.setAttribute("stroke-linejoin", "round");
    el.setAttribute("aria-hidden", "true");
    if (!d) return el;
    d.trim().split(/\s+(?=M)/).forEach(function (seg) {
      var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", seg);
      el.appendChild(path);
    });
    return el;
  }

  function has(name) { return !!P[name]; }

  return { svg: svg, has: has, names: Object.keys(P) };
})();
