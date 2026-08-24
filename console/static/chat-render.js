/* Incremental transcript rendering.

   One DOM node per store item, remembered by key, so a token delta patches
   one text node instead of rebuilding the conversation. That distinction is
   the whole reason this file exists: repainting a long transcript on every
   delta drops frames and destroys text selection mid-read.

   Thinking blocks and tool calls are collapsed by default. They matter when
   something goes wrong and are noise when it doesn't, so they are present but
   folded, with the summary carrying enough (tool name, target file) to decide
   whether to open one. */
window.ConsoleChatRender = (function (C, MD) {
  "use strict";

  var MAX_RESULT = 4000;

  function shortArgs(item) {
    var a = item.args || {};
    var p = a.file_path || a.path || a.notebook_path || a.pattern || a.command || a.url || "";
    if (p) return String(p).length > 70 ? "…" + String(p).slice(-68) : String(p);
    if (a.prompt) return String(a.prompt).slice(0, 60);
    var keys = Object.keys(a);
    return keys.length ? keys.slice(0, 3).join(", ") : "";
  }

  function toolIcon(name) {
    var n = (name || "").toLowerCase();
    if (/read|glob|grep|search/.test(n)) return "search";
    if (/write|edit|notebook/.test(n)) return "pencil";
    if (/bash|shell|powershell|run/.test(n)) return "cpu";
    if (/todo/.test(n)) return "list";
    if (/web|fetch/.test(n)) return "external";
    return "wrench";
  }

  /* ---------------- per-item builders ---------------- */
  function userItem(item) {
    var node = C.el("div", { class: "ct-item ct-user" + (item.steered ? " ct-steered" : "") }, [
      C.el("div", { class: "ct-who" }, [
        item.steered ? C.icon("steer") : C.icon("user"),
        C.el("span", { text: item.steered ? "you · steered mid-turn" : "you" }),
      ]),
      C.el("div", { class: "ct-bubble", text: item.text }),
    ]);
    if (item.wire) {
      // The composed text differs from what was typed (a backend without
      // slash commands rewrites it). Show what was typed, keep the wire text
      // one click away rather than presenting it as the person's words.
      node.appendChild(C.el("details", { class: "ct-wire" }, [
        C.el("summary", { class: "muted", text: "sent as" }),
        C.el("pre", { class: "code", text: item.wire }),
      ]));
    }
    return node;
  }

  function textItem(item) {
    var body = C.el("div", { class: "ct-md" });
    body.appendChild(MD.render(item.text));
    var node = C.el("div", { class: "ct-item ct-assistant" }, [body]);
    node._body = body;
    return node;
  }

  function thinkingItem(item) {
    var pre = C.el("div", { class: "ct-think-body", text: item.text });
    var node = C.el("details", { class: "ct-item ct-think" }, [
      C.el("summary", {}, [C.icon("brain"), C.el("span", { text: "thinking" })]),
      pre,
    ]);
    node._body = pre;
    return node;
  }

  function toolItem(item) {
    var head = C.el("summary", { class: "ct-toolhead" }, [
      C.icon(toolIcon(item.name)),
      C.el("span", { class: "ct-toolname", text: item.name || "tool" }),
      C.el("span", { class: "ct-toolarg truncate", text: shortArgs(item) }),
    ]);
    var body = C.el("div", { class: "ct-toolbody" });
    var node = C.el("details", { class: "ct-item ct-tool" }, [head, body]);
    node._head = head;
    node._body = body;
    paintToolBody(node, item);
    return node;
  }

  function paintToolBody(node, item) {
    var body = C.clear(node._body);
    if (item.args && Object.keys(item.args).length) {
      body.appendChild(C.el("pre", { class: "code ct-args", text: JSON.stringify(item.args, null, 2).slice(0, 3000) }));
    } else if (item.argText) {
      body.appendChild(C.el("pre", { class: "code ct-args muted", text: item.argText.slice(0, 2000) }));
    }
    if (item.result) {
      body.appendChild(C.el("div", { class: "ct-resulthead" }, [
        item.result.ok ? C.icon("check") : C.icon("alert"),
        C.el("span", { text: item.result.ok ? "result" : "error" }),
      ]));
      body.appendChild(C.el("pre", {
        class: "code ct-result" + (item.result.ok ? "" : " bad"),
        text: (item.result.content || "").slice(0, MAX_RESULT) || "(empty)",
      }));
    }
    // Update the summary too: the tool name arrives before its args do.
    if (node._head) {
      var arg = node._head.querySelector(".ct-toolarg");
      var nm = node._head.querySelector(".ct-toolname");
      if (arg) arg.textContent = shortArgs(item);
      if (nm) nm.textContent = item.name || "tool";
      node._head.classList.toggle("bad", !!(item.result && !item.result.ok));
    }
  }

  /* The one interactive transcript item: a gated tool call parked on a human.
     Buttons answer via the approve endpoint; the server's approval.decided
     event patches the card into its settled form for every viewer. */
  function approvalItem(item) {
    var node = C.el("div", { class: "ct-item" });
    node._body = node;
    paintApproval(node, item);
    return node;
  }

  function paintApproval(node, item) {
    var a = item.approval || {};
    C.clear(node);
    if (a.decided) {
      node.appendChild(C.el("div", { class: "ct-approval decided" }, [
        C.icon(a.decided === "deny" ? "alert" : "check"),
        C.el("span", {}, [
          C.el("b", { text: a.tool || "tool" }),
          " — " + (a.decided === "deny" ? "denied" : "allowed") + (a.by ? " by " + a.by : ""),
        ]),
      ]));
      return;
    }
    var row = C.el("div", { class: "row ct-appbtns" });
    function btn(label, decision, cls) {
      return C.el("button", { class: cls, onclick: function () {
        row.querySelectorAll("button").forEach(function (b) { b.disabled = true; });
        C.post("/api/agents/chats/" + encodeURIComponent(item.sid || "") + "/approve",
               { key: a.key, decision: decision })
          .catch(function (err) {
            C.toast(err.message, "err");
            row.querySelectorAll("button").forEach(function (b) { b.disabled = false; });
          });
      } }, [label]);
    }
    C.append(row, [
      btn("Allow once", "allow", "btn primary sm"),
      btn("Allow for this chat", "allow-session", "btn sm"),
      C.el("span", { class: "grow" }),
      btn("Deny", "deny", "btn danger sm"),
    ]);
    node.appendChild(C.el("div", { class: "ct-approval pending" }, [
      C.el("div", { class: "ct-apphead" }, [
        C.icon("alert"),
        C.el("b", { text: "Permission needed" }),
        C.el("span", { class: "chip warn", text: a.tool || "tool" }),
      ]),
      C.el("pre", { class: "code ct-args", text: JSON.stringify(a.input || {}, null, 2).slice(0, 3000) }),
      row,
    ]));
  }

  function systemItem(item) {
    if (item.kind === "approval") return approvalItem(item);
    if (item.kind === "turnend") {
      var bits = [];
      if (item.cost) bits.push("$" + item.cost.toFixed(4));
      if (item.ms) bits.push(Math.round(item.ms / 100) / 10 + "s");
      return C.el("div", { class: "ct-rule" + (item.is_error ? " bad" : "") }, [
        C.el("span", { text: item.is_error ? "turn failed" : "turn complete" }),
        bits.length ? C.el("span", { class: "muted", text: bits.join(" · ") }) : null,
      ]);
    }
    if (item.kind === "interrupt") {
      return C.el("div", { class: "ct-rule warn" }, [
        C.icon("stop"), C.el("span", { text: "interrupted" + (item.via ? " (" + item.via + ")" : "") }),
      ]);
    }
    if (item.kind === "exit") {
      var msg = "session ended" + (item.code === null || item.code === undefined ? "" : " (exit " + item.code + ")");
      if (item.dropped) msg += " — " + item.dropped + " queued message(s) dropped";
      return C.el("div", { class: "ct-rule" }, [C.el("span", { text: msg })]);
    }
    if (item.kind === "error") {
      return C.el("div", { class: "ct-item" }, [C.el("div", { class: "errbox", text: item.text })]);
    }
    if (item.kind === "notice") {
      return C.el("div", { class: "ct-note " + (item.level || "info") }, [
        C.icon(item.level === "warn" ? "alert" : "info"),
        C.el("span", { text: item.text }),
      ]);
    }
    return C.el("details", { class: "ct-item ct-tool" }, [
      C.el("summary", { class: "ct-toolhead muted" }, [C.icon("info"), "unrecognised event"]),
      C.el("pre", { class: "code", text: item.text || "" }),
    ]);
  }

  function build(item) {
    if (item.role === "user") return userItem(item);
    if (item.role === "system") return systemItem(item);
    if (item.kind === "thinking") return thinkingItem(item);
    if (item.kind === "tool") return toolItem(item);
    return textItem(item);
  }

  /** Attach a renderer to a scroll host for one store. */
  function mount(host, store, opts) {
    opts = opts || {};
    var nodes = {};
    var stick = true;

    function atBottom() {
      return host.scrollHeight - host.scrollTop - host.clientHeight < 40;
    }
    host.addEventListener("scroll", function () { stick = atBottom(); });

    function scroll(force) {
      if (force || stick) host.scrollTop = host.scrollHeight;
    }

    function addNode(item) {
      var node = build(item);
      nodes[item.key] = node;
      host.appendChild(node);
      scroll(false);
    }

    function patchNode(item) {
      var node = nodes[item.key];
      if (!node) return;
      if (item.kind === "text") {
        // Re-render just this block's markdown. Cheap: one block, not the
        // transcript, and markdown needs the whole block to parse fences.
        var fresh = MD.render(item.text);
        C.clear(node._body).appendChild(fresh);
      } else if (item.kind === "thinking") {
        node._body.textContent = item.text;
      } else if (item.kind === "tool") {
        paintToolBody(node, item);
      } else if (item.kind === "approval") {
        paintApproval(node, item);
      }
      scroll(false);
    }

    var offItem = store.on("item", addNode);
    var offPatch = store.on("patch", patchNode);

    function renderAll() {
      C.clear(host);
      nodes = {};
      store.state.items.forEach(addNode);
      scroll(true);
    }

    return {
      renderAll: renderAll,
      scroll: scroll,
      destroy: function () { offItem(); offPatch(); },
      lastAssistantText: function () {
        var items = store.state.items;
        for (var i = items.length - 1; i >= 0; i--) {
          if (items[i].role === "assistant" && items[i].kind === "text") return items[i].text;
        }
        return "";
      },
    };
  }

  return { mount: mount, build: build };
})(window.Console, window.ConsoleMarkdown);
