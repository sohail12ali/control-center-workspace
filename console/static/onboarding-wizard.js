/* Setup wizard. One question per screen. Writes the same files Settings
   edits, and can be opened again from Overview or Settings.

   Draft answers live in localStorage so a refresh resumes the screen.
   Key values never do — the draft is a browser store, and a secret does
   not belong in one. */
(function (C) {
  "use strict";

  var STEPS = [
    { id: "workspace", label: "Workspace" },
    { id: "environment", label: "Environment" },
    { id: "files", label: "Editor files" },
    { id: "models", label: "Default models" },
    { id: "review", label: "Review" },
  ];
  var DRAFT_KEY = "onboardingDraft";

  var root = null;
  var state = null;
  var busy = false;
  var lastFocus = null;

  function draftOf(s) {
    return {
      step: s.step,
      name: s.name,
      title: s.title,
      slug: s.slug,
      enabled: s.enabled,
      editors: s.editors,
      backend: s.backend,
      model: s.model,
      workBackend: s.workBackend,
      workModel: s.workModel,
    };
  }

  function saveDraft() {
    if (!state) return;
    C.prefs.set(DRAFT_KEY, draftOf(state));
  }

  function blankFrom(snap, draft) {
    var ws = (snap && snap.workspace) || {};
    var models = (snap && snap.models) || {};
    var enabled = {};
    (snap && snap.providers || []).forEach(function (p) { enabled[p.id] = !!p.enabled; });
    var editors = (snap && snap.editors || []).filter(function (e) { return e.wired; })
      .map(function (e) { return e.id; });
    var s = {
      snap: snap,
      step: 0,
      name: ws.name || ws.git_name || "",
      title: ws.title || ws.committed_title || "",
      slug: ws.slug || "",
      enabled: enabled,
      editors: editors,
      secrets: {},
      backend: models.backend || "",
      model: models.model || "",
      workBackend: models.work_backend || "",
      workModel: models.work_model || "",
    };
    if (!draft || typeof draft !== "object") return s;
    if (typeof draft.step === "number" && draft.step >= 0 && draft.step < STEPS.length) {
      s.step = draft.step;
    }
    ["name", "title", "slug", "backend", "model", "workBackend", "workModel"].forEach(function (k) {
      if (typeof draft[k] === "string") s[k] = draft[k];
    });
    if (draft.enabled && typeof draft.enabled === "object") {
      Object.keys(draft.enabled).forEach(function (id) {
        if (Object.prototype.hasOwnProperty.call(s.enabled, id)) s.enabled[id] = !!draft.enabled[id];
      });
    }
    if (Array.isArray(draft.editors)) {
      var known = {};
      (snap.editors || []).forEach(function (e) { known[e.id] = true; });
      s.editors = draft.editors.filter(function (id) { return known[id]; });
    }
    return s;
  }

  function close() {
    if (!root) return;
    document.removeEventListener("keydown", onKey);
    if (root.parentNode) root.parentNode.removeChild(root);
    root = null;
    state = null;
    busy = false;
    if (lastFocus && lastFocus.isConnected) lastFocus.focus();
    lastFocus = null;
  }

  function onKey(e) {
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); }
  }

  function setBusy(on) {
    busy = on;
    if (!root) return;
    // Only the footer and the close button. Step dots keep the disabled
    // state paint() gave them — a failed save must not unlock later steps.
    root.querySelectorAll("[data-act], .ob-head button").forEach(function (b) {
      b.disabled = on;
    });
  }

  function showError(msg) {
    var el = root && root.querySelector(".ob-error");
    if (!el) return;
    el.hidden = !msg;
    el.textContent = msg || "";
  }

  function applyTitle(snap) {
    var ws = (snap && snap.workspace) || {};
    var title = ws.title || ws.committed_title || "Delivery Console";
    if (window.ConsoleApp && window.ConsoleApp.setTitle) window.ConsoleApp.setTitle(title);
  }

  function postStep(body) {
    setBusy(true);
    showError("");
    return C.post("/api/onboarding/setup", body).then(function (snap) {
      state.snap = snap;
      applyTitle(snap);
      setBusy(false);
      return snap;
    }, function (err) {
      setBusy(false);
      showError(err.message || "Could not save this step");
      throw err;
    });
  }

  function advance() {
    if (state.step < STEPS.length - 1) state.step += 1;
    saveDraft();
    paint();
  }

  function gatherKeys() {
    var keys = {};
    if (!root) return keys;
    root.querySelectorAll("[data-key-env]").forEach(function (input) {
      var value = (input.value || "").trim();
      if (value) keys[input.getAttribute("data-key-env")] = value;
    });
    return keys;
  }

  function continueStep() {
    if (busy || !state) return;
    var id = STEPS[state.step].id;
    if (id === "workspace") {
      state.name = (root.querySelector("[data-field=name]").value || "").trim();
      state.title = (root.querySelector("[data-field=title]").value || "").trim();
      if (!state.name) { showError("Your name is required"); return; }
      var slug = state.name === ((state.snap.workspace || {}).name || "")
        ? (state.snap.workspace || {}).slug || ""
        : "";
      postStep({ step: "workspace", name: state.name, title: state.title, slug: slug })
        .then(function (snap) {
          state.slug = (snap.workspace || {}).slug || "";
          advance();
        }).catch(function () {});
      return;
    }
    if (id === "environment") {
      postStep({ step: "environment", enabled: state.enabled, keys: gatherKeys() })
        .then(advance).catch(function () {});
      return;
    }
    if (id === "files") {
      postStep({ step: "files", editors: state.editors.slice() })
        .then(advance).catch(function () {});
      return;
    }
    if (id === "models") {
      postStep({
        step: "models",
        backend: state.backend,
        model: state.backend ? state.model : "",
        work_backend: state.workBackend,
        work_model: state.workBackend ? state.workModel : "",
      }).then(function (snap) {
        var m = snap.models || {};
        state.backend = m.backend || "";
        state.model = m.model || "";
        state.workBackend = m.work_backend || "";
        state.workModel = m.work_model || "";
        advance();
      }).catch(function () {});
      return;
    }
    setBusy(true);
    C.post("/api/onboarding/complete", {}).then(function () {
      C.prefs.del(DRAFT_KEY);
      close();
      if (window.ConsoleApp) window.ConsoleApp.go("overview");
    }, function (err) {
      setBusy(false);
      showError(err.message || "Could not finish setup");
    });
  }

  function skipStep() {
    if (busy || !state) return;
    var id = STEPS[state.step].id;
    if (id !== "environment" && id !== "files") return;
    advance();
  }

  function field(label, hint, attrs) {
    var input = C.el("input", attrs);
    return C.el("label", { class: "ob-field" }, [
      C.el("span", { class: "ob-label", text: label }),
      hint ? C.el("span", { class: "muted", text: hint }) : null,
      input,
    ]);
  }

  function screenWorkspace() {
    var ws = state.snap.workspace || {};
    var hint = ws.git_name && !ws.name
      ? "Git already says “" + ws.git_name + "”. Change it if work logs should use another name."
      : "Work logs are attributed to this name.";
    return C.el("div", {}, [
      C.el("h2", { text: "Who is this console for?" }),
      C.el("p", { class: "muted ob-lead", text: "The name on your work logs, and the name in the header. You can change both later in Settings." }),
      field("Your name", hint, {
        type: "text", "data-field": "name", value: state.name, autocomplete: "name",
        oninput: function (e) { state.name = e.target.value; saveDraft(); showError(""); },
      }),
      field("Console name", "Shown in the header and the browser tab. Leave blank to keep the name this workspace already ships with.", {
        type: "text", "data-field": "title", value: state.title,
        oninput: function (e) { state.title = e.target.value; saveDraft(); },
      }),
    ]);
  }

  function keyField(p, aria, placeholder, tone, suffix) {
    return C.el("div", { class: "ob-key" }, [
      C.chip(p.key_env + suffix, tone),
      tone === "ok"
        ? C.el("span", { class: "muted", text: "Type a new value only to replace it. The current value is never shown." })
        : null,
      C.el("input", {
        type: "password", "data-key-env": p.key_env, autocomplete: "off",
        "aria-label": aria, placeholder: placeholder,
        value: state.secrets[p.key_env] || "",
        oninput: function (e) { state.secrets[p.key_env] = e.target.value; },
      }),
    ]);
  }

  function screenEnvironment() {
    var providers = state.snap.providers || [];
    var clis = state.snap.clis || [];
    var tiles = providers.map(function (p) {
      var on = !!state.enabled[p.id];
      var key = null;
      if (on && p.needs_key) {
        if (p.has_key) {
          key = keyField(p, "Replace " + p.key_env, "Leave blank to keep it", "ok", " is set");
        } else {
          key = keyField(p, p.key_env, p.key_env, "warn", " is missing");
        }
      }
      return C.el("div", { class: "ob-tilewrap" + (on ? " on" : "") }, [
        C.el("button", {
          type: "button", class: "ob-tile", "aria-pressed": on ? "true" : "false",
          onclick: function () {
            state.enabled[p.id] = !state.enabled[p.id];
            saveDraft();
            paint();
          },
        }, [
          C.el("b", { text: p.label }),
          C.el("span", { class: "muted", text: p.is_local ? "On this machine" : (p.needs_key ? "Needs a key" : "Hosted") }),
        ]),
        key,
      ]);
    });
    return C.el("div", {}, [
      C.el("h2", { text: "Which models can this machine use?" }),
      C.el("p", { class: "muted ob-lead", text: "Turn providers on. A key is saved in .env and is not shown again. Skip if you will add keys later — the board works without them." }),
      providers.length
        ? C.el("div", { class: "ob-tiles" }, tiles)
        : C.el("p", { class: "muted", text: "No API providers are configured in agents.toml." }),
      clis.length
        ? C.el("p", { class: "ob-note" }, [
            C.el("span", { class: "muted", text: "Already on PATH: " }),
            clis.map(function (c) { return C.chip(c.label, "ok"); }),
          ])
        : null,
    ]);
  }

  function screenFiles() {
    var editors = state.snap.editors || [];
    return C.el("div", {}, [
      C.el("h2", { text: "Which editors should know about this console?" }),
      C.el("p", { class: "muted ob-lead", text: "Writes the console MCP entry into that editor’s project config, and a short note in AGENTS.md. Other servers already in those files are left alone." }),
      C.el("div", { class: "ob-tiles" }, editors.map(function (e) {
        var on = state.editors.indexOf(e.id) !== -1;
        return C.el("button", {
          type: "button", class: "ob-tile", "aria-pressed": on ? "true" : "false",
          onclick: function () {
            var i = state.editors.indexOf(e.id);
            if (i === -1) state.editors.push(e.id);
            else state.editors.splice(i, 1);
            saveDraft();
            paint();
          },
        }, [
          C.el("b", { text: e.label }),
          C.el("span", { class: "muted", text: e.wired ? e.path + " — already connected" : e.path }),
        ]);
      })),
    ]);
  }

  function roleSelect(kind, backendKey, modelKey) {
    var choices = (state.snap.models && state.snap.models.choices) || [];
    var backend = state[backendKey];
    var selected = null;
    choices.forEach(function (c) { if (c.id === backend) selected = c; });
    var backendSel = C.el("select", {
      "aria-label": kind + " provider",
      onchange: function (e) {
        state[backendKey] = e.target.value;
        state[modelKey] = "";
        saveDraft();
        paint();
      },
    }, [
      C.el("option", { value: "", text: "Automatic (local first)" }),
      choices.map(function (c) {
        return C.el("option", { value: c.id, text: c.label, selected: c.id === backend ? "selected" : null });
      }),
    ]);
    var modelSel = null;
    if (backend) {
      var models = ((selected && selected.models) || []).slice();
      if (state[modelKey] && models.indexOf(state[modelKey]) === -1) {
        models.unshift(state[modelKey]);
      }
      modelSel = C.el("select", {
        "aria-label": kind + " model",
        onchange: function (e) { state[modelKey] = e.target.value; saveDraft(); },
      }, [
        C.el("option", { value: "", text: "Backend default" }),
        models.map(function (entry) {
          var id = typeof entry === "string" ? entry : (entry && entry.id) || "";
          var text = typeof entry === "string" ? entry : (entry && (entry.label || entry.id)) || id;
          if (!id) return null;
          return C.el("option", { value: id, text: text, selected: id === state[modelKey] ? "selected" : null });
        }),
      ]);
    }
    return C.el("div", { class: "ob-role" }, [
      C.el("span", { class: "ob-label", text: kind }),
      C.el("span", { class: "muted", text: kind === "Talk"
        ? "Conversation, status, ticket lookups."
        : "Code changes, builds, and test runs." }),
      backendSel,
      modelSel,
    ]);
  }

  function screenModels() {
    return C.el("div", {}, [
      C.el("h2", { text: "Which models should be the default?" }),
      C.el("p", { class: "muted ob-lead", text: "Talk answers quickly. Work does the engineering. Automatic picks the first ready local model, then a hosted one. The lists are providers you turned on, plus CLIs already on PATH." }),
      roleSelect("Talk", "backend", "model"),
      roleSelect("Work", "workBackend", "workModel"),
    ]);
  }

  function screenReview() {
    var rows = (state.snap.review || []).map(function (row) {
      return C.el("div", { class: "ob-review" }, [
        C.el("b", { text: row.label }),
        C.el("span", { text: row.value }),
        C.el("span", { class: "muted", text: row.where }),
      ]);
    });
    return C.el("div", {}, [
      C.el("h2", { text: "You’re set up" }),
      C.el("p", { class: "muted ob-lead", text: "These are the same settings Settings edits. Change any of them there, or run this setup again." }),
      C.el("div", { class: "ob-reviews" }, rows),
    ]);
  }

  var SCREENS = {
    workspace: screenWorkspace,
    environment: screenEnvironment,
    files: screenFiles,
    models: screenModels,
    review: screenReview,
  };

  function paint() {
    var body = root.querySelector(".ob-body");
    var step = STEPS[state.step];
    C.clear(body);
    var screen = C.el("div", { class: "ob-screen" }, [SCREENS[step.id]()]);
    body.appendChild(screen);

    var dots = root.querySelector(".ob-dots");
    C.clear(dots);
    STEPS.forEach(function (s, i) {
      var cls = "ob-dot";
      if (i === state.step) cls += " on";
      else if (i < state.step) cls += " done";
      dots.appendChild(C.el("button", {
        type: "button", class: cls, title: s.label,
        "aria-label": s.label + (i === state.step ? ", current" : ""),
        "aria-current": i === state.step ? "step" : null,
        disabled: i > state.step,
        onclick: function () {
          if (i < state.step) { state.step = i; saveDraft(); paint(); }
        },
      }));
    });

    var count = root.querySelector(".ob-count");
    count.textContent = "Step " + (state.step + 1) + " of " + STEPS.length + ", " + step.label;

    var back = root.querySelector("[data-act=back]");
    back.hidden = state.step === 0;
    var skip = root.querySelector("[data-act=skip]");
    skip.hidden = step.id !== "environment" && step.id !== "files";
    var next = root.querySelector("[data-act=next]");
    next.textContent = step.id === "review" ? "Done" : "Continue";

    var focus = body.querySelector("input, select, button");
    if (focus) focus.focus();
  }

  function mount(snap) {
    if (root) return;
    lastFocus = document.activeElement;
    var draft = C.prefs.get(DRAFT_KEY, null);
    state = blankFrom(snap, draft);
    root = C.el("div", { class: "ob-scrim", role: "presentation" }, [
      C.el("div", {
        class: "ob-panel", role: "dialog", "aria-modal": "true", "aria-labelledby": "ob-title",
      }, [
        C.el("header", { class: "ob-head" }, [
          C.el("div", {}, [
            C.el("div", { class: "ob-kicker", text: "Setup" }),
            C.el("div", { class: "sr-only", id: "ob-title", text: "Console setup" }),
            C.el("div", { class: "ob-dots", role: "tablist", "aria-label": "Setup steps" }),
          ]),
          C.el("button", {
            type: "button", class: "btn sm iconly", "aria-label": "Close setup",
            onclick: close,
          }, [C.icon("x")]),
        ]),
        C.el("p", { class: "sr-only ob-count", "aria-live": "polite" }),
        C.el("div", { class: "ob-body" }),
        C.el("p", { class: "ob-error", hidden: true, role: "alert" }),
        C.el("footer", { class: "ob-foot" }, [
          C.el("button", { type: "button", class: "btn", "data-act": "back", onclick: function () {
            if (busy || state.step === 0) return;
            state.step -= 1;
            saveDraft();
            paint();
          } }, ["Back"]),
          C.el("span", { class: "grow" }),
          C.el("button", { type: "button", class: "btn", "data-act": "skip", onclick: skipStep }, ["Skip"]),
          C.el("button", { type: "button", class: "btn primary", "data-act": "next", onclick: continueStep }, ["Continue"]),
        ]),
      ]),
    ]);
    document.body.appendChild(root);
    document.addEventListener("keydown", onKey);
    paint();
  }

  function open(prefetched) {
    if (C.IS_STATIC) return;
    if (root) return;
    if (prefetched && prefetched.steps) { mount(prefetched); return; }
    C.get("/api/onboarding/setup").then(mount, function (err) {
      C.toast(err.message || "Setup is unavailable", "err");
    });
  }

  function maybeOpen() {
    if (C.IS_STATIC) return;
    C.get("/api/onboarding/setup").then(function (snap) {
      if (snap && snap.should_open) mount(snap);
    }).catch(function () { /* plugin off, or the server is down — the board still opens */ });
  }

  window.ConsoleOnboarding = { open: open, maybeOpen: maybeOpen };
})(window.Console);
