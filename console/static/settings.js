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
      C.el("div", { style: "padding:2px 4px 0" }, [seg]),
      C.el("div", { style: "padding:10px 4px 2px" }, [swatches]),
    ], null, {
      icon: "layout",
      collapse: { id: "set.appearance", open: true },
      help: "System follows your OS. A pinned choice overrides it, on this "
            + "browser only — nobody else sees it and no server state changes.",
    });
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
      C.el("div", {}, rows),
      hidden.length
        ? C.el("div", { class: "row", style: "margin-top:9px" }, [
            C.el("button", { class: "btn sm", onclick: function () { setHidden([]); } }, ["Show all tabs"]),
          ])
        : null,
    ], head, {
      icon: "columns",
      collapse: { id: "set.tabs", open: false },
      help: ["Hide tabs you don't use. Stored in this browser (",
             C.el("code", {}, ["localStorage"]),
             "), applied immediately, and invisible to everyone else."],
    });
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
     cursor-agent is not on PATH".

     API backends are NOT listed here, however much agents.toml calls them all
     backends. OpenRouter, Ollama and LM Studio have no binary: they are a URL
     and a key, they are never "on PATH", and this panel was telling them to
     install something that does not exist. They are the Model providers panel
     below, which already knows how to say "the key is not set" and has the
     switch that actually turns them on. One kind of thing per panel. */
  function agentBackends(repaint) {
    var body = C.el("div", {}, [C.skeleton(2)]);
    var chip = C.el("span", { class: "chip zero", text: "all offered" });

    C.get("/api/agents/backends").then(function (d) {
      var backends = (d.backends || []).filter(function (b) { return !b.is_api; });
      C.clear(body);
      if (!backends.length) {
        body.appendChild(C.empty("No CLIs configured",
          "Add a [[backend]] row with a `command` to console/config/agents.toml.",
          "cpu"));
        return;
      }

      var off = C.prefs.get("disabledBackends", []);

      function setOff(list) {
        C.prefs.set("disabledBackends", list);
        repaint();
      }

      // Refuse to leave zero usable CLIs: an empty composer with no
      // explanation is the worst outcome of this switch. Counted over the
      // CLIs shown here, not over every backend — an API provider switched on
      // in the panel below is not a reason to let you strand this one.
      var usable = backends.filter(function (b) {
        return b.installed && off.indexOf(b.id) === -1;
      });
      var hiddenHere = backends.filter(function (b) {
        return off.indexOf(b.id) !== -1;
      }).length;
      chip.className = "chip" + (hiddenHere ? " warn" : " zero");
      chip.textContent = hiddenHere ? hiddenHere + " hidden" : "all offered";

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
            "Your last usable CLI can't be switched off — the composer would "
            + "be left with no process-backed agent to offer." },
            ["last one"]) : null,
          C.el("label", { class: "switch" }, [
            input, C.el("span", { class: "track" }), C.el("span", { class: "knob" }),
          ]),
        ]));
      });

      if (hiddenHere) {
        body.appendChild(C.el("div", { class: "row", style: "margin-top:9px" }, [
          C.el("button", { class: "btn sm", onclick: function () {
            // Only the CLIs: a provider switched off in the panel below is a
            // different decision and this button must not undo it.
            var ids = backends.map(function (b) { return b.id; });
            setOff(C.prefs.get("disabledBackends", []).filter(function (id) {
              return ids.indexOf(id) === -1;
            }));
          } }, ["Offer all CLIs"]),
        ]));
      }
    }).catch(function (err) {
      C.clear(body).appendChild(C.errbox(err));
    });

    return C.panel("Agent CLIs", [body], chip, {
      icon: "cpu",
      collapse: { id: "set.backends", open: false },
      help: ["Command-line agents — a binary on PATH that the console "
             + "runs as a process. Which ones the New-chat picker offers you "
             + "is stored in this browser; to change what the server offers "
             + "everyone, edit ",
             C.el("code", {}, ["console/config/agents.toml"]),
             ". Hosted and local API models are in Model providers, not here."],
    });
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

    function save(patch, done, where) {
      // `where` re-points ONE shipped provider. Built here rather than by the
      // caller so the wire shape lives in one place.
      if (where && where.id) {
        patch = { where: {} };
        patch.where[where.id] = { base_url: where.base_url || "",
                                  api_key_env: where.api_key_env || "" };
      }
      C.post("/api/agents/providers", patch)
        .then(function (d) {
          C.toast("Saved", "ok");
          // Reload rather than repaint from the response: the POST answers
          // with providers only, and painting from it would drop the footer.
          load();
          if (done) done();
        })
        .catch(function (err) { C.toast(err.message, "err"); load(); });
    }

    /* Which provider's edit form is open, if any. One at a time: two open
       forms invite editing one and saving the other. */
    var editing = null;
    /* Editing a provider means two different things depending on where its row
       came from, and the form says which.

       A provider YOU added is yours to rewrite — label, address, key name. A
       SHIPPED one can only be re-pointed: its address and the name of its key
       are facts about this machine, while its tool gates, context caps and
       transport are reviewed decisions that live in the committed file. So the
       shipped form offers two fields and a way back to the default, rather
       than pretending everything is editable and refusing on save. */
    function editForm(p, done) {
      var label = C.el("input", { type: "text", placeholder: "Label",
                                  "aria-label": "Label" });
      label.value = p.label || "";
      var url = C.el("input", { type: "text", style: "min-width:17em",
                                placeholder: "http://host:port/v1",
                                "aria-label": "Base URL" });
      url.value = p.base_url || "";
      // "KEY_ENV_VAR (optional)" was true and still misread: a text box next
      // to a URL, on a row whose complaint is "the key is not set", reads as
      // somewhere to paste a key. Pasting one there fails validation, which
      // is correct and arrives too late to be kind.
      var keyEnv = C.el("input", { type: "text",
                                   placeholder: "OPENROUTER_API_KEY (a NAME, not the key)",
                                   title: "The NAME of an environment variable. "
                                          + "The key itself goes in the .env file "
                                          + "named at the bottom of this panel.",
                                   "aria-label": "Key environment variable name" });
      keyEnv.value = p.key_env || "";
      var result = C.el("div", { class: "muted", style: "font-size:11.5px;flex-basis:100%" });

      var test = C.el("button", {
        class: "btn sm",
        // Before saving, so a wrong port is a sentence rather than a failed
        // turn ten minutes later.
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

      var apply = C.el("button", {
        class: "btn sm primary",
        onclick: function () {
          if (p.custom) {
            save({ custom: { id: p.id, label: label.value,
                             base_url: url.value, api_key_env: keyEnv.value } }, done);
          } else {
            // A shipped row: only where it is and what its key is called.
            // The patch is built from the third argument, so there is nothing
            // to pass as the first.
            save(null, done, { id: p.id, base_url: url.value,
                               api_key_env: keyEnv.value });
          }
        },
      }, ["Save"]);

      var cancel = C.el("button", { class: "btn sm", onclick: function () { done(); } },
                        ["Cancel"]);

      // Only for a shipped row that has been moved: put it back where the
      // committed file says it lives.
      var moved = !p.custom && p.default_base_url && p.base_url !== p.default_base_url;
      var reset = moved ? C.el("button", {
        class: "btn sm",
        title: "Back to " + p.default_base_url,
        onclick: function () {
          save(null, done, { id: p.id, base_url: "", api_key_env: "" });
        },
      }, ["Reset to default"]) : null;

      var fields = p.custom ? [label, url, keyEnv] : [url, keyEnv];
      return C.el("div", { class: "setrow", style: "flex-wrap:wrap" }, [
        C.el("div", { class: "settext" }, [
          C.el("b", { text: "Editing " + p.label }),
          C.el("span", { text: p.custom
            ? "your provider — label, address and the NAME of its key"
            : "a shipped provider — only where it is and what its key is "
              + "called. Everything else stays in agents.toml" }),
        ]),
        C.el("div", { class: "setctl" }, fields.concat([test, apply, reset, cancel])),
        result,
      ]);
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
            (!p.custom && p.default_base_url && p.base_url !== p.default_base_url)
              ? C.el("span", { class: "chip warn", style: "margin-left:6px",
                               title: "ships as " + p.default_base_url },
                     ["moved"]) : null,
          ]),
          C.el("span", { text: state }),
        ]),
        p.enabled
          ? C.chip(p.available ? "ready" : "unusable", p.available ? "ok" : "warn")
          : null,
        p.enabled ? refresh : null,
        C.el("button", {
          class: "btn sm",
          title: p.custom ? "Edit this provider"
                          : "Point this provider somewhere else on this machine",
          onclick: function () { editing = p.id; load(); },
        }, [C.icon("pencil")]),
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

    /* Where the keys live, by absolute path.

       Every "the key is not set" message pointed at "the workspace .env" and
       none of them said where that was — on a machine where the file did not
       exist yet, that is an instruction to edit something invisible. Names
       only, never values: this is a web page. */
    function envFooter(info) {
      info = info || {};
      var path = info.path || "";
      var present = !!info.present;
      var names = info.names || [];
      return C.el("div", { class: "envfile" }, [
        C.el("div", { class: "row" }, [
          C.icon(present ? "file" : "alert"),
          C.el("b", { text: present ? "Keys are read from" : "No key file yet — create" }),
        ]),
        C.el("code", { class: "envpath", text: path }),
        C.el("div", { class: "muted", style: "font-size:11.5px" }, [
          present
            ? (names.length
                ? "defines " + names.join(", ")
                : "present, but defines nothing")
            : "one KEY=value per line. It is gitignored, and read once when "
              + "the console starts — add a key and restart.",
        ]),
      ]);
    }

    function paintRows(rows, envInfo) {
      C.clear(body);
      rows.forEach(function (p) {
        body.appendChild(row(p));
        if (editing === p.id) {
          body.appendChild(editForm(p, function () { editing = null; load(); }));
        }
      });
      if (adding) {
        body.appendChild(addForm());
      } else {
        body.appendChild(C.el("div", { class: "row", style: "margin-top:9px" }, [
          C.el("button", {
            class: "btn sm",
            onclick: function () { adding = true; paintRows(rows, envInfo); },
          }, [C.icon("cpu"), "Add a provider"]),
        ]));
      }
      body.appendChild(envFooter(envInfo));
    }

    function load() {
      C.get("/api/agents/providers")
        .then(function (d) { paintRows(d.providers || [], d.env_file); })
        .catch(function (err) { C.clear(body).appendChild(C.errbox(err)); });
    }
    load();

    return C.panel("Model providers", [body], null, {
      icon: "cpu",
      collapse: { id: "set.providers", open: false },
      help: ["Switch one on to use it in the composer and as the Assistant's "
             + "backend. Stored for THIS machine in ",
             C.el("code", {}, ["console/.cache/agents/providers.json"]),
             " — the committed ", C.el("code", {}, ["agents.toml"]),
             " keeps stating the defaults, comments and all. A key is named, "
             + "never pasted: put its value in the workspace ",
             C.el("code", {}, [".env"]), "."],
    });
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
      toggle("pickSkills", true, "Skill menu (/)", "offers .claude/skills"),
      toggle("pickAgents", true, "Agent menu (@)", "offers .claude/agents"),
      toggle("pickFiles", true, "File menu (#)",
             "searches the workspace; never offers .env or other secrets"),
      toggle("chatListHidden", false, "Start with the chat list folded",
             "wide windows only — a narrow one always opens on the chat"),
    ], null, {
      icon: "pencil",
      collapse: { id: "set.composer", open: false },
      help: ["Type ", C.el("code", {}, ["/"]), " for a skill, ",
             C.el("code", {}, ["@"]), " for an agent, ", C.el("code", {}, ["#"]),
             " for a file. A trigger only opens the menu at the start of a "
             + "word, so ", C.el("code", {}, ["and/or"]), " and ",
             C.el("code", {}, ["#1234"]),
             " are left alone — and a reference that names nothing real "
             + "is sent as plain text rather than as an error."],
    });
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

    return C.panel("Loaded on the server", [body], null, {
      icon: "package",
      collapse: { id: "set.diagnostics", open: false },
      help: ["This is what ", C.el("code", {}, ["console/config/plugins.toml"]),
             " produced — committed, shared by everyone on this checkout, "
             + "and not affected by anything above. Setting a plugin row to ",
             C.el("code", {}, ["enabled = false"]),
             " means its module is never imported: the routes below disappear "
             + "and the tab leaves the manifest, rather than merely being "
             + "hidden."],
    });
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

    return C.panel("This machine", [body], null, {
      icon: "wrench",
      collapse: { id: "set.machine", open: false },
      help: "Worktrees and notification reach for THIS checkout — things "
            + "you set up once and confirm months later. Read-only here on "
            + "purpose: adding a worktree checks out a branch, and this page "
            + "has no authentication of its own.",
    });
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

    return C.panel("Telegram", [body], null, {
      icon: "send",
      collapse: { id: "set.telegram", open: false },
      help: "Where an agent's approval request goes when you are away from "
            + "this machine. Settable here: what QUIETS the bot — which "
            + "events fire, and quiet hours. Anything that WIDENS it — "
            + "inbound, the allowlist, the credentials — is terminal-only, "
            + "because this page has no authentication of its own.",
    });
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

      /* Six subjects, not twenty settings in a column. Each one folds, and
         which are open is remembered — the models you are switching between
         this week stay open, the wake word you set once stays shut. */
      body.appendChild(C.group("Models", [
        effectiveRoute(),
        roleRow(s, d, {
          label: "Talk", backendKey: "backend", modelKey: "model", icon: "cpu",
          autoLabel: "Auto — first installed, local first",
          hint: "conversation, status, ticket lookups — a fast local model "
                + "does this well",
        }),
        roleRow(s, d, {
          label: "Work", backendKey: "work_backend", modelKey: "work_model",
          icon: "wrench", autoLabel: "None — nothing to delegate to",
          hint: "code, builds, test runs. The talk model hands these over with "
                + "console_delegate rather than attempting them",
        }),
        choice(s, "mode", "Tool mode",
          "plan refuses every write, so the Assistant could not create a "
          + "ticket or remember anything",
          [["default", "default — gated tools ask"], ["plan", "plan — read-only"]],
          "sliders"),
      ], {
        id: "set.assistant.models", open: true, icon: "cpu",
        help: "Two roles, because they want different models: Talk answers "
              + "you, Work is what Talk hands code and builds to. The top of "
              + "this section is what a message sent right now would actually "
              + "reach — \"Auto\" is a search over what is running, not a "
              + "fixed choice. A model with no tool training cannot run any of "
              + "the Assistant's verbs.",
      }));

      body.appendChild(C.group("Voice", [
        toggle(s, "speak", "Speak replies",
          "read finished replies aloud — the same switch as Mute replies in "
          + "the tray menu, which writes this one", "speaker"),
        field(s, "speak_voice", "Voice",
          "a neural voice from desktop/tts (fetch one with "
          + "desktop/get-piper.ps1). Blank uses whichever is installed; with "
          + "none, the OS voice speaks — that is the robotic one",
          "text", "speaker"),
        field(s, "speak_rate_percent", "Speaking speed",
          "percent of the voice's natural pace, 50 to 200", "number", "speaker"),
        field(s, "reply_chars", "Spoken length",
          "characters read aloud; the full text always stays in the chat",
          "number", "speaker"),
      ], { id: "set.assistant.voice", open: false, icon: "speaker" }));

      body.appendChild(C.group("Listening", [
        field(s, "listen_max_seconds", "Take cap",
          "seconds — the backstop if the detector never hears you stop",
          "number", "clock"),
        field(s, "listen_silence_ms", "Ends after",
          "milliseconds of quiet, so a pause to think does not cut you off",
          "number", "mic"),
        field(s, "stt_model", "Speech model",
          "base.en is accurate on ticket ids; tiny.en is faster and worse at "
          + "exactly those. Fetch one with desktop/get-whisper.ps1 -Model",
          "text", "brain"),
        choice(s, "tray_click_action", "Tray icon click",
          CLICK_HINT[s.tray_click_action] || CLICK_HINT.listen,
          CLICK_ACTIONS, "mic"),
      ], {
        id: "set.assistant.listening", open: false, icon: "mic",
        help: "One spoken take: it records until you stop talking, or until "
              + "the cap. Transcription happens on this machine.",
      }));

      body.appendChild(C.group("Hands-free", [
        toggle(s, "hands_free_require_wake", "Require the wake word",
          s.hands_free_require_wake
            ? "only what starts with the wake word is sent"
            : "OFF — every utterance is sent, which is for headphones and an "
              + "empty room", "mic"),
        field(s, "hands_free_wake_word", "Wake word",
          "matched at the start of a sentence, as a whole word", "text", "mic"),
        toggle(s, "hands_free_listen_while_speaking",
          "Keep listening while speaking",
          s.hands_free_listen_while_speaking
            ? "for headphones — on speakers it hears itself and answers"
            : "off: it would otherwise answer its own voice", "speaker"),
        field(s, "hands_free_max_minutes", "Stops after",
          "minutes, so a microphone left on by accident does not stay on",
          "number", "clock"),
      ], {
        id: "set.assistant.handsfree", open: false, icon: "mic",
        help: "An always-on microphone. Audio is transcribed on this machine "
              + "and thrown away unless it is addressed, so leaving it on "
              + "means the room is heard locally and forgotten — not sent "
              + "anywhere.",
      }));

      body.appendChild(C.group("Chat", [
        field(s, "session_idle_minutes", "New chat after",
          "minutes of silence before the next message starts a fresh chat",
          "number", "clock"),
        field(s, "ticket_prefix", "Ticket prefix",
          "how a spoken id is canonicalised — \"t dash two\" becomes T-002",
          "text", "list"),
      ], { id: "set.assistant.chat", open: false, icon: "clock" }));

      // Read-only: a capability statement about models, reviewed in the
      // committed file rather than set per machine.
      body.appendChild(C.group("Vision", [
        C.el("div", { class: "row", style: "flex-wrap:wrap" },
          (s.vision_models || []).length
            ? s.vision_models.map(function (m) { return C.chip(m); })
            : [C.chip("none — captures are read with OCR", "warn")]),
      ], {
        id: "set.assistant.vision", open: false, icon: "scope",
        help: ["Which model ids can actually look at a screenshot. Committed "
               + "in ", C.el("code", {}, ["console/config/assistant.toml"]),
               " rather than set here, because it describes the models, not "
               + "this machine — so this list is read-only."],
      }));
    }

    function save(patch) {
      C.post("/api/assistant/settings", patch)
        .then(function (d) { paint({ settings: d.settings, installed: installed }); C.toast("Saved", "ok"); })
        .catch(function (err) { C.toast(err.message, "err"); load(); });
    }

    /* Which backends the role pickers may offer.

       Two requests rather than one, because the answers cost different
       things. `/api/assistant/settings` is on the desktop shell's hot path and
       is now guaranteed not to touch the network; asking which providers are
       reachable means probing them, so it lives on `/api/agents/backends`
       where the cost is expected. The pickers paint as soon as the settings
       land and gain their options a moment later. */
    var installed = [];
    function loadInstalled() {
      return C.get("/api/agents/backends")
        .then(function (d) {
          installed = (d.backends || [])
            .filter(function (b) { return b.installed; })
            .map(function (b) { return b.id; })
            .sort();
          return installed;
        })
        // A failure here costs the picker its options, not the panel. The
        // settings themselves are already on screen and still saveable.
        .catch(function () { return installed; });
    }

    function load() {
      C.get("/api/assistant/settings")
        .then(function (d) {
          paint(d);
          loadInstalled().then(function () { paint(d); });
        })
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

    return C.panel("Assistant", [body], null, {
      icon: "brain",
      collapse: { id: "set.assistant", open: false },
      help: ["Stored for THIS machine in ",
             C.el("code", {}, ["console/.cache/assistant/settings.json"]),
             " — not in the committed defaults, so your choice of backend "
             + "never shows up in anyone else's diff. The native shell reads "
             + "the same merged view."],
    });
  }

  /* "What will actually answer me" — the question the pickers below could
     not answer.

     Talk on "Auto" is not a setting, it is a SEARCH: resolve_backend tries the
     local runtimes first and falls through to whatever is ready. Which one
     that is depends on what is running this minute, so it cannot be shown as
     a selected option in a dropdown — it has to be asked for, live. When the
     local runtimes are off it lands on a CLI that takes seconds per spoken
     turn, and until now nothing on this page said so.

     Its own request because it is a slow one: every candidate is probed until
     one answers. `/api/assistant/settings` is on the tray's hot path and is
     guaranteed not to touch a socket, so this deliberately does not live
     there. */
  function effectiveRoute() {
    var box = C.el("div", { class: "route" }, [
      C.el("span", { class: "muted", text: "checking what will answer…" }),
    ]);

    function line(role, r) {
      if (!r || !r.ready) {
        return C.el("div", { class: "rrow bad" }, [
          C.icon("alert"),
          C.el("div", {}, [
            C.el("b", { text: role + " — nothing is ready" }),
            C.el("span", { class: "muted", text: (r && r.why) || "" }),
          ]),
        ]);
      }
      return C.el("div", { class: "rrow" }, [
        C.icon(r.is_api ? "cpu" : "file"),
        C.el("div", {}, [
          C.el("b", {}, [
            role + " → " + (r.label || r.backend),
            C.el("span", { class: "chip", style: "margin-left:6px",
                           text: r.pinned ? "pinned" : "auto" }),
          ]),
          C.el("span", { class: "muted", text: r.model
            ? "model " + r.model
            // Not a blank: no model flag is sent, so the backend picks. Saying
            // "unknown" would imply we failed to look it up.
            : "no model pinned — " + (r.label || r.backend) + " uses its own default" }),
        ]),
      ]);
    }

    function passed(rows) {
      if (!rows || !rows.length) return null;
      return C.el("details", { class: "why" }, [
        C.el("summary", { text: rows.length + " passed over — why" }),
        C.el("div", { class: "rows" }, rows.map(function (r) {
          return C.el("div", { class: "lrow" }, [
            C.el("span", { class: "mono", style: "font-size:11.5px", text: r.backend }),
            C.el("span", { class: "ltext muted", style: "font-size:11.5px", text: r.why }),
          ]);
        })),
      ]);
    }

    /* Re-asked on demand, because the answer changes without the page
       changing: start a local runtime, or put a key in the workspace .env,
       and the same settings resolve somewhere else entirely. Reloading the
       tab to find out is a worse loop than a button. */
    var again = C.el("button", { class: "btn sm", type: "button",
      onclick: function () { load(); } }, ["Re-check"]);

    function load() {
      again.disabled = true;
      C.get("/api/assistant/resolve").then(function (d) {
        C.clear(box);
        box.appendChild(line("Talk", d.talk));
        box.appendChild(line("Work", d.work));
        // One list, not two: the same candidates are tried for both roles and
        // fail for the same reasons, so printing it twice is just noise.
        box.appendChild(passed((d.talk && d.talk.rejected) || []));
        box.appendChild(C.el("div", { class: "row" }, [again]));
        again.disabled = false;
      }).catch(function (err) {
        C.clear(box);
        box.appendChild(C.el("span", { class: "muted",
          text: "could not work out what will answer: " + err.message }));
        box.appendChild(C.el("div", { class: "row" }, [again]));
        again.disabled = false;
      });
    }
    load();

    return box;
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
    ], null, {
      icon: "folder",
      collapse: { id: "set.storage", open: false },
      help: ["Every key this console has written to your browser's ",
             C.el("code", {}, ["localStorage"]),
             ", verbatim. Nothing here leaves this machine, and resetting it "
             + "touches no server state — it puts the page back to defaults."],
    });
  }

  /* The jump bar. Every panel on this page folds, so the page is a menu of
     subjects — and a menu you have to scroll to read is not one. A chip opens
     its panel and scrolls to it, because a fold you then have to find is not
     navigation.

     Built from the panels actually rendered, not from a list written twice:
     the panels differ by whether Agents loaded and whether this is a static
     export, and a hard-coded index would offer chips for things that are not
     on the page. */
  function jumpBar(host) {
    var panels = [].slice.call(host.querySelectorAll("section.panel.collapsible"));

    function setAll(open) {
      panels.forEach(function (p) { if (p._setOpen) p._setOpen(open); });
    }

    var chips = panels.map(function (p) {
      var title = p.querySelector("header h3");
      return C.el("button", {
        class: "btn sm", type: "button",
        onclick: function () {
          if (p._setOpen) p._setOpen(true);
          p.scrollIntoView({ block: "start", behavior: "smooth" });
        },
      }, [title ? title.textContent : "Section"]);
    });

    return C.el("div", { class: "secnav" }, [
      C.el("div", { class: "chips" }, chips),
      C.el("button", { class: "btn sm", type: "button",
        onclick: function () { setAll(false); } }, ["Collapse all"]),
      C.el("button", { class: "btn sm", type: "button",
        onclick: function () { setAll(true); } }, ["Expand all"]),
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
      kids.push(storage(paint));
      if (!C.IS_STATIC) kids.push(diagnostics());

      // One grid for everything now that the tall panels fold: storage and
      // diagnostics were full-width rows below because they were long, which
      // stopped being true.
      var grid = C.el("div", { class: "grid" }, kids);
      h.appendChild(jumpBar(grid));
      h.appendChild(grid);
    }

    paint();
  }

  C.tab("settings", { render: render });
})(window.Console);
