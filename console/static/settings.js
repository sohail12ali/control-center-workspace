/* Settings tab — everything here is stored in THIS BROWSER and nowhere else.

   That distinction is the one thing this page has to get across, so it is
   said in the UI and not only in a comment: hiding a tab here is a personal
   view preference, while `enabled = false` in console/config/plugins.toml is
   a committed, server-side decision that removes the routes for everyone who
   pulls the checkout. Conflating the two would let someone "turn off" the
   agents plugin by hiding its tab and believe the launch endpoint was gone.
   The Diagnostics panel exists to make that concrete: it lists what the
   server actually loaded, which no browser preference can change. */
(function (C) {
  "use strict";

  var THEMES = [
    ["system", "System", "Follow the OS setting"],
    ["light", "Light", "Cool grey ground, blue accent"],
    ["dark", "Dark", "Neutral dark ground, soft blue accent"],
    ["vsdark", "VS Dark", "VS Code's Dark Modern — #1f1f1f ground, Segoe and Cascadia, square corners"],
    ["vslight", "VS Light", "VS Code's Light Modern — white ground, Segoe and Cascadia, square corners"],
  ];

  /* The four colours every swatch shows, in paint order. */
  var SWATCH = ["--bg", "--surface", "--accent", "--ink"];

  /* Sample a theme's tokens from the live stylesheet by briefly pinning it on
     <html> and reading computed styles — swap, read, restore, all inside one
     task so no frame paints in between. Sampled rather than listed twice: a
     token edited in styles.css shows up on the chip without anyone
     remembering to update a copy. "system" samples with nothing pinned, so
     its chip shows whichever side the OS picks — which is literally what the
     setting does. */
  function sampleTheme(theme) {
    var root = document.documentElement;
    var prev = root.getAttribute("data-theme");
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    var cs = getComputedStyle(root);
    var out = {};
    SWATCH.forEach(function (n) { out[n] = cs.getPropertyValue(n).trim(); });
    if (prev === null) root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", prev);
    return out;
  }

  function swatch(theme, label, active, onPick) {
    var s = sampleTheme(theme);
    return C.el("button", {
      class: "swatch", type: "button", "aria-pressed": String(active),
      title: label, "aria-label": "Theme: " + label,
      onclick: function () { onPick(theme); },
    }, SWATCH.map(function (n) {
      return C.el("i", { style: "background:" + (s[n] || "transparent") });
    }));
  }

  function appearance(repaint) {
    var current = C.prefs.get("theme", "system");

    // Five options no longer fit beside the description in a narrow panel
    // column, so the control stacks under the text instead of sharing a row
    // (side-by-side squeezed the text to a word per line). flex-wrap is the
    // safety net for even narrower panels.
    var seg = C.el("div", { class: "seg", style: "flex-wrap:wrap" }, THEMES.map(function (t) {
      return C.el("button", {
        "aria-pressed": String(current === t[0]),
        title: t[2] || t[1],
        onclick: function () { pick(t[0]); },
      }, [t[1]]);
    }));

    var swatches = C.el("div", { class: "swatches" }, THEMES.map(function (t) {
      return swatch(t[0], t[1], current === t[0], pick);
    }));

    function pick(theme) {
      C.prefs.set("theme", theme);
      window.ConsoleApp.applyTheme(theme);
      repaint();
    }

    return C.panel("Appearance", [
      C.el("div", { class: "setrow", style: "border-bottom:0;padding-bottom:2px" }, [
        C.el("div", { class: "settext" }, [
          C.el("b", { text: "Theme" }),
          C.el("span", { text: "System follows your OS. A pinned choice overrides it on this browser only." }),
        ]),
      ]),
      C.el("div", { style: "padding:7px 4px 0" }, [seg]),
      C.el("div", { style: "padding:10px 4px 2px" }, [swatches]),
    ]);
  }

  function tabVisibility(manifest, repaint) {
    var hidden = C.prefs.get("hiddenTabs", []);
    var toggleable = manifest.filter(function (t) { return !t.always; });

    function setHidden(list) {
      C.prefs.set("hiddenTabs", list);
      window.ConsoleApp.rebuildNav();
      repaint();
    }

    var rows = toggleable.map(function (t) {
      var isHidden = hidden.indexOf(t.id) !== -1;
      var input = C.el("input", {
        type: "checkbox", "aria-label": "Show the " + t.label + " tab",
        onchange: function (e) {
          var next = C.prefs.get("hiddenTabs", []).filter(function (id) { return id !== t.id; });
          if (!e.target.checked) next.push(t.id);
          setHidden(next);
        },
      });
      input.checked = !isHidden;

      return C.el("div", { class: "setrow" }, [
        t.icon ? C.icon(t.icon) : null,
        C.el("div", { class: "settext" }, [
          C.el("b", { text: t.label }),
          C.el("span", { text: (t.group === "boards" ? "Board · " : "") + (t.needs_live ? "needs a live server" : "works in a static export") }),
        ]),
        C.el("label", { class: "switch" }, [
          input,
          C.el("span", { class: "track" }),
          C.el("span", { class: "knob" }),
        ]),
      ]);
    });

    var head = C.el("span", { class: "chip" + (hidden.length ? " warn" : " zero"),
      text: hidden.length ? hidden.length + " hidden" : "all shown" });

    return C.panel("Tabs", [
      C.el("p", { class: "muted", style: "margin-bottom:4px" }, [
        "Hide tabs you don't use. Stored in this browser (",
        C.el("code", {}, ["localStorage"]),
        "), applied immediately, and invisible to everyone else.",
      ]),
      C.el("div", {}, rows),
      hidden.length
        ? C.el("div", { class: "row", style: "margin-top:9px" }, [
            C.el("button", { class: "btn sm", onclick: function () { setHidden([]); } }, ["Show all tabs"]),
          ])
        : null,
    ], head);
  }

  /* Agent CLIs — which backends the composer offers.

     Browser-local, like the tab switches: this hides a CLI from YOUR picker.
     It does NOT remove it from the server, because that is a different
     decision made in a different place — `console/config/agents.toml` is
     committed and applies to everyone who pulls the checkout, and
     `plugins.toml` can remove the whole Agents feature. Keeping the two
     apart is deliberate; a preference must not look like a deployment
     change.

     A CLI that is not installed is shown, disabled, and says so, rather than
     hidden — "why is my CLI missing" is a worse question than "it says
     cursor-agent is not on PATH". */
  function agentBackends(repaint) {
    var body = C.el("div", {}, [C.skeleton(2)]);

    C.get("/api/agents/backends").then(function (d) {
      var backends = d.backends || [];
      C.clear(body);
      if (!backends.length) {
        body.appendChild(C.empty("No backends configured",
          "Add a [[backend]] row to console/config/agents.toml.", "cpu"));
        return;
      }

      var off = C.prefs.get("disabledBackends", []);

      function setOff(list) {
        C.prefs.set("disabledBackends", list);
        repaint();
      }

      // Refuse to leave zero usable backends: an empty composer with no
      // explanation is the worst outcome of this switch.
      var usable = backends.filter(function (b) {
        return b.installed && off.indexOf(b.id) === -1;
      });

      backends.forEach(function (b) {
        var disabled = off.indexOf(b.id) !== -1;
        var lastOne = usable.length === 1 && usable[0].id === b.id;

        var input = C.el("input", {
          type: "checkbox", "aria-label": "Offer " + b.label + " in the composer",
          onchange: function (e) {
            var next = C.prefs.get("disabledBackends", []).filter(function (id) { return id !== b.id; });
            if (!e.target.checked) next.push(b.id);
            setOff(next);
          },
        });
        input.checked = !disabled;
        if (!b.installed || lastOne) input.disabled = true;

        var why = !b.installed
          ? "not on PATH — install it or change `command` in agents.toml"
          : (b.steerable ? "steerable mid-turn" : "queue-only (one process per turn)") +
            " · " + b.transport;

        body.appendChild(C.el("div", { class: "setrow" }, [
          C.icon("cpu"),
          C.el("div", { class: "settext" }, [
            C.el("b", {}, [
              b.label,
              C.el("span", { class: "mono", style: "font-weight:400;color:var(--ink-3)", text: "  " + b.command }),
            ]),
            C.el("span", { text: why }),
          ]),
          !b.installed ? C.el("span", { class: "chip danger", text: "missing" }) : null,
          lastOne ? C.el("span", { class: "chip", title:
            "The last usable CLI can't be switched off — the composer would have nothing to offer." },
            ["last one"]) : null,
          C.el("label", { class: "switch" }, [
            input, C.el("span", { class: "track" }), C.el("span", { class: "knob" }),
          ]),
        ]));
      });

      if (off.length) {
        body.appendChild(C.el("div", { class: "row", style: "margin-top:9px" }, [
          C.el("button", { class: "btn sm", onclick: function () { setOff([]); } }, ["Offer all CLIs"]),
        ]));
      }
    }).catch(function (err) {
      C.clear(body).appendChild(C.errbox(err));
    });

    var offNow = C.prefs.get("disabledBackends", []);
    return C.panel("Agent CLIs", [
      C.el("p", { class: "muted", style: "margin-bottom:4px" }, [
        "Which CLIs the New-chat picker offers you. Stored in this browser — ",
        "to change what the server offers everyone, edit ",
        C.el("code", {}, ["console/config/agents.toml"]), ".",
      ]),
      body,
    ], C.el("span", { class: "chip" + (offNow.length ? " warn" : " zero"),
      text: offNow.length ? offNow.length + " hidden" : "all offered" }),
      { icon: "cpu" });
  }

  /* Diagnostics — the server's own answer to "what is actually loaded".
     Deliberately next to the tab switches above: one is a preference, this
     is the deployment. */
  function diagnostics() {
    var body = C.el("div", {}, [C.skeleton(3)]);
    C.get("/api/routes").then(function (d) {
      C.clear(body);
      var byPrefix = {};
      d.routes.forEach(function (r) {
        var name = r.name.split(".")[0];
        (byPrefix[name] = byPrefix[name] || []).push(r);
      });
      body.appendChild(C.el("div", { class: "row", style: "flex-wrap:wrap;margin-bottom:8px" }, [
        C.chip(d.routes.length + " routes", "accent"),
        C.chip(d.tabs.length + " tabs in the manifest"),
      ]));
      body.appendChild(C.el("div", { class: "tablewrap" }, [
        C.el("table", { class: "dt" }, [
          C.el("thead", {}, [C.el("tr", {}, [
            C.el("th", { text: "Feature" }), C.el("th", { class: "num", text: "Routes" }), C.el("th", { text: "Endpoints" }),
          ])]),
          C.el("tbody", {}, Object.keys(byPrefix).sort().map(function (k) {
            return C.el("tr", {}, [
              C.el("td", {}, [C.el("code", {}, [k])]),
              C.el("td", { class: "num", text: String(byPrefix[k].length) }),
              C.el("td", { class: "muted", style: "font-size:11px",
                text: byPrefix[k].map(function (r) { return r.name.split(".")[1]; }).join(", ") }),
            ]);
          })),
        ]),
      ]));
    }).catch(function (err) {
      C.clear(body).appendChild(C.errbox(err));
    });

    return C.panel("Loaded on the server", [
      C.el("p", { class: "muted", style: "margin-bottom:8px" }, [
        "This is what ", C.el("code", {}, ["console/config/plugins.toml"]),
        " produced — committed, shared by everyone on this checkout, and not affected by anything above. ",
        "Setting a plugin row to ", C.el("code", {}, ["enabled = false"]),
        " means its module is never imported: the routes below disappear and the tab leaves the manifest, "
        + "rather than merely being hidden.",
      ]),
      body,
    ]);
  }

  function storage(repaint) {
    var keys = [];
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k && k.indexOf("console.") === 0) keys.push(k);
      }
    } catch (e) { /* private mode: nothing stored, nothing to clear */ }

    /* The Getting-started card tells people Settings can bring it back, so
       there is an explicit control rather than making them work out that
       clearing a localStorage key is the way. */
    var restore = C.prefs.get("hideOnboarding", false)
      ? C.el("div", { class: "setrow" }, [
          C.icon("info"),
          C.el("div", { class: "settext" }, [
            C.el("b", { text: "Getting started card" }),
            C.el("span", { text: "dismissed on Overview" }),
          ]),
          C.el("button", {
            class: "btn sm",
            onclick: function () {
              C.prefs.del("hideOnboarding");
              C.toast("Setup card restored on Overview", "ok");
              repaint();
            },
          }, ["Show again"]),
        ])
      : null;

    return C.panel("Stored in this browser", [
      restore,
      keys.length
        ? C.el("div", { class: "rows" }, keys.sort().map(function (k) {
            return C.el("div", { class: "lrow" }, [
              C.el("span", { class: "mono", style: "font-size:11.5px", text: k }),
              C.el("span", { class: "ltext muted truncate", style: "font-size:11.5px",
                text: (function () { try { return localStorage.getItem(k); } catch (e) { return "?"; } })() }),
            ]);
          }))
        : C.el("div", { class: "muted", text: "Nothing stored yet — every setting is still at its default." }),
      keys.length
        ? C.el("div", { class: "row", style: "margin-top:9px" }, [
            C.el("button", {
              class: "btn sm danger",
              onclick: function () {
                keys.forEach(function (k) { try { localStorage.removeItem(k); } catch (e) { /* ignore */ } });
                window.ConsoleApp.applyTheme("system");
                window.ConsoleApp.rebuildNav();
                C.toast("Preferences reset", "ok");
                repaint();
              },
            }, ["Reset all preferences"]),
            C.el("span", { class: "muted", text: "Affects this browser only. No server data is touched." }),
          ])
        : null,
    ]);
  }

  function render(host) {
    var manifest = window.ConsoleApp.manifest();

    function paint() {
      var h = C.clear(host);
      var kids = [appearance(paint), tabVisibility(manifest, paint)];
      // Only when the Agents feature actually loaded — a switch for a plugin
      // that is off would be a control with nothing behind it.
      var hasAgents = manifest.some(function (t) { return t.id === "agents"; });
      if (hasAgents && !C.IS_STATIC) kids.push(agentBackends(paint));
      h.appendChild(C.el("div", { class: "grid" }, kids));
      h.appendChild(C.el("div", { style: "margin-top:12px" }, [storage(paint)]));
      if (!C.IS_STATIC) {
        h.appendChild(C.el("div", { style: "margin-top:12px" }, [diagnostics()]));
      }
    }

    paint();
  }

  C.tab("settings", { render: render });
})(window.Console);
