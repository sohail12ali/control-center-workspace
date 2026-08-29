/* Chat state + SSE subscription.

   Separated from rendering because they change for different reasons: the
   reducer follows the server's event vocabulary, the renderer follows what
   looks right. Mixing them produced a repaint-everything-on-every-delta loop
   in the version this replaces.

   Reconnect contract, which is the whole reason events carry `seq`:
   - subscribe with ?from=<last seq we have>
   - a `stream.reset` means the server can no longer prove contiguity, so we
     re-fetch the transcript and resubscribe from its head rather than
     silently carrying a hole in the middle of a turn.

   The store keeps a flat `items` list — the transcript in order — where each
   item is one renderable thing (a user message, an assistant text block, a
   thinking block, a tool call). Deltas mutate the item in place and notify
   listeners with just that item, so a token append touches one node. */
window.ConsoleChatStore = (function (C) {
  "use strict";

  /* Exactly ONE event stream may exist console-wide.

     Not tidiness — a correctness requirement. Each SSE connection holds one
     of the browser's ~6 per-origin HTTP/1.1 slots for as long as the chat
     lives, so a handful of leaked streams silently exhausts the pool and
     every ordinary request then hangs rather than failing. Careful
     open/close discipline in the caller is not enough on its own: a reconnect
     racing a chat switch can double-subscribe. This module-level handle makes
     the invariant structural — opening a stream always closes whatever was
     open first. */
  var activeStream = null;

  function claimStream(es) {
    if (activeStream && activeStream !== es) {
      try { activeStream.close(); } catch (e) { /* already gone */ }
    }
    activeStream = es;
  }

  function releaseStream(es) {
    if (es) { try { es.close(); } catch (e) { /* already gone */ } }
    if (activeStream === es) activeStream = null;
  }

  function create(chatId) {
    var st = {
      id: chatId,
      items: [],
      byBlock: {},        // block id -> item
      byTool: {},         // tool id  -> item
      head: 0,
      snapshot: null,
      queued: [],
      busy: false,
      alive: true,
      todos: [],
      plan: "",
      files: [],          // paths the agent touched, derived from tool args
      // Tool-call rounds used in the CURRENT turn, for backends that report
      // them (the console's own API loop does; a CLI's rounds are its own
      // business and it never says). Reset per turn because the cap is a
      // per-turn cap — carrying it across turns would show pressure that has
      // already been released.
      toolRound: 0,
      usage: { cost: 0, tokens_in: 0, tokens_out: 0, turns: 0 },
      approvals: {},      // approval key -> {tool, input, decided, by, item}
      replaying: false,   // true while load() replays history — listeners that
                          // announce or speak must stay quiet for old events
      es: null,
      closed: false,
      listeners: { item: [], patch: [], meta: [], end: [] },
    };

    function on(kind, fn) { st.listeners[kind].push(fn); return function () { off(kind, fn); }; }
    function off(kind, fn) {
      st.listeners[kind] = st.listeners[kind].filter(function (f) { return f !== fn; });
    }
    function emit(kind, arg) {
      st.listeners[kind].slice().forEach(function (fn) {
        try { fn(arg); } catch (e) { /* a bad listener must not stop the stream */ }
      });
    }

    function addItem(item) {
      item.key = "i" + st.items.length;
      st.items.push(item);
      emit("item", item);
      return item;
    }

    /* ---------------- the reducer ---------------- */
    function apply(ev) {
      var t = ev.type;
      if (ev.seq) st.head = Math.max(st.head, ev.seq);

      switch (t) {
        case "session.started":
          st.meta = ev;
          emit("meta", st);
          return;

        case "session.init":
          if (ev.model) { st.model = ev.model; emit("meta", st); }
          return;

        case "turn.start":
          st.busy = true;
          st.toolRound = 0;
          addItem({ role: "user", text: ev.text, wire: ev.wire || "", steered: false });
          emit("meta", st);
          return;

        case "turn.steer":
          addItem({ role: "user", text: ev.text, wire: ev.wire || "", steered: true });
          return;

        case "text.start":
          st.byBlock[ev.block] = addItem({ role: "assistant", kind: "text", block: ev.block, text: "", open: true });
          return;

        case "text.delta": {
          var it = st.byBlock[ev.block];
          if (!it) it = st.byBlock[ev.block] = addItem({ role: "assistant", kind: "text", block: ev.block, text: "", open: true });
          it.text += ev.text || "";
          emit("patch", it);
          return;
        }

        case "text.done": {
          var d = st.byBlock[ev.block];
          if (d) {
            if (ev.text) d.text = ev.text;
            d.open = false;
            emit("patch", d);
          }
          return;
        }

        case "thinking.start":
          st.byBlock[ev.block] = addItem({ role: "assistant", kind: "thinking", block: ev.block, text: "", open: true });
          return;

        case "thinking.delta": {
          var th = st.byBlock[ev.block];
          if (!th) th = st.byBlock[ev.block] = addItem({ role: "assistant", kind: "thinking", block: ev.block, text: "", open: true });
          th.text += ev.text || "";
          emit("patch", th);
          return;
        }

        case "thinking.done": {
          var td = st.byBlock[ev.block];
          if (td) { if (ev.text) td.text = ev.text; td.open = false; emit("patch", td); }
          return;
        }

        case "tool.pending":
          st.byBlock[ev.block] = addItem({
            role: "assistant", kind: "tool", block: ev.block, id: ev.id,
            name: ev.name, args: null, argText: "", open: true, result: null,
          });
          if (ev.id) st.byTool[ev.id] = st.byBlock[ev.block];
          return;

        case "tool.delta": {
          var tl = st.byBlock[ev.block];
          if (tl) { tl.argText += ev.text || ""; emit("patch", tl); }
          return;
        }

        case "tool.start": {
          var ts = st.byBlock[ev.block];
          if (!ts) {
            ts = st.byBlock[ev.block] = addItem({
              role: "assistant", kind: "tool", block: ev.block, id: ev.id,
              name: ev.name, args: null, argText: "", open: true, result: null,
            });
          }
          ts.name = ev.name || ts.name;
          ts.args = ev.args || {};
          ts.open = false;
          if (ev.id) st.byTool[ev.id] = ts;
          // Only the console's own loop reports which round it is on. A CLI
          // never does, so this stays 0 there and the budget panel — which
          // only renders when the backend declares budgets — stays absent.
          if (ev.round) { st.toolRound = ev.round; emit("meta", st); }
          noteFile(ts);
          emit("patch", ts);
          return;
        }

        case "tool.result": {
          var tr = st.byTool[ev.id];
          if (tr) {
            tr.result = { ok: ev.ok !== false, content: ev.content || "" };
            emit("patch", tr);
          }
          return;
        }

        case "todo":
          st.todos = ev.items || [];
          emit("meta", st);
          return;

        case "plan":
          st.plan = ev.plan || "";
          emit("meta", st);
          return;

        case "usage":
          /* A running total for the CURRENT turn, re-reported as it grows —
             not a delta. It was previously dropped on the floor, which is why
             the header's token counters never moved. */
          st.turnTokens = { in: Number(ev.input_tokens || 0),
                            out: Number(ev.output_tokens || 0) };
          emit("meta", st);
          return;

        case "turn.end":
          st.busy = false;
          st.usage.cost += Number(ev.cost_usd || 0);
          st.usage.turns += Number(ev.num_turns || 0);
          /* Take the larger of the incremental total and the one reported on
             the result: a backend may send either, or both, and summing them
             would double-count the turn. */
          var tin = Math.max(Number(ev.input_tokens || 0),
                             (st.turnTokens && st.turnTokens.in) || 0);
          var tout = Math.max(Number(ev.output_tokens || 0),
                              (st.turnTokens && st.turnTokens.out) || 0);
          st.usage.tokens_in += tin;
          st.usage.tokens_out += tout;
          st.turnTokens = null;
          addItem({ role: "system", kind: "turnend", is_error: !!ev.is_error,
                    cost: Number(ev.cost_usd || 0), ms: ev.duration_ms || 0,
                    tokens_in: tin, tokens_out: tout,
                    model: st.model || "", subtype: ev.subtype || "" });
          emit("meta", st);
          return;

        case "turn.interrupt":
          st.busy = false;
          addItem({ role: "system", kind: "interrupt", via: ev.via || "" });
          emit("meta", st);
          return;

        case "queue.add":
          st.queued.push(ev.item);
          emit("meta", st);
          return;

        case "queue.remove":
          st.queued = st.queued.filter(function (q) { return q.id !== ev.id; });
          emit("meta", st);
          return;

        case "queue.drain":
          st.queued = st.queued.filter(function (q) { return q.id !== (ev.item || {}).id; });
          emit("meta", st);
          return;

        case "approval.request": {
          /* `preview` is what makes the card reviewable rather than a wall of
             escaped JSON: a diff for a file write, the command for a shell
             call. Null when the server had nothing useful to say, which the
             renderer handles by falling back to the raw arguments. */
          var ap = { key: ev.key, tool: ev.tool || "tool", input: ev.input || {},
                     preview: ev.preview || null,
                     timeout: ev.timeout || 0, decided: "", by: "" };
          st.approvals[ev.key] = ap;
          ap.item = addItem({ role: "system", kind: "approval", sid: st.id, approval: ap });
          return;
        }

        case "approval.decided": {
          var apd = st.approvals[ev.key];
          if (apd) {
            apd.decided = ev.decision || "allow";
            apd.by = ev.by || "";
            if (apd.item) emit("patch", apd.item);
          }
          return;
        }

        case "notice":
          // A replayed user message confirms a steer was admitted; it is not
          // new content, so it does not become an item.
          if (ev.kind === "replay") return;
          // A rate-limit event that says "allowed" is the normal case and
          // fires every turn — only surface it when it is actually telling
          // you something (throttled, or burning overage).
          if (ev.kind === "rate_limit") {
            st.rateLimit = ev;
            if (ev.status === "allowed" && !ev.using_overage) { emit("meta", st); return; }
          }
          addItem({ role: "system", kind: "notice", level: ev.level || "info", text: ev.text || "" });
          return;

        case "error":
          addItem({ role: "system", kind: "error", text: ev.text || "unknown error" });
          emit("meta", st);
          return;

        case "session.exit":
          st.alive = false;
          st.busy = false;
          addItem({ role: "system", kind: "exit", code: ev.exit_code,
                    dropped: ev.dropped_queued || 0 });
          emit("meta", st);
          emit("end", st);
          return;

        case "stream.reset":
          // Handled by the subscriber, not here.
          return;

        default:
          // `raw` and anything unrecognised: surface it rather than swallow.
          addItem({ role: "system", kind: "raw", text: JSON.stringify(ev).slice(0, 400) });
          return;
      }
    }

    /* Files the agent touched, for the side panel. Derived from tool args
       rather than a separate event, because the tool call already says it. */
    function noteFile(tool) {
      var a = tool.args || {};
      var p = a.file_path || a.path || a.notebook_path || "";
      if (!p) return;
      var verb = /write|edit|create/i.test(tool.name || "") ? "write" : "read";
      var found = st.files.filter(function (f) { return f.path === p; })[0];
      if (found) {
        if (verb === "write") found.verb = "write";
      } else {
        st.files.push({ path: p, verb: verb });
      }
      emit("meta", st);
    }

    /* ---------------- load + subscribe ---------------- */
    function load() {
      return C.get("/api/agents/chats/" + encodeURIComponent(chatId)).then(function (data) {
        st.items = [];
        st.byBlock = {};
        st.byTool = {};
        st.todos = [];
        st.plan = "";
        st.files = [];
        st.queued = [];
        st.approvals = {};
        st.usage = { cost: 0, tokens_in: 0, tokens_out: 0, turns: 0 };
        st.toolRound = 0;
        st.head = 0;
        st.replaying = true;
        try { (data.events || []).forEach(apply); }
        finally { st.replaying = false; }
        st.snapshot = data.snapshot;
        if (data.snapshot) {
          st.alive = !!data.snapshot.alive;
          st.busy = !!data.snapshot.busy;
          st.queued = data.snapshot.queued || [];
        } else {
          st.alive = false;
        }
        st.head = data.head || st.head;
        emit("meta", st);
        return st;
      });
    }

    function subscribe() {
      if (st.closed || !st.alive) return;
      close();
      var url = "/api/agents/chats/" + encodeURIComponent(chatId) + "/stream?from=" + st.head;
      var es = new EventSource(url);
      st.es = es;
      claimStream(es);
      es.onmessage = function (m) {
        // A stream that lost its claim (a newer chat opened) must not keep
        // mutating this store's state.
        if (activeStream !== es) { releaseStream(es); return; }
        var ev;
        try { ev = JSON.parse(m.data); } catch (e) { return; }
        if (ev.type === "stream.reset") {
          // Gap we cannot bridge — re-read the whole transcript, then resume.
          close();
          load().then(subscribe);
          return;
        }
        apply(ev);
      };
      es.onerror = function () {
        // EventSource retries on its own, but only from where the browser
        // thinks it is. Ours must resume from our own head, so we take over.
        close();
        if (!st.closed && st.alive) {
          setTimeout(function () { if (!st.closed && st.alive) subscribe(); }, 1200);
        }
      };
    }

    function close() {
      if (st.es) { releaseStream(st.es); st.es = null; }
    }

    function destroy() {
      st.closed = true;
      close();
    }

    return {
      state: st, on: on, off: off,
      load: load, subscribe: subscribe, close: close, destroy: destroy,
    };
  }

  return { create: create };
})(window.Console);
