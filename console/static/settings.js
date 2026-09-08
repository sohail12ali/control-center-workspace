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

  /* Model providers — which model answers, and where it runs.

     Separate from "Agent CLIs" above because they are a different kind of
     thing with different failure modes: a CLI needs a binary on PATH, a hosted
     provider needs a key, a local runtime needs a server that is running. One
     "not installed" for all three was the console's old answer and it sent
     people to fix the wrong thing.

     This panel writes SERVER state, and one thing it deliberately does not
     write is agents.toml. That file is a document — two hundred lines of
     comments explaining why the ollama row needs a tool-capable model, what LM
     Studio means by "loaded" — and a TOML round-trip would delete every word.
     Your choices go to console/.cache/agents/providers.json instead, which is
     gitignored, so whether you run Ollama never lands in anyone else's diff. */
  function providers(repaint) {
    var body = C.el("div", {}, [C.skeleton(3)]);
    var adding = false;

    function save(patch, done) {
      C.post("/api/agents/providers", patch)
        .then(function (d) {
          C.toast("Saved", "ok");
          paintRows(d.providers || []);
          if (done) done();
        })
        .catch(function (err) { C.toast(err.message, "err"); load(); });
    }

    function row(p) {
      var toggle = C.el("input", {
        type: "checkbox", "aria-label": "Use " + p.label,
        onchange: function (e) {
          var patch = { enabled: {} };
          patch.enabled[p.id] = e.target.checked;
          save(patch);
        },
      });
      toggle.checked = !!p.enabled;

      var refresh = C.el("button", {
        class: "btn sm",
        title: p.available
          ? "Ask " + p.label + " for its current model list"
          : "Reachable providers only — see the reason on the left",
        onclick: function (e) {
          var btn = e.currentTarget;
          btn.disabled = true;
          btn.textContent = "Fetching…";
          C.post("/api/agents/models/refresh", { backend: p.id })
            .then(function (d) {
              if (d.error) C.toast(d.error, "err");
              else C.toast(p.label + ": " + d.count + " models cached", "ok");
              load();
            })
            .catch(function (err) { C.toast(err.message, "err"); load(); });
        },
      }, ["Refresh models"]);
      refresh.disabled = !p.available;

      /* Why the state line is worth its space: "unusable" alone sends someone
         reading source. "nothing is listening on 127.0.0.1:11434 — is the
         server running?" does not. */
      var state = !p.enabled
        ? (p.base_url + (p.notes ? " · " + p.notes : ""))
        : (p.available
            ? p.base_url + (p.key_env
                ? " · " + p.key_env + (p.has_key ? " is set" : " is NOT set")
                : " · no key needed")
            : (p.reason || "unavailable"));

      return C.el("div", { class: "setrow" }, [
        C.icon(p.is_local ? "cpu" : "external"),
        C.el("div", { class: "settext" }, [
          C.el("b", {}, [
            p.label,
            p.is_local ? C.el("span", { class: "chip ok", style: "margin-left:6px" },
              ["local"]) : null,
            p.custom ? C.el("span", { class: "chip", style: "margin-left:6px" },
              ["yours"]) : null,
          ]),
          C.el("span", { text: state }),
        ]),
        p.enabled
          ? C.chip(p.available ? "ready" : "unusable", p.available ? "ok" : "warn")
          : null,
        p.enabled ? refresh : null,
        p.custom ? C.el("button", {
          class: "btn sm", title: "Remove this provider",
          onclick: function () { save({ remove: p.id }); },
        }, [C.icon("trash")]) : null,
        C.el("label", { class: "switch" }, [
          toggle, C.el("span", { class: "track" }), C.el("span", { class: "knob" }),
        ]),
      ]);
    }

    /* Add your own: anything that speaks the OpenAI chat API. A key, if it
       needs one, is named — never pasted: the value belongs in the workspace
       .env, and nothing here should be the first file in this project to hold
       a secret. */
    function addForm() {
      var id = C.el("input", { type: "text", placeholder: "id (e.g. work-vllm)",
                               "aria-label": "Provider id" });
      var label = C.el("input", { type: "text", placeholder: "Label",
                                  "aria-label": "Provider label" });
      var url = C.el("input", { type: "text", style: "min-width:16em",
                                placeholder: "http://host:port/v1",
                                "aria-label": "Base URL" });
      var keyEnv = C.el("input", { type: "text", placeholder: "KEY_ENV_VAR (optional)",
                                   "aria-label": "Key environment variable name" });
      var result = C.el("div", { class: "muted", style: "font-size:11.5px" });

      var test = C.el("button", {
        class: "btn sm",
        // Before saving, deliberately: adding it and finding out on the first
        // turn is how a typo in a port number costs an afternoon.
        onclick: function () {
          result.textContent = "Testing…";
          C.post("/api/agents/providers/probe",
                 { base_url: url.value, api_key_env: keyEnv.value })
            .then(function (d) {
              result.textContent = d.ok
                ? "answering — " + (d.count || 0) + " models"
                  + (d.models && d.models.length ? ": " + d.models.slice(0, 3).join(", ") : "")
                : d.reason || "no answer";
            })
            .catch(function (err) { result.textContent = err.message; });
        },
      }, ["Test"]);

      var add = C.el("button", {
        class: "btn sm primary",
        onclick: function () {
          var custom = { id: id.value, base_url: url.value };
          if (label.value.trim()) custom.label = label.value;
          if (keyEnv.value.trim()) custom.api_key_env = keyEnv.value;
          save({ custom: custom }, function () {
            var on = { enabled: {} };
            on[String(id.value || "").trim().toLowerCase()] = true;
            save(on, function () { adding = false; load(); });
          });
        },
      }, ["Add"]);

      return C.el("div", { class: "setrow", style: "flex-wrap:wrap" }, [
        C.el("div", { class: "settext" }, [
          C.el("b", { text: "Add a provider" }),
          C.el("span", { text: "any endpoint that speaks the OpenAI chat API — "
                               + "vLLM, llama.cpp, a hosted gateway" }),
        ]),
        C.el("div", { class: "setctl" }, [id, label, url, keyEnv, test, add]),
        result,
      ]);
    }

    function paintRows(rows) {
      C.clear(body);
      rows.forEach(function (p) { body.appendChild(row(p)); });
      if (adding) {
        body.appendChild(addForm());
      } else {
        body.appendChild(C.el("div", { class: "row", style: "margin-top:9px" }, [
          C.el("button", {
            class: "btn sm",
            onclick: function () { adding = true; paintRows(rows); },
          }, [C.icon("cpu"), "Add a provider"]),
        ]));
      }
    }

    function load() {
      C.get("/api/agents/providers")
        .then(function (d) { paintRows(d.providers || []); })
        .catch(function (err) { C.clear(body).appendChild(C.errbox(err)); });
    }
    load();

    return C.panel("Model providers", [
      C.el("p", { class: "muted", style: "margin-bottom:4px" }, [
        "Switch one on to use it in the composer and as the Assistant's "
        + "backend. Stored for THIS machine in ",
        C.el("code", {}, ["console/.cache/agents/providers.json"]),
        " — the committed ", C.el("code", {}, ["agents.toml"]),
        " keeps stating the defaults, comments and all. A key is named, never "
        + "pasted: put its value in the workspace ",
        C.el("code", {}, [".env"]), ".",
      ]),
      body,
    ], null, { icon: "cpu" });
  }

  /* Composer — how the message box behaves. Browser-local, like the switches
     above: these are view preferences, not deployment decisions. */
  function composer(repaint) {
    function toggle(key, dflt, label, hint) {
      var on = C.prefs.get(key, dflt);
      var input = C.el("input", {
        type: "checkbox", "aria-label": label,
        onchange: function (e) { C.prefs.set(key, e.target.checked); repaint(); },
      });
      input.checked = !!on;
      return C.el("div", { class: "setrow" }, [
        C.el("div", { class: "settext" }, [
          C.el("b", { text: label }), C.el("span", { text: hint }),
        ]),
        C.el("label", { class: "switch" }, [
          input, C.el("span", { class: "track" }), C.el("span", { class: "knob" }),
        ]),
      ]);
    }

    return C.panel("Composer", [
      C.el("p", { class: "muted", style: "margin-bottom:4px" }, [
        "Type ", C.el("code", {}, ["/"]), " for a skill, ",
        C.el("code", {}, ["@"]), " for an agent, ", C.el("code", {}, ["#"]),
        " for a file. A trigger only opens the menu at the start of a word, so ",
        C.el("code", {}, ["and/or"]), " and ", C.el("code", {}, ["#1234"]),
        " are left alone — and a reference that names nothing real is sent as ",
        "plain text rather than as an error.",
      ]),
      toggle("pickSkills", true, "Skill menu (/)", "offers .claude/skills"),
      toggle("pickAgents", true, "Agent menu (@)", "offers .claude/agents"),
      toggle("pickFiles", true, "File menu (#)",
             "searches the workspace; never offers .env or other secrets"),
      toggle("chatListHidden", false, "Start with the chat list folded",
             "wide windows only — a narrow one always opens on the chat"),
    ], null, { icon: "pencil" });
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

  /* Machine state — worktrees and whether an approval can reach a phone.
     Both belong beside diagnostics: things about THIS checkout that you set
     up once and then need to confirm months later, not things you operate.

     Read-only on purpose. Adding a worktree checks out a branch; changing
     notification settings decides whether a remote run can be unblocked at
     all. Both are fine from a terminal that shows you the error, and neither
     belongs behind a button on a page with no authentication of its own. */
  function machine() {
    var body = C.el("div", {}, [C.skeleton(2)]);

    // Notification health used to be reported here too. It now has its own
    // panel, which says the same things and more; leaving a second copy would
    // guarantee the two drift the first time either is edited.
    Promise.all([
      C.get("/api/worktrees").catch(function () { return null; }),
    ]).then(function (res) {
      var wt = res[0];
      C.clear(body);
      if (!wt) {
        body.appendChild(C.empty("Ops plugin is disabled",
          "Enable the `ops` row in console/config/plugins.toml.", "sliders"));
        return;
      }

      if (wt) {
        body.appendChild(C.el("b", { text: "Worktrees" }));
        if (wt.error) {
          body.appendChild(C.el("p", { class: "muted", text: wt.error }));
        } else if (!wt.worktrees.length) {
          body.appendChild(C.el("p", { class: "muted", text: "None." }));
        } else {
          var rows = C.el("div", { class: "rows", style: "margin-top:6px" });
          wt.worktrees.forEach(function (w) {
            rows.appendChild(C.el("div", { class: "lrow" }, [
              C.chip(w.is_main ? "main" : (w.managed ? "managed" : "external"),
                     w.is_main ? "accent" : null),
              C.el("span", { class: "ltext" }, [
                C.el("b", { text: w.name || "—" }),
                C.el("span", { class: "mono", style: "font-size:11px;color:var(--ink-3)",
                               text: " " + (w.branch || "detached") }),
              ]),
              C.el("span", { class: "muted mono", style: "font-size:11px",
                             text: (w.head || "").slice(0, 7) }),
            ]));
          });
          body.appendChild(rows);
        }
        body.appendChild(C.el("p", { class: "muted", style: "margin:8px 0 0;font-size:11px" }, [
          "Add and remove with ", C.el("code", {}, ["kanban worktree"]),
          " — removing one with uncommitted work is refused there, and names what would be lost.",
        ]));
      }
    });

    return C.panel("This machine", [body], null, { icon: "wrench" });
  }

  /* Telegram — when it fires, and who may drive it.

     The split down the middle of this panel is the whole design. This page has
     no authentication of its own, and since inbound landed a Telegram tap can
     approve `run_command`. So:

       settable here   what QUIETS the bot — which events fire, quiet hours.
                       The worst a visitor can do is stop your phone buzzing.
       terminal only   anything that WIDENS it — inbound on/off, the allowlist,
                       the credentials. Granting access from an unauthenticated
                       page is the one thing that cannot be undone by reading
                       the audit log afterwards.

     The read-only half is still shown, because "why is my phone silent" is
     answered by facts this page has and the terminal does not put in front of
     you. */
  var KIND_BLURB = {
    approval: "A gated tool is waiting on you. Never silenced by quiet hours — "
            + "it denies on a timeout, so silencing it kills the run.",
    turn_end: "A run finished, or failed.",
    job_error: "A scheduled job died. Nobody is watching a 3am job.",
  };

  function telegram(repaint) {
    var body = C.el("div", {}, [C.skeleton(3)]);

    function paint(d) {
      C.clear(body);

      body.appendChild(C.el("div", { class: "row", style: "flex-wrap:wrap;margin-bottom:6px" }, [
        C.chip(d.ready ? "ready" : "not ready", d.ready ? "ok" : "warn"),
        C.chip(d.channel || "—"),
        d.inbound ? C.chip("inbound on", "accent") : C.chip("inbound off"),
        d.quiet_now ? C.chip("quiet hours", "warn") : null,
      ]));
      if (d.reason) {
        // The whole value of this row. "Not ready" sends you reading source;
        // naming the variable and the value does not.
        body.appendChild(C.el("div", { class: "errbox", style: "margin-bottom:10px",
                                       text: d.reason }));
      }

      // -- when it fires (settable: these can only quiet it) ---------------
      body.appendChild(C.el("b", { text: "When it fires" }));
      (d.kinds || []).forEach(function (kind) {
        var on = (d.events || []).indexOf(kind) !== -1;
        var box = C.el("input", { type: "checkbox" });
        box.checked = on;
        box.addEventListener("change", function () {
          var next = (d.events || []).filter(function (e) { return e !== kind; });
          if (box.checked) next.push(kind);
          save({ events: next });
        });
        body.appendChild(C.el("label", { class: "setrow" }, [
          box,
          C.el("span", { class: "settext" }, [
            C.el("b", { text: kind }),
            C.el("span", { text: KIND_BLURB[kind] || "" }),
          ]),
        ]));
      });

      // -- quiet hours ------------------------------------------------------
      function clock(id, value) {
        var input = C.el("input", {
          type: "time", "aria-label": id === "quiet_from" ? "Quiet from" : "Quiet until",
        });
        input.value = value || "";
        input.addEventListener("change", function () {
          var patch = {};
          patch[id] = input.value;
          save(patch);
        });
        return input;
      }
      var on = d.quiet_from && d.quiet_to;
      body.appendChild(C.el("div", { class: "setrow" }, [
        C.icon("clock"),
        C.el("span", { class: "settext" }, [
          C.el("b", { text: "Quiet hours" }),
          C.el("span", { text: on
            ? "turn_end and job_error are held between these times. Approvals still come through."
            : "Off — set both times to hold the informational events overnight." }),
        ]),
        // One wrapper, so the pair moves to the next line together. Split
        // across two lines they read as two unrelated fields.
        C.el("div", { class: "setctl" }, [
          clock("quiet_from", d.quiet_from),
          C.el("span", { class: "muted", text: "to" }),
          clock("quiet_to", d.quiet_to),
          on ? C.el("button", {
            class: "btn sm", title: "Turn quiet hours off",
            onclick: function () { save({ quiet_from: "", quiet_to: "" }); },
          }, [C.icon("x")]) : null,
        ]),
      ]));

      // -- who may drive it (read-only, deliberately) -----------------------
      body.appendChild(C.el("b", { style: "display:block;margin-top:12px",
                                   text: "Who may drive it" }));
      var who = d.allow_all
        ? "EVERY user — anyone who finds this bot can drive it"
        : (d.allowed_count
            ? d.allowed_count + " allowed user" + (d.allowed_count === 1 ? "" : "s")
            : "nobody — the allowlist is empty, so inbound does nothing");
      body.appendChild(C.el("div", { class: "setrow" }, [
        C.icon(d.allow_all ? "alert" : "user"),
        C.el("span", { class: "settext" }, [
          C.el("b", { text: who }),
          C.el("span", { text: d.inbound
            ? "A tap can approve any gated tool, including shell commands."
            : "Inbound is off, so buttons do nothing and only outbound messages are sent." }),
        ]),
        C.chip(d.allow_all ? "allow-all" : "fail-closed", d.allow_all ? "danger" : "ok"),
      ]));
      body.appendChild(C.el("p", { class: "muted", style: "margin:6px 0 0;font-size:11px" }, [
        "Set with ", C.el("code", {}, [d.self_user_env || "TELEGRAM_USER_ID"]),
        " or ", C.el("code", {}, [d.allowed_users_env || "TELEGRAM_ALLOWED_USERS"]),
        " in the workspace's .env, and ", C.el("code", {}, ["inbound"]),
        " in console.toml. Not editable here on purpose: this page has no "
        + "authentication, so anything that widens who can reach this machine "
        + "stays in a terminal. Check it with ",
        C.el("code", {}, ["kanban notify who"]), ".",
      ]));

      body.appendChild(C.el("div", { class: "row", style: "margin-top:10px" }, [
        C.el("button", { class: "btn sm", onclick: test }, [C.icon("send"), "Send test message"]),
        C.el("span", { class: "muted", text: "Credentials are reported present or absent, never shown." }),
      ]));
    }

    function save(patch) {
      C.post("/api/notify/prefs", patch)
        .then(function (d) { paint(merge(d.config)); C.toast("Saved", "ok"); })
        .catch(function (err) { C.toast(err.message, "err"); load(); });
    }

    // The prefs response carries the resolved config but not the read-only
    // facts, so the last full status is kept to fill them back in.
    var last = {};
    function merge(cfg) {
      var out = {};
      Object.keys(last).forEach(function (k) { out[k] = last[k]; });
      Object.keys(cfg || {}).forEach(function (k) { out[k] = cfg[k]; });
      last = out;
      return out;
    }

    function test() {
      C.post("/api/notify/test", {})
        .then(function (d) {
          C.toast(d.sent ? "Sent — check your phone" : (d.reason || "Not sent"),
                  d.sent ? "ok" : "err");
        })
        .catch(function (err) { C.toast(err.message, "err"); });
    }

    function load() {
      C.get("/api/notify")
        .then(function (d) { last = d; paint(d); })
        .catch(function (err) { C.clear(body).appendChild(C.errbox(err)); });
    }
    load();

    return C.panel("Telegram", [body], null, { icon: "send" });
  }

  /* The Assistant — the only panel here that writes SERVER state.

     Everything above is either a browser preference or read-only. These go to
     `POST /api/assistant/settings`, which stores them in the gitignored
     per-machine override rather than in the committed assistant.toml, so
     picking a backend on this laptop never lands in anyone else's diff.

     The server validates every one of them and its refusals are written for a
     human ("hands_free_wake_word needs at least two characters"), so a failed
     save shows the server's own sentence and reloads rather than guessing.
     Nothing is validated twice here — a second copy of the rules would drift
     from the ones that actually decide. */
  function assistant() {
    var body = C.el("div", {}, [C.skeleton(4)]);
    var CLICK_ACTIONS = [
      ["listen", "Talk (state-aware)"],
      ["show", "Show the window"],
      ["hands_free", "Toggle hands-free"],
    ];
    var CLICK_HINT = {
      listen: "click to talk · again to send · while it speaks, to stop it",
      show: "the plain tray behaviour, whatever the assistant is doing",
      hands_free: "arm and disarm the microphone from the icon",
    };

    function row(label, hint, control, iconName) {
      return C.el("div", { class: "setrow" }, [
        iconName ? C.icon(iconName) : null,
        C.el("div", { class: "settext" }, [
          C.el("b", { text: label }), C.el("span", { text: hint }),
        ]),
        control,
      ]);
    }

    function toggle(s, key, label, hint, iconName) {
      var input = C.el("input", { type: "checkbox", "aria-label": label });
      input.checked = !!s[key];
      input.addEventListener("change", function () {
        var patch = {}; patch[key] = input.checked; save(patch);
      });
      return row(label, hint, C.el("label", { class: "switch" }, [
        input, C.el("span", { class: "track" }), C.el("span", { class: "knob" }),
      ]), iconName);
    }

    function field(s, key, label, hint, type, iconName) {
      var input = C.el("input", { type: type || "text", "aria-label": label });
      input.value = s[key] === null || s[key] === undefined ? "" : String(s[key]);
      if (type === "number") input.style.width = "5.5em";
      // On change, not on every keystroke: each save is a POST and an audit
      // record, and a half-typed wake word is not a setting anyone meant.
      input.addEventListener("change", function () {
        var patch = {}; patch[key] = input.value; save(patch);
      });
      return row(label, hint, C.el("div", { class: "setctl" }, [input]), iconName);
    }

    function choice(s, key, label, hint, options, iconName) {
      var sel = C.el("select", { "aria-label": label });
      options.forEach(function (o) {
        var opt = C.el("option", { value: o[0], text: o[1] });
        if (String(s[key] || "") === o[0]) opt.selected = true;
        sel.appendChild(opt);
      });
      sel.addEventListener("change", function () {
        var patch = {}; patch[key] = sel.value; save(patch);
      });
      return row(label, hint, C.el("div", { class: "setctl" }, [sel]), iconName);
    }


    /* A role: which provider answers, and which of its models.

       The model is a DROPDOWN built from that provider's fetched catalogue,
       not a text box — a typed id that does not exist falls back to the
       backend's default silently, which is how you end up wondering why the
       model you chose is not the one answering.

       Each option carries what the server said about it: whether it is
       resident (LM Studio keeps ONE model loaded and swaps on demand, so
       picking an unloaded one is a ~20-second decision), and whether it claims
       tool training — which the Assistant needs for any of its verbs to work. */
    function roleRow(s, d, opts) {
        var wrap = C.el("div", {});
        var backends = [["", opts.autoLabel]].concat(
            (d.installed || []).map(function (id) { return [id, id]; }));

        var sel = C.el("select", { "aria-label": opts.label + " backend" });
        backends.forEach(function (o) {
            var opt = C.el("option", { value: o[0], text: o[1] });
            if (String(s[opts.backendKey] || "") === o[0]) opt.selected = true;
            sel.appendChild(opt);
        });
        sel.addEventListener("change", function () {
            var patch = {}; patch[opts.backendKey] = sel.value;
            // The model belonged to the old provider; keeping it would send a
            // qwen id to claude.
            patch[opts.modelKey] = "";
            save(patch);
        });

        var models = C.el("select", { "aria-label": opts.label + " model" });
        var note = C.el("span", { class: "muted", style: "font-size:11px" });

        function fillModels(rows, reportsResidency) {
            C.clear(models);
            var chosen = String(s[opts.modelKey] || "");
            models.appendChild(C.el("option", { value: "", text: "(backend default)" }));
            (rows || []).forEach(function (m) {
                var bits = [];
                if (m.loaded === true) bits.push("● loaded");
                else if (m.loaded === false) bits.push("○ not loaded");
                if (m.params) bits.push(m.params);
                if (m.tool_use === false) bits.push("no tool training");
                var opt = C.el("option", {
                    value: m.id,
                    text: m.id + (bits.length ? "  — " + bits.join(" · ") : ""),
                });
                if (m.id === chosen) opt.selected = true;
                models.appendChild(opt);
            });
            // A chosen model the catalogue does not list still has to appear,
            // or switching provider would silently drop it.
            if (chosen && !(rows || []).some(function (m) { return m.id === chosen; })) {
                var kept = C.el("option", { value: chosen, text: chosen + "  — not in the catalogue" });
                kept.selected = true;
                models.appendChild(kept);
            }
            if (!(rows || []).length) {
                note.textContent = "no catalogue yet — Refresh models on the provider above";
            } else if (!reportsResidency) {
                note.textContent = rows.length + " models · this provider does not report what is loaded";
            } else {
                note.textContent = rows.length + " models";
            }
        }

        models.addEventListener("change", function () {
            var picked = models.value;
            var row = (models._rows || []).filter(function (m) { return m.id === picked; })[0];
            // Ask ONCE, and only when we actually know it is not resident.
            // Nothing here ever loads a model; the first request does that,
            // and this is the warning that it will take a while.
            if (row && row.loaded === false) {
                var ok = window.confirm(
                    picked + " is not loaded.\n\nThe first request will load it, "
                    + "which takes roughly 5-25 seconds depending on size. "
                    + "Once loaded, replies are about a second.\n\nUse it anyway?");
                if (!ok) { models.value = String(s[opts.modelKey] || ""); return; }
            }
            var patch = {}; patch[opts.modelKey] = picked;
            save(patch);
        });

        var chosenBackend = String(s[opts.backendKey] || "");
        if (chosenBackend) {
            C.get("/api/agents/models?backend=" + encodeURIComponent(chosenBackend))
                .then(function (m) {
                    models._rows = m.models || [];
                    fillModels(m.models, m.reports_residency);
                })
                .catch(function () { fillModels([], false); });
        } else {
            fillModels([], false);
            note.textContent = "pick a provider to choose a model";
        }

        wrap.appendChild(C.el("div", { class: "setrow" }, [
            C.icon(opts.icon),
            C.el("div", { class: "settext" }, [
                C.el("b", { text: opts.label }),
                C.el("span", { text: opts.hint }),
            ]),
            C.el("div", { class: "setctl" }, [sel, models, note]),
        ]));
        return wrap;
    }

    function paint(d) {
      var s = d.settings || {};
      C.clear(body);

      body.appendChild(roleRow(s, d, {
        label: "Talk", backendKey: "backend", modelKey: "model", icon: "cpu",
        autoLabel: "Auto — first installed, local first",
        hint: "conversation, status, ticket lookups — a fast local model does "
              + "this well",
      }));
      body.appendChild(roleRow(s, d, {
        label: "Work", backendKey: "work_backend", modelKey: "work_model",
        icon: "wrench", autoLabel: "None — nothing to delegate to",
        hint: "code, builds, test runs. The talk model hands these over with "
              + "console_delegate rather than attempting them",
      }));
      body.appendChild(choice(s, "mode", "Tool mode",
        "plan refuses every write, so the Assistant could not create a ticket "
        + "or remember anything",
        [["default", "default — gated tools ask"], ["plan", "plan — read-only"]],
        "sliders"));
      body.appendChild(toggle(s, "speak", "Speak replies",
        "read finished replies aloud — the same switch as Mute replies in the "
        + "tray menu, which writes this one", "speaker"));
      body.appendChild(field(s, "speak_voice", "Voice",
        "a neural voice from desktop/tts (fetch one with "
        + "desktop/get-piper.ps1). Blank uses whichever is installed; with "
        + "none, the OS voice speaks — that is the robotic one",
        "text", "speaker"));
      body.appendChild(field(s, "speak_rate_percent", "Speaking speed",
        "percent of the voice's natural pace, 50 to 200",
        "number", "speaker"));
      body.appendChild(field(s, "reply_chars", "Spoken length",
        "characters read aloud; the full text always stays in the chat",
        "number", "speaker"));
      body.appendChild(field(s, "session_idle_minutes", "New chat after",
        "minutes of silence before the next message starts a fresh chat",
        "number", "clock"));
      body.appendChild(field(s, "ticket_prefix", "Ticket prefix",
        "how a spoken id is canonicalised — \"t dash two\" becomes T-002",
        "text", "list"));
      body.appendChild(field(s, "listen_max_seconds", "Take cap",
        "seconds — the backstop if the detector never hears you stop",
        "number", "clock"));
      body.appendChild(field(s, "listen_silence_ms", "Ends after",
        "milliseconds of quiet, so a pause to think does not cut you off",
        "number", "mic"));
      body.appendChild(field(s, "stt_model", "Speech model",
        "base.en is accurate on ticket ids; tiny.en is faster and worse at "
        + "exactly those. Fetch one with desktop/get-whisper.ps1 -Model",
        "text", "brain"));
      body.appendChild(choice(s, "tray_click_action", "Tray icon click",
        CLICK_HINT[s.tray_click_action] || CLICK_HINT.listen,
        CLICK_ACTIONS, "mic"));

      body.appendChild(C.el("b", { style: "display:block;margin-top:12px",
                                   text: "Hands-free" }));
      body.appendChild(C.el("p", { class: "muted", style: "margin:2px 0 4px;font-size:11px" }, [
        "An always-on microphone. Audio is transcribed on this machine and "
        + "thrown away unless it is addressed, so leaving it on means the room "
        + "is heard locally and forgotten — not sent anywhere.",
      ]));
      body.appendChild(toggle(s, "hands_free_require_wake", "Require the wake word",
        s.hands_free_require_wake
          ? "only what starts with the wake word is sent"
          : "OFF — every utterance is sent, which is for headphones and an "
            + "empty room", "mic"));
      body.appendChild(field(s, "hands_free_wake_word", "Wake word",
        "matched at the start of a sentence, as a whole word", "text", "mic"));
      body.appendChild(toggle(s, "hands_free_listen_while_speaking",
        "Keep listening while speaking",
        s.hands_free_listen_while_speaking
          ? "for headphones — on speakers it hears itself and answers"
          : "off: it would otherwise answer its own voice", "speaker"));
      body.appendChild(field(s, "hands_free_max_minutes", "Stops after",
        "minutes, so a microphone left on by accident does not stay on",
        "number", "clock"));

      // Read-only: a capability statement about models, reviewed in the
      // committed file rather than set per machine.
      body.appendChild(C.el("div", { class: "row", style: "flex-wrap:wrap;margin-top:10px" },
        [C.el("span", { class: "muted", style: "font-size:11px", text: "Vision models:" })].concat(
          (s.vision_models || []).length
            ? s.vision_models.map(function (m) { return C.chip(m); })
            : [C.chip("none — captures are read with OCR", "warn")])));
      body.appendChild(C.el("p", { class: "muted", style: "margin:4px 0 0;font-size:11px" }, [
        "Which model ids can actually look at a screenshot. Committed in ",
        C.el("code", {}, ["console/config/assistant.toml"]),
        " rather than set here, because it describes the models, not this machine.",
      ]));
    }

    function save(patch) {
      C.post("/api/assistant/settings", patch)
        .then(function (d) { paint({ settings: d.settings, installed: installed }); C.toast("Saved", "ok"); })
        .catch(function (err) { C.toast(err.message, "err"); load(); });
    }

    var installed = [];
    function load() {
      C.get("/api/assistant/settings")
        .then(function (d) { installed = d.installed || []; paint(d); })
        .catch(function (err) {
          C.clear(body);
          // A 404 is not a fault: the assistant plugin can be switched off.
          if (String(err.message || "").indexOf("404") !== -1) {
            body.appendChild(C.empty("Assistant not loaded",
              "Set the assistant row to enabled = true in console/config/plugins.toml.",
              "brain"));
          } else {
            body.appendChild(C.errbox(err));
          }
        });
    }
    load();

    return C.panel("Assistant", [
      C.el("p", { class: "muted", style: "margin-bottom:4px" }, [
        "Stored for THIS machine in ",
        C.el("code", {}, ["console/.cache/assistant/settings.json"]),
        " — not in the committed defaults, so your choice of backend never "
        + "shows up in anyone else's diff. The native shell reads the same "
        + "merged view.",
      ]),
      body,
    ], null, { icon: "brain" });
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
      if (hasAgents && !C.IS_STATIC) {
        kids.push(agentBackends(paint));
        kids.push(providers(paint));
        kids.push(composer(paint));
      }
      if (!C.IS_STATIC) {
        kids.push(assistant());
        kids.push(telegram(paint));
        kids.push(machine());
      }
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
