/* Minimal markdown → DOM for agent output.

   Deliberately small and DOM-building rather than innerHTML: agent output is
   untrusted text (it echoes file contents, error messages, whatever it read),
   so it never goes near innerHTML. Every node here is created and given
   textContent, which makes injection structurally impossible rather than
   filtered-against.

   Supports what agents actually emit: fenced code, inline code, headings,
   bullet/numbered lists, blockquotes, bold/italic, links, and hard rules.
   Anything else renders as its literal text, which is the right failure —
   showing the source beats silently dropping content. */
window.ConsoleMarkdown = (function () {
  "use strict";

  var INLINE = [
    // order matters: code first so its content isn't re-parsed for emphasis
    { re: /`([^`]+)`/, tag: "code", cls: "md-ic" },
    { re: /\*\*([^*]+)\*\*/, tag: "strong" },
    { re: /(?:^|[\s(])\*([^*\n]+)\*(?=[\s).,!?]|$)/, tag: "em", trimLead: true },
    { re: /\b_([^_\n]+)_\b/, tag: "em" },
    { re: /~~([^~]+)~~/, tag: "del" },
  ];

  var LINK = /\[([^\]]+)\]\(([^)\s]+)\)/;
  var BARE = /(https?:\/\/[^\s<>()]+)/;

  function inline(text, parent) {
    if (!text) return;
    // Links first — their label may itself contain emphasis.
    var m = LINK.exec(text);
    if (m) {
      inline(text.slice(0, m.index), parent);
      var a = document.createElement("a");
      a.href = m[2];
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      inline(m[1], a);
      parent.appendChild(a);
      inline(text.slice(m.index + m[0].length), parent);
      return;
    }
    for (var i = 0; i < INLINE.length; i++) {
      var rule = INLINE[i];
      var hit = rule.re.exec(text);
      if (!hit) continue;
      var start = hit.index;
      var raw = hit[0];
      // A rule that intentionally matched a leading space keeps it outside.
      if (rule.trimLead && /^[\s(]/.test(raw)) {
        start += 1;
        raw = raw.slice(1);
      }
      inline(text.slice(0, start), parent);
      var node = document.createElement(rule.tag);
      if (rule.cls) node.className = rule.cls;
      node.textContent = hit[1];
      parent.appendChild(node);
      inline(text.slice(start + raw.length), parent);
      return;
    }
    var b = BARE.exec(text);
    if (b) {
      inline(text.slice(0, b.index), parent);
      var link = document.createElement("a");
      link.href = b[1];
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = b[1];
      parent.appendChild(link);
      inline(text.slice(b.index + b[0].length), parent);
      return;
    }
    parent.appendChild(document.createTextNode(text));
  }

  function codeBlock(lang, lines) {
    var wrap = document.createElement("div");
    wrap.className = "md-code";
    if (lang) {
      var tag = document.createElement("div");
      tag.className = "md-lang";
      tag.textContent = lang;
      wrap.appendChild(tag);
    }
    var pre = document.createElement("pre");
    var code = document.createElement("code");
    code.textContent = lines.join("\n");
    pre.appendChild(code);
    wrap.appendChild(pre);
    return wrap;
  }

  /** Render `src` into a fresh element. */
  function render(src) {
    var root = document.createElement("div");
    root.className = "md";
    var lines = String(src == null ? "" : src).split("\n");
    var i = 0;
    var list = null;

    function closeList() { list = null; }

    while (i < lines.length) {
      var line = lines[i];

      // fenced code
      var fence = /^\s*```+\s*(\S*)\s*$/.exec(line);
      if (fence) {
        closeList();
        var lang = fence[1] || "";
        var body = [];
        i++;
        while (i < lines.length && !/^\s*```+\s*$/.test(lines[i])) {
          body.push(lines[i]);
          i++;
        }
        i++; // consume closing fence (or run off the end, which is fine)
        root.appendChild(codeBlock(lang, body));
        continue;
      }

      if (/^\s*$/.test(line)) { closeList(); i++; continue; }

      // heading
      var h = /^(#{1,6})\s+(.*)$/.exec(line);
      if (h) {
        closeList();
        var el = document.createElement("h" + Math.min(6, h[1].length + 2));
        el.className = "md-h";
        inline(h[2], el);
        root.appendChild(el);
        i++;
        continue;
      }

      // rule
      if (/^\s*([-*_])\s*\1\s*\1[\s\S]*$/.test(line) && !/\w/.test(line)) {
        closeList();
        root.appendChild(document.createElement("hr"));
        i++;
        continue;
      }

      // blockquote
      var q = /^\s*>\s?(.*)$/.exec(line);
      if (q) {
        closeList();
        var bq = document.createElement("blockquote");
        inline(q[1], bq);
        root.appendChild(bq);
        i++;
        continue;
      }

      // list item
      var li = /^\s*(?:[-*+]|(\d+)[.)])\s+(.*)$/.exec(line);
      if (li) {
        var ordered = !!li[1];
        if (!list || list.ordered !== ordered) {
          var el2 = document.createElement(ordered ? "ol" : "ul");
          el2.className = "md-list";
          root.appendChild(el2);
          list = { node: el2, ordered: ordered };
        }
        var item = document.createElement("li");
        inline(li[2], item);
        list.node.appendChild(item);
        i++;
        continue;
      }

      // paragraph — consume until a blank line or a block starter
      closeList();
      var para = [line];
      i++;
      while (i < lines.length && !/^\s*$/.test(lines[i]) &&
             !/^\s*```/.test(lines[i]) && !/^#{1,6}\s/.test(lines[i]) &&
             !/^\s*>/.test(lines[i]) &&
             !/^\s*(?:[-*+]|\d+[.)])\s/.test(lines[i])) {
        para.push(lines[i]);
        i++;
      }
      var p = document.createElement("p");
      inline(para.join(" "), p);
      root.appendChild(p);
    }
    return root;
  }

  return { render: render };
})();
