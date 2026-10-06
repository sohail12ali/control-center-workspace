/* Settings tab. Two kinds of control live here, and the page says which
   is which.

   Appearance, tab visibility, and the "Saved preferences" panel are saved
   preferences, shared through the server by the desktop app and every
   browser tab. They change what is shown, never what the server offers.
   `enabled = false` in console/config/plugins.toml is a
   committed, server-side decision that removes the routes for everyone who
   pulls the checkout. Conflating the two would let someone "turn off" the
   agents plugin by hiding its tab and believe the launch endpoint was gone.
   The Diagnostics panel lists what the server actually loaded.

   The Workspace panel is the other server action: it reports leftover
   tickets and secret paths, and it can delete workspace content from this
   checkout after you type reset. It does not commit, and it does not
   rewrite history. */
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
      help: "System follows your OS. A pinned choice overrides it and is saved "
            + "with your other preferences, so the desktop app and every browser "
            + "tab show the same theme. It changes how the console looks, nothing else.",
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
      help: "Hide tabs you don't use. The choice is saved with your other preferences, "
            + "so the desktop app and every browser tab hide the same tabs, and it "
            + "applies immediately. It only hides a tab from view; it does not turn "
            + "the feature off.",
    });
  }

  /* Agent CLIs — which backends the composer offers.

     A saved preference, like the tab switches, shared by the app and every
     browser tab: this hides a CLI from the shared picker.
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
             + "runs as a process. Which ones the New-chat picker offers is a "
             + "saved preference, shared by the app and every browser tab; to "
             + "change what the server offers everyone, edit ",
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

  /* Composer — how the message box behaves. Saved preferences shared by the
     app and every browser tab, like the switches above: these are view
     preferences, not deployment decisions. */
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

    /* When each setting takes effect, exactly as the server says it
       (`applies` on GET /api/assistant/settings). Held here and set in load():
       both repaints (load's second paint and save) pass objects that carry only
       `settings` and `backends`, so reading it off `d` in paint would drop
       every chip on the second paint. The page keeps no list of its own, only
       the label for each kind of answer (AC-69). */
    var applies = {};
    var WHEN_LABEL = { live: "(live)", restart: "(restart needed)", next_chat: "(next chat)" };

    // `key` is the setting a row edits. A row with none (a readout, the wake
    // recorder) shows no chip, because there is nothing to say about when it
    // takes effect.
    function row(label, hint, control, iconName, key) {
      var when = key ? applies[key] : null;
      var chip = when && WHEN_LABEL[when.when]
        ? C.el("span", {
            class: "va-when va-when-" + when.when,
            title: when.note || "", text: WHEN_LABEL[when.when],
          })
        : null;
      return C.el("div", { class: "setrow" }, [
        iconName ? C.icon(iconName) : null,
        C.el("div", { class: "settext" }, [
          C.el("b", {}, [label, chip && " ", chip]), C.el("span", { text: hint }),
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
      ]), iconName, key);
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
      return row(label, hint, C.el("div", { class: "setctl" }, [input]), iconName, key);
    }

    /* Record the wake word: say it three times, then build it.

       Three, because one recording is a template of one reading of the phrase
       and the detector is only as forgiving as what it was given. The button
       blocks while the shell records — that is honest, it IS recording — and
       says what it heard back as a count, never as audio. */
    function wakeRecorder(s) {
      var name = String(s.hands_free_wake_word || "console");
      var status = C.el("span", { text: "" });
      var say = C.el("button", { class: "btn", text: "Say it" });
      var build = C.el("button", { class: "btn", text: "Build" });
      var forget = C.el("button", { class: "btn", text: "Remove" });
      var taken = 0;

      function busy(on, what) {
        [say, build, forget].forEach(function (b) { b.disabled = on; });
        if (on) status.textContent = what;
      }
      function report(installed) {
        if (installed && installed.length) {
          status.textContent = "recorded: " + installed.join(", ");
        } else if (taken) {
          status.textContent = taken + " of 3 recorded";
        } else {
          status.textContent = "not recorded — hands-free falls back to "
            + "transcribing everything";
        }
      }

      say.addEventListener("click", function () {
        busy(true, "listening — say it now");
        C.post("/api/assistant/wake/sample", { name: name }).then(function (r) {
          busy(false);
          if (r && r.samples) { taken = r.samples; report(null); }
          else { status.textContent = (r && r.reason) || "nothing recorded"; }
        }).catch(function (e) { busy(false); status.textContent = String(e); });
      });
      build.addEventListener("click", function () {
        busy(true, "building");
        C.post("/api/assistant/wake/train", { name: name }).then(function (r) {
          busy(false);
          taken = 0;
          if (r && r.wakeword) { report(r.installed); }
          else { status.textContent = (r && r.reason) || "could not build it"; }
        }).catch(function (e) { busy(false); status.textContent = String(e); });
      });
      forget.addEventListener("click", function () {
        busy(true, "removing");
        C.post("/api/assistant/wake/forget", { name: name }).then(function (r) {
          busy(false); taken = 0; report(r && r.installed);
        }).catch(function (e) { busy(false); status.textContent = String(e); });
      });

      C.get("/api/assistant/voice").then(function (v) {
        report(v && v.wake && v.wake.installed);
      }).catch(function () { report(null); });

      return row("Record the wake word",
        "say it three times, then build — it is matched against your voice, "
        + "on this machine, and never leaves it",
        C.el("div", { class: "setctl" }, [say, build, forget, status]), "mic");
    }

    /* The live panel: input level, wake score, and what the engine is.

       Polled rather than streamed. A second of staleness costs nothing here,
       and an EventSource for a panel most people never open would be a
       connection held open for the life of the tab. */
    function voicePanel() {
      var lines = C.el("div", { class: "setctl", style: "flex-direction:column;align-items:flex-start" });
      var timer = null;

      function draw(v) {
        lines.textContent = "";
        if (!v || v.ok === false) {
          lines.appendChild(C.el("span", {
            text: (v && v.reason) || "the desktop shell is not running",
          }));
          return;
        }
        var wake = v.wake || {};
        [
          ["Microphone", v.microphone || "none"],
          ["Input level", bar(v.wake && v.wake.level)],
          ["Listening", v.listening ? "yes" : "no"],
          ["Hands-free", v.hands_free ? "on" : "off"
            + (v.hands_free_stopped ? " — " + v.hands_free_stopped : "")],
          ["Wake word", wake.available ? (wake.installed || []).join(", ")
            : (wake.hint || "not recorded")],
          ["Wake score", bar(wake.score)],
          ["Last fired", wake.fired
            ? wake.fired.name + " at " + wake.fired.score.toFixed(2)
            : "not since the shell started"],
          ["Speech engine", v.engine_running
            ? (v.model || "running") : "not running"],
        ].forEach(function (pair) {
          lines.appendChild(C.el("div", {}, [
            C.el("b", { text: pair[0] + ": " }),
            C.el("span", { text: String(pair[1]) }),
          ]));
        });
      }

      // A number AND a bar: the bar is what you watch while talking, the
      // number is what you quote when it does not work.
      function bar(value) {
        var n = Math.max(0, Math.min(1, Number(value) || 0));
        var filled = Math.round(n * 20);
        return "[" + new Array(filled + 1).join("#")
          + new Array(20 - filled + 1).join(".") + "] " + n.toFixed(2);
      }

      function poll() {
        C.get("/api/assistant/voice").then(draw).catch(function (e) {
          draw({ ok: false, reason: String(e) });
        });
      }
      // Only while the panel is on screen: a hidden panel polling the shell
      // twice a second would keep a microphone-adjacent endpoint warm for no
      // reason anybody asked for.
      var observer = new IntersectionObserver(function (entries) {
        var visible = entries.some(function (e) { return e.isIntersecting; });
        if (visible && !timer) { poll(); timer = setInterval(poll, 500); }
        if (!visible && timer) { clearInterval(timer); timer = null; }
      });
      observer.observe(lines);
      return row("Live", "updates twice a second while this panel is open",
        lines, "mic");
    }

    /* The speech-model manager: what is installed, what could be, which one
       is in use.

       Every fact on a row (state, size, hint, licence, verified, in use) is
       the server's, from GET /api/assistant/voice/assets. That route scans
       desktop/stt and desktop/tts itself, so it answers with the desktop
       shell stopped, and the page keeps no catalogue of its own.
       `loadAssets()` is the one request: the pickers elsewhere on this page
       reuse it instead of adding more. */
    var assets = null;          // the last good answer
    var assetsFetch = null;     // the request in flight, so callers share it
    var assetTimer = null;
    var assetNotes = {};        // row -> the sentence a refused action or a failed check left
    var assetViews = [];        // pickers that follow the same answer: { sel, fill }
    var ASSET_ACTIVE = { downloading: true, retrying: true, verifying: true };
    var ASSET_STATE_KIND = {
      installed: "ok", partial: "warn", paused: "warn", retrying: "warn",
      downloading: "info", verifying: "info", failed: "danger",
    };

    // `fresh`: the caller just changed something, so an answer already on its
    // way may predate it. Wait that one out and ask again.
    function loadAssets(fresh) {
      if (fresh && assetsFetch) {
        return assetsFetch.then(null, function () {}).then(function () { return loadAssets(); });
      }
      if (!assetsFetch) {
        assetsFetch = C.get("/api/assistant/voice/assets").then(function (d) {
          assetsFetch = null; assets = d;
          // The pickers on this page follow the one answer; a repaint leaves the
          // old ones detached, so they are dropped here.
          assetViews = assetViews.filter(function (v) { return v.sel.isConnected; });
          assetViews.forEach(function (v) { v.fill(d); });
          return d;
        }, function (err) { assetsFetch = null; throw err; });
      }
      return assetsFetch;
    }

    // Binary units, like the sizes in the hints the catalogue carries.
    function fmtBytes(n) {
      n = Number(n) || 0;
      if (n >= 1073741824) return (n / 1073741824).toFixed(2) + " GiB";
      if (n >= 1048576) return (n / 1048576).toFixed(1) + " MiB";
      if (n >= 1024) return Math.round(n / 1024) + " KiB";
      return n + " B";
    }

    function fmtLeft(s) {
      if (s < 90) return s + " s";
      if (s < 5400) return Math.round(s / 60) + " min";
      return (s / 3600).toFixed(1) + " h";
    }

    function tip(node, text) { node.setAttribute("title", text); return node; }

    function assetManager() {
      var box = C.el("div", { class: "va-list" });
      var parts = {};             // row -> { el, key, update } for what is on screen
      var built = false;
      var diskText = C.el("span", { class: "va-size" });
      var diskRow = row("Free disk space",
        "where models and voices are kept: desktop/stt and desktop/tts",
        C.el("div", { class: "setctl" }, [diskText]), "file");
      // The shell being stopped is a state, not a fault: the list is read from
      // disk and is complete without it.
      var shellNote = C.el("div", {
        class: "va-note", hidden: true,
        text: "The desktop shell is not running, so which model it has loaded "
          + "is not shown. What is on disk is listed regardless.",
      });
      // A repaint replaces this list, so the old list's timer must not outlive
      // it: one timer per panel.
      clearTimeout(assetTimer);

      function uid(a) { return a.kind + ":" + a.id; }

      // The buttons post the id and nothing else: the server owns the
      // catalogue, so there is no hash, URL or path for this page to send
      // (delete also names the inventory file).
      function act(a, action, extra) {
        var body = { id: a.id };
        if (extra) Object.keys(extra).forEach(function (k) { body[k] = extra[k]; });
        delete assetNotes[uid(a)];
        return C.post("/api/assistant/voice/assets/" + action, body).then(function (r) {
          // A verify that finds different bytes answers 200 with ok:false: a
          // result to show, not a fault.
          if (r && r.ok === false && r.message) assetNotes[uid(a)] = r.message;
        }, function (err) {
          assetNotes[uid(a)] = err && err.status ? err.message
            : "Could not reach the console: " + ((err && err.message) || err);
        }).then(function () { poll(true); });
      }

      function btn(label, kind, onclick) {
        return C.el("button", {
          type: "button", class: "btn sm" + (kind ? " " + kind : ""),
          onclick: onclick, text: label,
        });
      }

      function actions(a) {
        var name = a.label || a.id;
        var out = [];
        function go(action, extra) {
          return function (e) { e.currentTarget.disabled = true; act(a, action, extra); };
        }
        if (a.state === "not_installed" || a.state === "partial" || a.state === "failed") {
          out.push(tip(btn("Download", "primary", go("download")),
            a.state === "not_installed" ? "download " + fmtBytes(a.size_bytes)
              : "continue from what is already on disk"));
        }
        if (ASSET_ACTIVE[a.state]) out.push(btn("Pause", "", go("pause")));
        if (a.state === "paused") out.push(btn("Resume", "primary", go("resume")));
        if (ASSET_ACTIVE[a.state] || a.state === "paused") out.push(btn("Cancel", "", go("cancel")));
        if (a.state === "installed" && !a.custom && !a.verified) {
          out.push(tip(btn("Verify", "", go("verify")),
            "check the file against the catalogue checksum"));
        }
        if (a.state === "installed" || a.state === "partial" || a.state === "failed") {
          var why = a.loaded
            ? "it is loaded in the speech engine; choose another model and wait for it to load first"
            : (a.in_use ? "it is in use; choose another "
                + (a.kind === "stt" ? "model" : "voice") + " first" : "");
          var del = btn("Delete", "danger", function (e) {
            var sure = window.confirm(a.state === "installed"
              ? "Delete " + name + "?\n\nIt is removed from disk (" + fmtBytes(a.size) + ")."
                + (a.custom ? " It is not in the catalogue, so it cannot be downloaded again from here."
                            : " You can download it again later.")
              : "Discard the partly downloaded " + name + "?");
            if (!sure) return;
            e.currentTarget.disabled = true;
            act(a, "delete", { name: a.name });
          });
          out.push(del);
          if (why) {
            del.disabled = true;
            out.push(C.el("span", { class: "va-reason", text: "Delete is off: " + why }));
          }
        }
        return out;
      }

      // A real progress bar, so a screen reader hears "42%" and not nothing.
      // It is updated in place: replacing the row every second would drop the
      // focus and could eat a click that starts mid-redraw.
      function progress(a) {
        var fill = C.el("span", { class: "va-fill" });
        var bar = C.el("div", {
          class: "va-bar", role: "progressbar", "aria-valuemin": 0,
          "aria-valuemax": 100, "aria-valuenow": 0,
          "aria-label": "Download of " + (a.label || a.id),
        }, [fill]);
        var text = C.el("div", { class: "va-bar-text" });
        function update(b) {
          var total = Number(b.total) || Number(b.size_bytes) || 0;
          var done = Math.max(0, Math.min(Number(b.done) || 0, total));
          var pct = total ? Math.floor(100 * done / total) : 0;
          var bits = [pct + "%"];
          if (b.state === "paused") bits.push("paused");
          else if (b.state === "retrying") bits.push("reconnecting");
          else if (b.state === "verifying") bits.push("checking the checksum");
          else {
            if (b.speed_bps > 0) bits.push(fmtBytes(b.speed_bps) + "/s");
            // Left out when the server has no estimate, never shown as 0.
            if (b.eta_s !== null && b.eta_s !== undefined) bits.push(fmtLeft(b.eta_s) + " left");
          }
          var line = bits.join(" · ");
          bar.setAttribute("aria-valuenow", String(pct));
          bar.setAttribute("aria-valuetext", line);
          fill.style.width = pct + "%";
          text.textContent = line;
        }
        update(a);
        return { el: C.el("div", { class: "va-progress" }, [bar, text]), update: update };
      }

      // What decides whether a row's markup must be rebuilt. Progress is not
      // in it: that is updated in place.
      function rowKey(a) {
        return [a.state, a.size, a.verified, a.in_use, a.loaded, a.custom, a.error,
          assetNotes[uid(a)] || ""].join("|");
      }

      function assetRow(a, key) {
        var installed = a.state === "installed";
        var size = a.state === "partial"
          ? fmtBytes(a.size) + " of " + fmtBytes(a.size_bytes)
          : fmtBytes(installed ? a.size : a.size_bytes);
        var meter = ASSET_ACTIVE[a.state] || a.state === "paused" ? progress(a) : null;
        // The server's own sentence: a refused action, a failed check, or why
        // the download failed (disk full, upstream changed, checksum mismatch).
        var problem = assetNotes[uid(a)] || (a.state === "failed" ? a.error : "");
        var facts = [
          C.chip(String(a.state).replace(/_/g, " "), ASSET_STATE_KIND[a.state]),
          C.chip(a.kind === "stt" ? "model" : "voice"),
          a.custom ? tip(C.chip("custom"), "a file placed by hand; not in the catalogue") : null,
          C.el("span", { class: "va-size", text: size }),
          installed
            ? (a.verified
                ? tip(C.chip("verified", "ok"), "checked against the catalogue checksum")
                : tip(C.chip("not verified"), "present, but not checked against the catalogue checksum"))
            : null,
          a.in_use ? tip(C.chip("in use", "accent"), "the one the assistant uses now") : null,
          a.loaded ? tip(C.chip("loaded", "info"), "loaded in the speech engine right now") : null,
          a.license ? C.el("span", { class: "va-licence", text: "Licence: " + a.license }) : null,
          meter ? meter.el : null,
          C.el("div", { class: "va-actions" }, actions(a)),
          problem ? C.el("div", { class: "va-error", role: "alert", text: problem }) : null,
        ];
        var r = row(a.label || a.id,
          a.hint || "A file placed in desktop/" + (a.kind === "stt" ? "stt" : "tts")
            + " by hand; it is not in the catalogue.",
          C.el("div", { class: "setctl" }, facts), a.kind === "stt" ? "brain" : "speaker");
        r.setAttribute("data-asset", a.id);
        return { el: r, key: key, update: function (b) { if (meter) meter.update(b); } };
      }

      // Rows are kept and updated, not rebuilt: a row is replaced only when
      // something its markup shows has changed, so a button under the pointer
      // is not swapped out from under it by the next poll.
      function draw(d) {
        if (!built) {
          C.clear(box);
          box.appendChild(diskRow);
          box.appendChild(shellNote);
          parts = {};
          built = true;
        }
        diskText.textContent = fmtBytes(d.free_bytes) + " free";
        shellNote.hidden = !(d.shell && d.shell.reachable === false);
        var list = (d.assets || []).slice().sort(function (x, y) {
          return (x.kind === "stt" ? 0 : 1) - (y.kind === "stt" ? 0 : 1);
        });
        var seen = {};
        list.forEach(function (a) {
          var key = rowKey(a), have = parts[uid(a)];
          seen[uid(a)] = true;
          if (have && have.key === key) { have.update(a); return; }
          var made = assetRow(a, key);
          if (have) have.el.replaceWith(made.el);
          parts[uid(a)] = made;
        });
        Object.keys(parts).forEach(function (id) {
          if (!seen[id]) { parts[id].el.remove(); delete parts[id]; }
        });
        // Order them, moving only what is out of place.
        var cursor = shellNote.nextSibling;
        list.forEach(function (a) {
          var el = parts[uid(a)].el;
          if (el === cursor) cursor = cursor.nextSibling;
          else box.insertBefore(el, cursor);
        });
      }

      // A failed refresh keeps the rows already on screen (a hiccup mid
      // download must not blank the list); only a first load has nothing to keep.
      function failed(err) {
        if (built) return;
        C.clear(box);
        box.appendChild(C.errbox(err));
      }

      function active(d) {
        return ((d && d.assets) || []).some(function (a) { return ASSET_ACTIVE[a.state]; });
      }

      // One request a second, and only while a job is moving: an idle list
      // asks for nothing. The chain ends by itself when the list leaves the
      // page (a repaint, another tab), because it checks the node it draws into.
      function poll(fresh) {
        loadAssets(fresh).then(draw, failed).then(function () {
          clearTimeout(assetTimer);
          if (box.isConnected && active(assets)) assetTimer = setTimeout(poll, 1000);
        });
      }

      if (assets) draw(assets); else box.appendChild(C.skeleton(3));
      poll();
      return box;
    }

    /* The Speech model row: a choice among the models that are installed, not
       a name to type. It follows the same answer as the manager below, so a
       download that finishes appears here without a second request.

       A configured name that is not installed stays in the list, marked, so the
       row never claims a model that is not there; the server still decides what
       is valid (shape only), so saving goes through `save()` unchanged. */
    function modelPicker(s) {
      var configured = String(s.stt_model || "");
      var sel = C.el("select", { "aria-label": "Speech model" });
      var shown = null;

      function fill(d) {
        var installed = ((d && d.assets) || []).filter(function (a) {
          return a.kind === "stt" && a.state === "installed";
        });
        var opts = installed.map(function (a) {
          return [a.id, (a.label || a.id) + " · " + fmtBytes(a.size) + (a.in_use ? " · in use" : "")];
        });
        if (configured && !installed.some(function (a) { return a.id === configured; })) {
          opts.unshift([configured, configured + " (not installed)"]);
        }
        // Rebuilt only when something changed: a poll must not close a list
        // somebody has open.
        var sig = JSON.stringify(opts);
        if (sig === shown) return;
        shown = sig;
        C.clear(sel);
        opts.forEach(function (o) {
          var opt = C.el("option", { value: o[0], text: o[1] });
          if (o[0] === configured) opt.selected = true;
          sel.appendChild(opt);
        });
        sel.disabled = !opts.length;
        if (!opts.length) {
          sel.appendChild(C.el("option", { value: "", text: "no model installed — download one below" }));
        }
      }

      sel.addEventListener("change", function () { save({ stt_model: sel.value }); });
      // Until the list arrives, say what is configured and nothing more.
      sel.appendChild(C.el("option", { value: configured, text: configured || "…" }));
      sel.disabled = true;
      assetViews.push({ sel: sel, fill: fill });
      if (assets) fill(assets); else loadAssets().catch(function () {});
      return row("Speech model",
        "base.en is accurate on ticket ids; tiny.en is faster and worse at "
        + "exactly those. Download more under Speech models and voices, below.",
        C.el("div", { class: "setctl" }, [sel]), "brain", "stt_model");
    }

    /* The Voice and Speaking speed rows: a choice among the voices that are
       installed and a slider, not a name and a number to type. The voice list
       follows the same answer as the manager (`loadAssets()`), which is also
       how the page learns what the shell is speaking with: `shell.speak_backend`.

       Preview speaks the sample with what the controls show right now, saved or
       not, and saves nothing. A slider saves on `change` (its release), not on
       every `input`, because each save is a POST and an audit record. */
    function voiceRows(s) {
      var configured = String(s.speak_voice || "");
      var sel = C.el("select", { "aria-label": "Voice" });
      var rate = C.el("input", {
        type: "range", min: "50", max: "200", step: "5", "aria-label": "Speaking speed",
      });
      var shownRate = C.el("span", { class: "va-size" });
      var preview = C.el("button", { class: "btn", text: "Preview" });
      var note = C.el("span", { class: "va-line" });
      var shown = null;
      var osVoice = false;
      var whyShown = false;

      var r0 = Number(s.speak_rate_percent);
      rate.value = String(isFinite(r0) && r0 > 0 ? r0 : 100);
      function showRate() { shownRate.textContent = rate.value + " %"; }
      showRate();

      function fill(d) {
        var shell = (d && d.shell) || {};
        osVoice = !!(shell.reachable && shell.speak_backend && shell.speak_backend !== "piper");
        var installed = ((d && d.assets) || []).filter(function (a) {
          return a.kind === "voice" && a.state === "installed";
        });
        var opts = [["", "Automatic - first installed"]];
        if (configured && !installed.some(function (a) { return a.id === configured; })) {
          opts.push([configured, configured + " (not installed)"]);
        }
        installed.forEach(function (a) {
          opts.push([a.id, (a.label || a.id) + (a.in_use ? " · in use" : "")]);
        });
        var sig = JSON.stringify(opts);
        if (sig !== shown) {
          shown = sig;
          C.clear(sel);
          opts.forEach(function (o) {
            var opt = C.el("option", { value: o[0], text: o[1] });
            if (o[0] === configured) opt.selected = true;
            sel.appendChild(opt);
          });
        }
        var why = osVoice
          ? "the OS voice is speaking: voice, speed and device choices do not apply" : "";
        [sel, rate, preview].forEach(function (c) {
          c.disabled = osVoice;
          if (why) c.setAttribute("title", why); else c.removeAttribute("title");
        });
        // The reason owns the line while it applies; a Preview sentence owns it otherwise.
        if (osVoice) { note.textContent = why; whyShown = true; }
        else if (whyShown) { note.textContent = ""; whyShown = false; }
      }

      rate.addEventListener("input", showRate);
      rate.addEventListener("change", function () { save({ speak_rate_percent: Number(rate.value) }); });
      sel.addEventListener("change", function () { save({ speak_voice: sel.value }); });
      preview.addEventListener("click", function () {
        note.textContent = "";
        preview.disabled = true;
        C.post("/api/assistant/voice/preview", { voice: sel.value, rate_percent: Number(rate.value) })
          .then(function (r) {
            note.textContent = r && r.ok === false
              ? (r.reason || "the sample could not be spoken") : "speaking the sample";
          })
          .catch(function (e) { note.textContent = e.message; })
          .then(function () { preview.disabled = osVoice; });
      });

      // Until the list arrives, say what is configured and nothing more.
      sel.appendChild(C.el("option", { value: configured, text: configured || "Automatic - first installed" }));
      sel.disabled = true;
      assetViews.push({ sel: sel, fill: fill });
      if (assets) fill(assets); else loadAssets().catch(function () {});

      return [
        row("Voice",
          "a neural voice from desktop/tts; download more under Speech models "
          + "and voices, below. Automatic uses the first one installed; with "
          + "none, the OS voice speaks - that is the robotic one",
          C.el("div", { class: "setctl" }, [sel, preview, note]), "speaker", "speak_voice"),
        row("Speaking speed", "percent of the voice's natural pace, 50 to 200",
          C.el("div", { class: "setctl" }, [rate, shownRate]), "speaker", "speak_rate_percent"),
      ];
    }

    /* The Audio devices group: which microphone and speaker, chosen by NAME.

       A name, not an index, because the order changes when something is
       plugged in. The page lists what the shell sees and shows the shell's own
       verdict on the saved name (`match`, `resolved`, `fallback`, `candidates`
       under `input` and `output`); it never matches names itself, so the one
       matcher stays in the shell (BR-6). Re-listed every 3 s, but only while
       the group is on screen, and never while a dropdown is open under the
       user's hand: a repaint would close it. */
    var deviceAnswer = null;    // the last answer, so a repaint draws at once

    function devicesPanel(s) {
      var wrap = C.el("div", { class: "va-list" });
      var timer = null;
      var inflight = false;
      var shown = null;
      var refresh = C.el("button", { class: "btn", text: "Refresh" });
      var status = C.el("span", { class: "va-line" });

      function devRow(label, hint, key, dir, iconName) {
        var sel = C.el("select", { "aria-label": label });
        var note = C.el("span", { class: "va-line" });
        sel.addEventListener("change", function () {
          var patch = {}; patch[key] = sel.value; save(patch);
        });
        return {
          dir: dir, key: key, sel: sel, note: note,
          node: row(label, hint, C.el("div", { class: "setctl" }, [sel, note]), iconName, key),
        };
      }
      var mic = devRow("Microphone",
        "the input the assistant listens on. System default follows the "
        + "operating system's choice", "input_device", "input", "mic");
      var spk = devRow("Speaker",
        "the output replies, previews and the test tone play on",
        "output_device", "output", "speaker");

      function fillRow(r, d) {
        var cfg = String(((d.configured || {})[r.dir] !== undefined
          ? d.configured[r.dir] : s[r.key]) || "");
        var names = (r.dir === "input" ? d.inputs : d.outputs) || [];
        var def = (r.dir === "input" ? d.default_input : d.default_output) || "";
        var v = d[r.dir] || {};
        // The shell's verdict is for the name the shell has applied; a name
        // saved a moment ago may not be there yet, and then it says so.
        var current = v.configured === cfg;
        var opts = [["", "System default" + (def ? " (" + def + ")" : "")]];
        if (cfg && names.indexOf(cfg) < 0) {
          opts.push([cfg, cfg + (current && v.fallback ? " (not connected)"
            : current && v.resolved ? " (matches " + v.resolved + ")" : "")]);
        }
        names.forEach(function (n) { opts.push([n, n]); });
        C.clear(r.sel);
        opts.forEach(function (o) {
          var opt = C.el("option", { value: o[0], text: o[1] });
          if (o[0] === cfg) opt.selected = true;
          r.sel.appendChild(opt);
        });
        r.sel.disabled = false;
        r.sel.removeAttribute("title");
        if (!cfg) r.note.textContent = "";
        else if (!current) r.note.textContent = "the app has not applied this choice yet";
        else if (v.fallback) {
          var several = (v.candidates || []).length > 1;
          r.note.textContent = (several ? "several devices match: " + v.candidates.join(", ") + " - " : "")
            + (v.resolved ? "using " + v.resolved + " instead" : "no device is available");
        } else r.note.textContent = v.resolved ? "in use: " + v.resolved : "";
      }

      function unavailable(r, why) {
        var cfg = String(s[r.key] || "");
        C.clear(r.sel);
        r.sel.appendChild(C.el("option", { value: cfg, text: cfg || "System default" }));
        r.sel.disabled = true;
        r.sel.setAttribute("title", why);
        r.note.textContent = why;
      }

      function draw(d, force) {
        deviceAnswer = d;
        var sig = JSON.stringify(d);
        if (sig === shown && !force) return;                   // unchanged: nothing to repaint
        if (document.activeElement === mic.sel || document.activeElement === spk.sel) return;
        shown = sig;
        if (!d || d.ok === false) {
          var why = (d && d.reason) || "the desktop shell is not running";
          unavailable(mic, why); unavailable(spk, why);
          status.textContent = "";
          return;
        }
        fillRow(mic, d); fillRow(spk, d);
        status.textContent = (d.inputs || []).length + " microphones, "
          + (d.outputs || []).length + " speakers";
      }

      function poll(force) {
        if (inflight) return;
        inflight = true;
        C.get("/api/assistant/voice/devices").then(function (d) { return d; }, function (e) {
          return { ok: false, reason: String(e && e.message || e) };
        }).then(function (d) { inflight = false; draw(d, force); });
      }
      refresh.addEventListener("click", function () { poll(true); });

      var observer = new IntersectionObserver(function (entries) {
        var visible = entries.some(function (e) { return e.isIntersecting; });
        if (visible && !timer) { poll(); timer = setInterval(function () {
          if (!wrap.isConnected) { clearInterval(timer); timer = null; return; }
          poll();
        }, 3000); }
        if (!visible && timer) { clearInterval(timer); timer = null; }
      });

      /* Test microphone / Test speaker. The shell does the work (open the
         resolved device, listen for 2 s, play a tone) and answers at once; the
         microphone test is then followed by polling the voice state, a script
         cannot hear, so for the speaker the page only says what was played and
         where. The shell's refusals (a take or hands-free is using the
         microphone; no device resolves) arrive as sentences and are shown as
         they are. */
      function peakBar() {
        var fill = C.el("span", { class: "va-fill" });
        var el = C.el("span", {
          class: "va-bar va-meter", role: "meter", "aria-label": "Microphone test level",
          "aria-valuemin": "0", "aria-valuemax": "1", "aria-valuenow": "0",
        }, [fill]);
        return {
          el: el,
          set: function (v) {
            var n = Math.max(0, Math.min(1, Number(v) || 0));
            fill.style.width = Math.round(n * 100) + "%";
            el.setAttribute("aria-valuenow", n.toFixed(2));
            return n;
          },
        };
      }
      var level = peakBar();
      var micInfo = C.el("span", { class: "va-size" });
      var micBtn = C.el("button", { class: "btn", text: "Test microphone" });
      var micNote = C.el("span", { class: "va-line" });
      var spkBtn = C.el("button", { class: "btn", text: "Test speaker" });
      var spkNote = C.el("span", { class: "va-line" });
      function busy(on) { micBtn.disabled = on; spkBtn.disabled = on; }
      function micDone(text) { busy(false); micNote.textContent = text; }

      // About every 250 ms, for at most 4 s (the shell's test listens for 2 s).
      function watchMic(t0) {
        C.get("/api/assistant/voice").then(function (v) {
          var t = v && v.mic_test;
          if (!v || v.ok === false || !t) {
            micDone((v && v.reason) || "the desktop shell did not report the test");
            return;
          }
          var n = level.set(t.peak);
          micInfo.textContent = "peak " + n.toFixed(2) + (t.device ? " - " + t.device : "");
          if (t.error) { micDone(t.error); return; }
          if (t.running && Date.now() - t0 < 4000) {
            setTimeout(function () { watchMic(t0); }, 250);
            return;
          }
          micDone(t.running ? "the test is still running; the level above is what it has heard so far"
            : n < 0.01 ? "nothing was heard: check the microphone above, and that it is not muted"
            : "the level above is the loudest it measured");
        }, function (e) { micDone(e.message); });
      }
      micBtn.addEventListener("click", function () {
        busy(true); micNote.textContent = ""; micInfo.textContent = ""; level.set(0);
        C.post("/api/assistant/voice/test/mic", {}).then(function (r) {
          if (!r || r.ok === false) { micDone((r && r.reason) || "the microphone test could not start"); return; }
          watchMic(Date.now());
        }, function (e) { micDone(e.message); });
      });
      spkBtn.addEventListener("click", function () {
        busy(true); spkNote.textContent = "";
        C.post("/api/assistant/voice/test/speaker", {}).then(function (r) {
          if (!r || r.ok === false) {
            busy(false);
            spkNote.textContent = (r && r.reason) || "the test tone could not be played";
            return;
          }
          spkNote.textContent = "playing a short tone" + (r.device ? " on " + r.device : "")
            + ". If you heard nothing, check the output device above.";
          setTimeout(function () { busy(false); }, 1500);
        }, function (e) { busy(false); spkNote.textContent = e.message; });
      });

      wrap.appendChild(mic.node);
      wrap.appendChild(spk.node);
      wrap.appendChild(row("Test microphone",
        "listens for 2 seconds on the device above and shows how loud it was",
        C.el("div", { class: "setctl" }, [micBtn, level.el, micInfo, micNote]), "mic"));
      wrap.appendChild(row("Test speaker",
        "plays a short tone on the speaker above. This page cannot hear it, "
        + "so it says what was played and on which device",
        C.el("div", { class: "setctl" }, [spkBtn, spkNote]), "speaker"));
      wrap.appendChild(row("Devices", "re-listed every 3 seconds while this group is open",
        C.el("div", { class: "setctl" }, [refresh, status]), "refresh"));
      observer.observe(wrap);
      if (deviceAnswer) draw(deviceAnswer, true);
      else { unavailable(mic, "reading the device list"); unavailable(spk, "reading the device list"); }
      return wrap;
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
      return row(label, hint, C.el("div", { class: "setctl" }, [sel]), iconName, key);
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
    /* A role, chosen in three steps: KIND, then PROVIDER, then MODEL.

       One flat list of backend ids could not answer the question people
       actually arrive with. "Claude Code" and "OpenRouter" are not two items
       of the same kind: one is a binary on PATH that runs as a process, the
       other is a URL and a key, and they fail, cost and behave differently.
       Mixing them in a single dropdown — by raw id, unlabelled — meant
       choosing a backend required already knowing which sort each one was.

       So: kind narrows the providers, and the provider narrows the models.
       Nothing new is stored. `backend` and `model` are the same two settings
       as before; the kind is DERIVED from whichever backend is pinned, so
       there is no third field to disagree with the other two.

       Auto stays, and stays first, because it is the right answer for a
       machine with one usable backend. It stores an empty `backend`, and
       `resolve_backend` searches at send time — which is why the readout at
       the top of this section exists to say where that search landed. */
    function roleRow(s, d, opts) {
        var wrap = C.el("div", {});
        var rows = d.backends || [];
        var pinned = String(s[opts.backendKey] || "");
        var pinnedRow = rows.filter(function (b) { return b.id === pinned; })[0];

        // Derived, never stored: a pinned backend already says which kind it
        // is, and a stored copy could contradict it. `forceKind` is the one
        // exception and lives for a single repaint — after you pick CLI or
        // API there is no provider yet, so there is nothing to derive from
        // and nothing saved to derive it from either.
        var kind = opts.forceKind || (!pinned ? "auto" : (pinnedRow
            ? (pinnedRow.is_api ? "api" : "cli")
            // Pinned to something the server no longer offers. Guess from the
            // id rather than silently resetting the row to Auto.
            : "gone"));

        var kindSel = C.el("select", { "aria-label": opts.label + " kind" });
        [["auto", opts.autoLabel],
         ["cli", "CLI — a binary on PATH, run as a process"],
         ["api", "API — an endpoint the console calls itself"]].forEach(function (o) {
            var opt = C.el("option", { value: o[0], text: o[1] });
            if (o[0] === kind) opt.selected = true;
            kindSel.appendChild(opt);
        });
        if (kind === "gone") {
            var lost = C.el("option", { value: "gone", text: pinned + " — not available now" });
            lost.selected = true;
            kindSel.appendChild(lost);
        }

        /* Only backends that are installed AND enabled can be saved: the
           server refuses the rest by name (`assistant_config.update`). So the
           list offers exactly those — except for a pin that has dropped out,
           which is shown anyway and disabled. A picker that quietly displayed
           "Auto" while the stored setting said `lm-studio` is how you end up
           debugging a machine that is not the one you are looking at. */
        var choices = rows.filter(function (b) {
            return b.installed && (kind === "api" ? b.is_api : !b.is_api);
        });

        var providerSel = C.el("select", { "aria-label": opts.label + " provider" });
        if (kind === "auto") {
            providerSel.appendChild(C.el("option", { value: "", text: "— chosen at send time —" }));
            providerSel.disabled = true;
        } else {
            if (!pinned || !choices.some(function (b) { return b.id === pinned; })) {
                var blank = C.el("option", { value: "", text: "Choose a provider…" });
                blank.selected = true;
                providerSel.appendChild(blank);
            }
            choices.forEach(function (b) {
                var opt = C.el("option", { value: b.id, text: b.label || b.id });
                if (b.id === pinned) opt.selected = true;
                providerSel.appendChild(opt);
            });
            if (kind === "gone") {
                var kept = C.el("option", { value: pinned, text: pinned + " — not reachable now" });
                kept.selected = true;
                providerSel.appendChild(kept);
            }
            if (!choices.length && kind !== "gone") {
                providerSel.appendChild(C.el("option", { value: "",
                    text: kind === "api" ? "no API provider is set up"
                                         : "no CLI is on PATH" }));
            }
        }

        kindSel.addEventListener("change", function () {
            if (kindSel.value === "auto") {
                var patch = {};
                patch[opts.backendKey] = "";
                patch[opts.modelKey] = "";
                save(patch);
                return;
            }
            // Nothing is saved by switching kind alone — there is no provider
            // yet to save. Repaint the two selects below and wait for one.
            kind = kindSel.value;
            pinned = "";
            var next = roleRow(
                Object.assign({}, s, (function () {
                    var o = {}; o[opts.backendKey] = ""; o[opts.modelKey] = ""; return o;
                })()),
                d,
                Object.assign({}, opts, { forceKind: kind }));
            wrap.replaceWith(next);
        });

        providerSel.addEventListener("change", function () {
            if (!providerSel.value) return;
            var patch = {};
            patch[opts.backendKey] = providerSel.value;
            // The model belonged to the old provider; keeping it would send a
            // qwen id to claude.
            patch[opts.modelKey] = "";
            save(patch);
        });

        var models = C.el("select", { "aria-label": opts.label + " model" });
        var note = C.el("span", { class: "muted", style: "font-size:11px" });

        function fillModels(rowsIn, reportsResidency) {
            C.clear(models);
            var chosen = String(s[opts.modelKey] || "");
            models.appendChild(C.el("option", { value: "", text: "(provider default)" }));
            (rowsIn || []).forEach(function (m) {
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
            if (chosen && !(rowsIn || []).some(function (m) { return m.id === chosen; })) {
                var kept = C.el("option", { value: chosen, text: chosen + "  — not in the catalogue" });
                kept.selected = true;
                models.appendChild(kept);
            }
            if (!(rowsIn || []).length) {
                note.textContent = "no catalogue yet — Refresh models on the provider above";
            } else if (!reportsResidency) {
                note.textContent = rowsIn.length + " models · this provider does not report what is loaded";
            } else {
                note.textContent = rowsIn.length + " models";
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

        if (pinned) {
            C.get("/api/agents/models?backend=" + encodeURIComponent(pinned))
                .then(function (m) {
                    models._rows = m.models || [];
                    fillModels(m.models, m.reports_residency);
                })
                .catch(function () { fillModels([], false); });
        } else {
            fillModels([], false);
            models.disabled = true;
            note.textContent = kind === "auto"
                ? "Auto sends no model — each provider uses its own default"
                : "pick a provider to choose a model";
        }

        // The role's chip is its backend's: backend and model of one role are
        // always classed together.
        wrap.appendChild(row(opts.label, opts.hint,
            C.el("div", { class: "setctl" }, [kindSel, providerSel, models, note]),
            opts.icon, opts.backendKey));
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
        voiceRows(s),
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
        field(s, "listen_first_pause_ms", "First pause",
          "milliseconds allowed before you have said much — hands-free only, "
          + "so a pause right after the wake word is thinking, not finishing",
          "number", "clock"),
        modelPicker(s),
        choice(s, "tray_click_action", "Tray icon click",
          CLICK_HINT[s.tray_click_action] || CLICK_HINT.listen,
          CLICK_ACTIONS, "mic"),
      ], {
        id: "set.assistant.listening", open: false, icon: "mic",
        help: "One spoken take: it records until you stop talking, or until "
              + "the cap. Transcription happens on this machine.",
      }));

      body.appendChild(C.group("Speech models and voices", [assetManager()], {
        id: "set.assistant.assets", open: false, icon: "brain",
        help: "Speech models turn your voice into text; voices speak the "
              + "replies. The list and its checksums are committed in "
              + "console/config/voice-assets.toml, and a download is only "
              + "installed after its checksum matches. Each voice shows its "
              + "licence: some are not for commercial use.",
      }));

      body.appendChild(C.group("Hands-free", [
        toggle(s, "hands_free_require_wake", "Require the wake word",
          s.hands_free_require_wake
            ? "only what starts with the wake word is sent"
            : "OFF — every utterance is sent, which is for headphones and an "
              + "empty room", "mic"),
        field(s, "hands_free_wake_word", "Wake word",
          "matched at the start of a sentence, as a whole word", "text", "mic"),
        wakeRecorder(s),
        field(s, "wake_sensitivity", "Sensitivity",
          "0 to 1 — higher fires more readily. Raise it if it misses you, "
          + "lower it if the room sets it off", "text", "mic"),
        field(s, "listen_preroll_ms", "Pre-roll",
          "milliseconds of audio kept from BEFORE the wake word fired, so the "
          + "start of your sentence is not cut off", "number", "clock"),
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
        help: "An always-on microphone. A small detector on this machine "
              + "listens for the wake word, and nothing is transcribed or "
              + "sent anywhere until it fires — so leaving the mic on means "
              + "the room is heard locally and forgotten.",
      }));

      body.appendChild(C.group("Audio devices", [devicesPanel(s)], {
        id: "set.assistant.devices", open: false, icon: "mic",
        help: "Which microphone listens and which speaker speaks, by name. "
              + "A name that is not connected falls back to the system "
              + "default, and this page says which device is in use then.",
      }));

      body.appendChild(C.group("Voice diagnostics", [voicePanel()], {
        id: "set.assistant.voicediag", open: false, icon: "mic",
        help: "What listening can see, live. \"It doesn't work\" is not "
              + "something anyone can act on; a level that never moves and a "
              + "score that never reaches the bar are different faults with "
              + "different fixes.",
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
        .then(function (d) { paint({ settings: d.settings, backends: installed }); C.toast("Saved", "ok"); })
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
          // Whole rows, not ids: the picker needs `label` to name a provider
          // and `is_api` to sort it into CLI or API, and rebuilding either
          // from an id is guesswork about a fact the server already sent.
          installed = (d.backends || []).slice().sort(function (a, b) {
            return String(a.label || a.id).localeCompare(String(b.label || b.id));
          });
          return installed;
        })
        // A failure here costs the picker its options, not the panel. The
        // settings themselves are already on screen and still saveable.
        .catch(function () { return installed; });
    }

    function load() {
      C.get("/api/assistant/settings")
        .then(function (d) {
          // `d` is the settings response and carries no backends, so the
          // first paint draws the pickers empty and the second fills them.
          // Passing `d` unchanged to both was the bug that left every fresh
          // page load showing "Auto" no matter what was pinned.
          applies = d.applies || {};
          paint(d);
          loadInstalled().then(function () {
            paint({ settings: d.settings, backends: installed });
          });
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
        //
        // Guarded, because `passed` returns null when nothing was passed over
        // — and `appendChild(null)` throws, so this panel showed "could not
        // work out what will answer" precisely when the answer was cleanest.
        var why = passed((d.talk && d.talk.rejected) || []);
        if (why) box.appendChild(why);
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

  /* Name and console title. Same two files the setup wizard writes, so a
     change here and a change in the wizard cannot diverge. */
  function identity() {
    var body = C.el("div", {}, [C.skeleton(2)]);

    function paint(snap) {
      var ws = (snap && snap.workspace) || {};
      var name = C.el("input", {
        type: "text", "aria-label": "Your name", value: ws.name || "",
      });
      var title = C.el("input", {
        type: "text", "aria-label": "Console name", value: ws.title || "",
        placeholder: ws.committed_title || "Delivery Console",
      });
      var save = C.el("button", { class: "btn sm", type: "button" }, ["Save"]);
      save.addEventListener("click", function () {
        var next = name.value.trim();
        if (!next) { C.toast("Your name is required", "err"); return; }
        save.disabled = true;
        C.post("/api/onboarding/setup", {
          step: "workspace",
          name: next,
          title: title.value.trim(),
          slug: next === (ws.name || "") ? (ws.slug || "") : "",
        }).then(function (fresh) {
          save.disabled = false;
          var ws = (fresh && fresh.workspace) || {};
          var shown = ws.title || ws.committed_title || "Delivery Console";
          if (window.ConsoleApp && window.ConsoleApp.setTitle) window.ConsoleApp.setTitle(shown);
          C.toast("Workspace saved", "ok");
          paint(fresh);
        }, function (err) {
          save.disabled = false;
          C.toast(err.message || "Could not save", "err");
        });
      });
      C.clear(body);
      body.appendChild(C.el("div", { class: "setrow" }, [
        C.icon("user"),
        C.el("div", { class: "settext" }, [
          C.el("b", { text: "Your name" }),
          C.el("span", { text: "Line 1 of author.local — work logs use it" }),
        ]),
        C.el("div", { class: "setctl" }, [name]),
      ]));
      body.appendChild(C.el("div", { class: "setrow" }, [
        C.icon("info"),
        C.el("div", { class: "settext" }, [
          C.el("b", { text: "Console name" }),
          C.el("span", { text: "Header title for this machine. Blank keeps the committed name." }),
        ]),
        C.el("div", { class: "setctl" }, [title]),
      ]));
      body.appendChild(C.el("div", { class: "row" }, [save]));
    }

    if (C.IS_STATIC) {
      C.clear(body).appendChild(C.el("div", { class: "muted", text: "A static export cannot change this." }));
    } else {
      C.get("/api/onboarding/setup").then(paint, function (err) {
        C.clear(body).appendChild(C.errbox(err));
      });
    }
    return C.panel("Workspace identity", [body], null, {
      icon: "user",
      collapse: { id: "set.identity", open: false },
      help: ["The setup wizard writes these too. The name is ",
             C.el("code", {}, ["knowledge-center/logs/author.local"]),
             ". The console name is a per-machine override, not ",
             C.el("code", {}, ["console.toml"]),
             ", so saving it does not rewrite that file's comments."],
    });
  }

  /* Saved preferences. Read through C.prefs, never the browser's own storage:
     in server mode the shared copy on the server is the truth and this page's
     keys were moved there at boot, so reading them directly shows nothing.
     Each sentence is one string so the wording can be checked as written. */
  function storage(repaint) {
    var server = C.prefs.mode() === "server";
    var all = C.prefs.all();
    var keys = Object.keys(all).sort();
    var MODE_SERVER = "Shared by the desktop app and every browser tab on this machine. Kept on the server in console/.cache/prefs.json; not committed.";
    var MODE_LOCAL = "Stored in this browser only.";
    var RESET_ASK = "Reset every saved preference for the app and all browser tabs? Tickets, chats and other data are not touched.";
    var RESET_HINT_SERVER = "Also clears the shared copy on the server, so the app and every open tab return to defaults.";
    var RESET_HINT_LOCAL = "Clears this browser's saved preferences.";

    /* The Getting-started card tells people Settings can bring it back, so
       there is an explicit control rather than making them work out that
       deleting a saved preference is the way. */
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

    var again = C.el("div", { class: "setrow" }, [
      C.icon("sliders"),
      C.el("div", { class: "settext" }, [
        C.el("b", { text: "Setup wizard" }),
        C.el("span", { text: "Name, providers, editor files, and default models" }),
      ]),
      C.el("button", {
        class: "btn sm", type: "button",
        onclick: function () {
          if (window.ConsoleOnboarding) window.ConsoleOnboarding.open();
        },
      }, ["Run setup again"]),
    ]);

    /* Reset reaches the app and every open tab now, not only this page, so it is
       asked first. A refusal from the server changes nothing, so the list is left
       as it is and the error is shown rather than success. */
    var reset = C.el("button", {
      class: "btn sm danger",
      onclick: function () {
        if (!window.confirm(RESET_ASK)) return;
        reset.disabled = true;
        C.prefs.reset().then(function () {
          window.ConsoleApp.applyTheme("system");
          window.ConsoleApp.rebuildNav();
          C.toast("Preferences reset", "ok");
          repaint();
        }, function (err) {
          reset.disabled = false;
          C.toast("Could not reset preferences: " + (err && err.message ? err.message : err), "err");
        });
      },
    }, ["Reset all preferences"]);

    return C.panel("Saved preferences", [
      again,
      restore,
      C.el("div", { class: "muted", text: server ? MODE_SERVER : MODE_LOCAL }),
      keys.length
        ? C.el("div", { class: "rows" }, keys.map(function (k) {
            return C.el("div", { class: "lrow" }, [
              C.el("span", { class: "mono", style: "font-size:11.5px", text: k }),
              C.el("span", { class: "ltext muted truncate", style: "font-size:11.5px",
                text: JSON.stringify(all[k]) }),
            ]);
          }))
        : C.el("div", { class: "muted", text: "Nothing saved yet — every setting is still at its default." }),
      keys.length
        ? C.el("div", { class: "row", style: "margin-top:9px" }, [
            reset,
            C.el("span", { class: "muted", text: server ? RESET_HINT_SERVER : RESET_HINT_LOCAL }),
          ])
        : null,
    ], null, {
      icon: "folder",
      collapse: { id: "set.storage", open: false },
      help: [(server ? "Every saved preference, verbatim, as the server holds it. "
                     : "Every saved preference this page holds, verbatim. ")
             + "Resetting puts the console back to defaults; tickets, chats and other data are not touched."],
    });
  }

  /* Reset layout: put pane sizes and fold states back to their defaults and
     nothing else. Exactly three saved preferences are removed; theme, hidden
     tabs and every other key stay. The splitters re-read storage, then the
     active tab is drawn again so folds and sizes show at once (the page
     returns to the top, which is accepted). */
  function layoutPanel() {
    var reset = C.el("button", {
      class: "btn sm", type: "button",
      onclick: function () {
        C.prefs.del("layout");
        C.prefs.del("panelOpen");
        C.prefs.del("chatListHidden");
        if (C.splitter) C.splitter.reapplyAll();
        window.ConsoleApp.go("settings");
        C.toast("Layout reset to defaults", "ok");
      },
    }, ["Reset layout"]);

    return C.panel("Layout", [
      C.el("div", { class: "muted", text: "Pane sizes, folded sections and the Agents chat list go back to their defaults. Theme, hidden tabs and other settings are kept." }),
      C.el("div", { class: "row", style: "margin-top:9px" }, [reset]),
    ], null, {
      icon: "sliders",
      collapse: { id: "set.layout", open: false },
    });
  }

  /* Workspace content on this checkout, and whether a secret path is in git.

     Clean deletes the working tree. The branch others clone still has the
     files until those deletions are committed. Older commits keep them.
     Ticket paths stay committable so a fork can store its own project. */
  function workspace() {
    var body = C.el("div", {}, [C.skeleton(3)]);

    function paint(d) {
      C.clear(body);
      var instance = d.instance || [];
      var secrets = d.secrets || [];
      var hook = d.hook || {};
      var blank = !!d.blank;

      body.appendChild(C.el("div", { class: "row", style: "flex-wrap:wrap;margin-bottom:8px" }, [
        C.chip(blank ? "blank template" : "workspace content present", blank ? "ok" : "warn"),
        C.chip(secrets.length
          ? secrets.length + " secret path" + (secrets.length === 1 ? "" : "s")
          : "no secrets in git",
          secrets.length ? "danger" : "ok"),
        C.chip(hook.active ? "commit hook on" : "commit hook off", hook.active ? "ok" : "warn"),
      ]));

      if (d.note) {
        body.appendChild(C.el("p", { class: "muted", style: "margin:0 0 10px", text: d.note }));
      }

      if (instance.length) {
        body.appendChild(C.el("b", { text: "Still in this checkout" }));
        var shown = instance.slice(0, 20);
        var rows = C.el("div", { class: "rows", style: "margin-top:6px" });
        shown.forEach(function (row) {
          rows.appendChild(C.el("div", { class: "lrow" }, [
            C.chip(row.action),
            C.el("span", { class: "mono", style: "font-size:11.5px", text: row.path }),
          ]));
        });
        body.appendChild(rows);
        if (instance.length > shown.length) {
          body.appendChild(C.el("p", { class: "muted", style: "margin:6px 0 0;font-size:11.5px",
            text: (instance.length - shown.length) + " more" }));
        }
      }

      if (secrets.length) {
        body.appendChild(C.el("b", { text: "Secrets in git", style: "display:block;margin-top:10px" }));
        var srows = C.el("div", { class: "rows", style: "margin-top:6px" });
        secrets.forEach(function (row) {
          srows.appendChild(C.el("div", { class: "lrow" }, [
            C.chip(row.where, "danger"),
            C.el("span", { class: "mono", style: "font-size:11.5px", text: row.path }),
          ]));
        });
        body.appendChild(srows);
      }

      body.appendChild(C.el("p", { class: "muted", style: "margin:10px 0 0;font-size:11.5px" }, [
        hook.detail ? hook.detail + ". " : "",
        hook.active ? null : C.el("code", {}, [hook.command || "git config core.hooksPath .githooks"]),
      ]));

      if (!blank) {
        var input = C.el("input", {
          type: "text",
          placeholder: "type reset",
          "aria-label": "Type reset to confirm",
          style: "min-width:9em",
        });
        var btn = C.el("button", {
          class: "btn sm danger", type: "button", disabled: true,
        }, ["Clean this workspace"]);
        input.addEventListener("input", function () {
          btn.disabled = input.value.trim() !== "reset";
        });
        btn.addEventListener("click", function () {
          btn.disabled = true;
          C.post("/api/workspace/clean", { confirm: "reset" }).then(function () {
            C.toast("Workspace cleaned. Commit the deletions when you want a blank branch.", "ok");
            load();
          }, function (err) {
            C.toast(err.message || "Clean failed", "err");
            btn.disabled = input.value.trim() !== "reset";
          });
        });
        body.appendChild(C.el("div", { class: "row", style: "margin-top:10px;flex-wrap:wrap" }, [
          input, btn,
        ]));
      }
    }

    function load() {
      C.get("/api/workspace").then(paint, function (err) {
        C.clear(body).appendChild(C.errbox(err));
      });
    }

    load();
    return C.panel("Workspace", [body], null, {
      icon: "trash",
      tone: "danger",
      collapse: { id: "set.workspace", open: false },
      help: ["Lists tickets, investigations, logs, telemetry, and cache still "
             + "in this checkout, and any secret path that is tracked or staged. "
             + "Clean deletes the working tree after you type ",
             C.el("code", {}, ["reset"]),
             ". It does not commit. Older commits keep the files. A fork commits its own tickets."],
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
        kids.push(workspace());
      }
      kids.push(identity());
      kids.push(storage(paint));
      kids.push(layoutPanel());
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
