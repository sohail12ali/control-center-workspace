/* Todos tab — every todo across every ticket, plus unscoped ones.

   Rebuilt around the gesture people actually want: tick a box. The previous
   version made each ticket a full panel (a header, a border and padding for
   one or two short lines) and hid the only action inside a status chip that
   looked like a label. Here the checkbox is the primary control, the ticket
   is a lightweight group heading rather than a panel, and the list keeps a
   readable line length instead of stretching a six-word todo across 1300px.

   Status model is unchanged — open / doing / done / dropped, written through
   the same tracker-update route the ticket drawer uses, so there is still one
   write path. The checkbox covers open↔done because that is the common case;
   "doing" gets its own explicit control rather than being a hidden third
   state you reach by clicking twice. */
(function (C) {
  "use strict";

  var CLOSED = ["done", "dropped"];
  var GENERAL = "_shared";
  var st = {
    items: [], scopes: [], status: "open", owner: "", query: "",
    host: null, api: null, busy: {}, newScope: GENERAL, newText: "",
  };

  function isClosed(it) { return CLOSED.indexOf(it.status) !== -1; }

  function scopeLabel(id) {
    var s = st.scopes.filter(function (x) { return x.id === id; })[0];
    return s ? s.label : id;
  }

  function counts(items) {
    var c = { all: items.length, open: 0, doing: 0, done: 0, dropped: 0 };
    items.forEach(function (i) { if (c[i.status] !== undefined) c[i.status]++; });
    return c;
  }

  function key(item) { return item.scope + "/" + item.id; }

  /* Every mutation goes through here so the busy-guard, the toast and the
     reload are identical no matter which control fired. General todos are
     now an ordinary tracker under the `_shared` scope, so they are writable
     on exactly the same path as a ticket's — no read-only special case. */
  function mutate(item, run, label) {
    if (C.IS_STATIC) { C.toast("This is a snapshot — it is read-only.", "err"); return; }
    var k = key(item);
    if (st.busy[k]) return;               // ignore a double-click mid-write
    st.busy[k] = true;
    paint();
    run()
      .then(function () {
        if (label) C.toast(label, "ok");
        if (st.api) st.api.refreshBadges();
        return reload();
      })
      .catch(function (e) { C.toast(e.message, "err"); })
      .then(function () { delete st.busy[k]; paint(); });
  }

  function setStatus(item, next) {
    mutate(item, function () {
      return C.post("/api/ticket/" + encodeURIComponent(item.scope) +
                    "/trackers/todos/" + encodeURIComponent(item.id), { status: next });
    }, item.id + " → " + next);
  }

  function moveTo(item, target) {
    mutate(item, function () {
      return C.post("/api/todos/" + encodeURIComponent(item.scope) + "/" +
                    encodeURIComponent(item.id) + "/move", { to: target });
    }, "Moved to " + (target === GENERAL ? "General" : target));
  }

  function removeTodo(item) {
    mutate(item, function () {
      return C.post("/api/todos/" + encodeURIComponent(item.scope) + "/" +
                    encodeURIComponent(item.id) + "/delete", {});
    }, "Deleted " + item.id);
  }

  /* ---------------- row ---------------- */
  function todoRow(item) {
    var done = isClosed(item);
    var doing = item.status === "doing";
    var locked = C.IS_STATIC;
    var working = !!st.busy[key(item)];

    var box = C.el("input", {
      type: "checkbox", class: "todobox",
      "aria-label": (done ? "Reopen" : "Complete") + ": " + item.text,
      title: locked ? "This is a read-only snapshot"
                    : (done ? "Reopen this todo" : "Mark done"),
    });
    box.checked = done;
    box.disabled = locked || working;
    box.addEventListener("change", function () {
      setStatus(item, done ? "open" : "done");
    });

    var meta = C.el("div", { class: "todometa" });
    if (item.priority && item.priority !== "medium") {
      meta.appendChild(C.el("span", {
        class: "chip " + (item.priority === "high" || item.priority === "critical" ? "danger" : ""),
        title: "Priority",
      }, [item.priority]));
    }
    if (item.due) meta.appendChild(C.el("span", { class: "chip", title: "Due" }, [C.icon("clock"), item.due]));
    // Only when it says something. "task" is the default every todo gets, so
    // rendering it put an identical chip on every row — noise that costs
    // horizontal space and carries no information.
    if (item.type && item.type !== "task" && item.type !== "other") {
      meta.appendChild(C.el("span", { class: "chip", title: "Type", text: item.type }));
    }
    meta.appendChild(C.el("span", { class: "todoid mono", title: "Tracker id", text: item.id }));

    /* "Doing" is a deliberate, separate control. Folding it into the checkbox
       would mean clicking twice to complete something, and clicking once to
       land in a state you didn't ask for. Hidden on closed items — you don't
       start something you've finished. */
    var startBtn = null;
    if (!done && !locked) {
      startBtn = C.el("button", {
        class: "todostart" + (doing ? " on" : ""),
        title: doing ? "Back to open" : "Mark in progress",
        "aria-pressed": String(doing),
        onclick: function () { setStatus(item, doing ? "open" : "doing"); },
      }, [C.icon(doing ? "play" : "circle"), C.el("span", { text: doing ? "doing" : "start" })]);
    }

    /* Move and delete. A <select> rather than a drag target: moving a todo
       to one of a dozen tickets by dragging across a grouped list is fiddly,
       and the destination list is exactly what a select is for. It resets to
       its placeholder after firing so it reads as an action, not a state. */
    var actions = null;
    if (!locked) {
      var sel = C.el("select", {
        class: "todomove", "aria-label": "Move this todo",
        title: "Move to another ticket, or out to General",
        onchange: function (e) {
          var target = e.target.value;
          e.target.selectedIndex = 0;
          if (target) moveTo(item, target);
        },
      }, [C.el("option", { value: "" }, ["move…"])].concat(
        st.scopes.filter(function (s) { return s.id !== item.scope; }).map(function (s) {
          return C.el("option", { value: s.id }, [s.general ? "General (no ticket)" : s.label]);
        })
      ));

      actions = C.el("div", { class: "todoacts" }, [
        sel,
        C.el("button", {
          class: "tododel", title: "Delete this todo", "aria-label": "Delete " + item.text,
          onclick: function () { removeTodo(item); },
        }, [C.icon("trash")]),
      ]);
    }

    var cls = "todoitem";
    if (done) cls += " done";
    if (doing) cls += " doing";
    if (working) cls += " working";

    return C.el("div", { class: cls }, [
      C.el("label", { class: "todocheck" }, [box, C.el("span", { class: "tick" }, [C.icon("check")])]),
      C.el("div", { class: "todotext", text: item.text }),
      startBtn,
      meta,
      actions,
    ]);
  }

  /* ---------------- groups ----------------
     A hairline heading, not a panel. Most tickets have one or two todos, so a
     bordered card per ticket was mostly chrome. */
  function group(label, items, api) {
    var head = C.el("div", { class: "todogroup-h" }, [
      label === null
        ? C.el("span", { class: "gname muted", text: "General (no ticket)" })
        : C.el("button", {
            class: "gname link-ish", title: "Open the tickets board",
            onclick: function () { if (api) api.go("board:tickets"); },
          }, [label]),
      C.el("span", { class: "ghair" }),
      C.el("span", { class: "gcount", text: String(items.length) }),
    ]);
    var list = C.el("div", { class: "todoitems" });
    items.forEach(function (i) { list.appendChild(todoRow(i)); });
    return C.el("section", { class: "todogroup" }, [head, list]);
  }

  /* Capture box. Defaults to General because that is what a todo with no
     home is — you jot it now and file it later, which is exactly what the
     move control is for. */
  function addForm() {
    var input = C.el("input", {
      type: "text", class: "todoadd-text", placeholder: "Add a todo…",
      value: st.newText, "aria-label": "New todo",
      oninput: function (e) { st.newText = e.target.value; },
    });

    function submit() {
      var text = st.newText.trim();
      if (!text) return;
      input.disabled = true;
      C.post("/api/todos", { text: text, scope: st.newScope })
        .then(function () {
          st.newText = "";
          C.toast("Added to " + (st.newScope === GENERAL ? "General" : st.newScope), "ok");
          if (st.api) st.api.refreshBadges();
          return reload();
        })
        .catch(function (e) { C.toast(e.message, "err"); input.disabled = false; });
    }
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") submit(); });

    var scopeSel = C.el("select", {
      "aria-label": "Where this todo belongs", class: "todoadd-scope",
      onchange: function (e) { st.newScope = e.target.value; },
    }, st.scopes.map(function (s) {
      return C.el("option", { value: s.id, selected: s.id === st.newScope || null },
        [s.general ? "General (no ticket)" : s.label]);
    }));

    return C.el("div", { class: "todoadd" }, [
      C.icon("list"),
      input,
      scopeSel,
      C.el("button", { class: "btn sm primary", onclick: submit }, ["Add"]),
    ]);
  }

  /* ---------------- paint ---------------- */
  function paint() {
    var host = C.clear(st.host);
    var all = st.items;
    var c = counts(all);

    var seg = C.el("div", { class: "seg" });
    [["open", "Open"], ["doing", "Doing"], ["done", "Done"], ["dropped", "Dropped"], ["all", "All"]]
      .forEach(function (pair) {
        seg.appendChild(C.el("button", {
          "aria-pressed": String(st.status === pair[0]),
          onclick: function () { st.status = pair[0]; paint(); },
        }, [
          pair[1],
          C.el("span", { class: "segn", text: String(c[pair[0]] === undefined ? 0 : c[pair[0]]) }),
        ]));
      });

    var owners = all.map(function (i) { return i.owner || ""; })
      .filter(function (v, i, arr) { return v && arr.indexOf(v) === i; }).sort();
    var bar = C.el("div", { class: "todobar" }, [seg]);
    if (owners.length > 1) {
      bar.appendChild(C.el("select", {
        "aria-label": "Filter by owner", style: "width:auto;min-width:130px",
        onchange: function (e) { st.owner = e.target.value; paint(); },
      }, [C.el("option", { value: "" }, ["All owners"])].concat(owners.map(function (o) {
        return C.el("option", { value: o, selected: o === st.owner || null }, [o]);
      }))));
    }
    bar.appendChild(C.el("span", { class: "grow" }));
    if (st.query) bar.appendChild(C.el("span", { class: "chip info", text: "filter: " + st.query }));
    host.appendChild(bar);

    if (!C.IS_STATIC) host.appendChild(addForm());

    var q = st.query.toLowerCase();
    var shown = all.filter(function (i) {
      if (st.status !== "all" && i.status !== st.status) return false;
      if (st.owner && (i.owner || "") !== st.owner) return false;
      if (q && (i.text + " " + i.id + " " + (i.ticket || "")).toLowerCase().indexOf(q) === -1) return false;
      return true;
    });

    var wrap = C.el("div", { class: "todolist" });
    host.appendChild(wrap);

    if (!shown.length) {
      wrap.appendChild(C.empty(
        st.status === "open" ? "Nothing waiting" : "No " + st.status + " todos",
        st.status === "open"
          ? "Add one with:  python console/kanban.py tracker add {T} todos \"…\""
          : "Try another filter.",
        st.status === "open" ? "check" : "inbox"
      ));
      return;
    }

    // Group by ticket, unscoped last. Sorting the key with a high codepoint
    // sentinel keeps "general" at the bottom without a second pass.
    var groups = {};
    shown.forEach(function (i) {
      var k = i.ticket || "￿";
      (groups[k] = groups[k] || []).push(i);
    });
    Object.keys(groups).sort().forEach(function (k) {
      wrap.appendChild(group(k === "￿" ? null : k, groups[k], st.api));
    });
  }

  function reload() {
    return Promise.all([C.get("/api/todos"), C.get("/api/todos/scopes")])
      .then(function (res) {
        st.items = res[0];
        st.scopes = (res[1] || {}).scopes || [];
        if (!st.scopes.some(function (s) { return s.id === st.newScope; })) {
          st.newScope = (st.scopes[0] || {}).id || GENERAL;
        }
        paint();
        return st.items;
      }).catch(function (err) {
        C.clear(st.host).appendChild(C.errbox(err));
      });
  }

  C.tab("todos", {
    render: function (host, api) {
      st.host = host;
      st.api = api;
      C.clear(host).appendChild(C.skeleton(5));
      reload();
    },
    onSearch: function (q) { st.query = q; if (st.host && st.items.length) paint(); },
    onLeave: function () { st.query = ""; },
  });
})(window.Console);
