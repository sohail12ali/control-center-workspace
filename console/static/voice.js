/* Voice: dictation into the composer, and read-aloud of agent replies.

   Both are browser APIs with real support gaps, so the rule here is: a
   capability that is MISSING stays visible and says why, while a capability
   the user switched OFF is genuinely gone. A control that silently vanishes
   teaches nobody that it exists — and "why is there no mic button" is a worse
   bug report than "the mic button says my browser can't do it".

   Dictation is Web Speech (`webkitSpeechRecognition`), which in practice means
   Chrome/Edge and sends audio to a vendor service. That is a real privacy
   consequence, so it is off until asked for, per-use, and the UI says where the
   audio goes rather than burying it.

   Read-aloud is `speechSynthesis`, which is local and broadly supported. It
   speaks the FINISHED text of a reply, not the token stream: reading deltas
   aloud produces stuttering nonsense, because each delta restarts the
   utterance mid-word. */
window.ConsoleVoice = (function (C) {
  "use strict";

  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var SS = window.speechSynthesis;

  var state = {
    listening: false,
    recog: null,
    onText: null,
    speaking: false,
    voices: [],
  };

  function support() {
    return {
      dictation: !!SR,
      readAloud: !!SS,
      dictationWhy: SR ? "" : "This browser has no Web Speech recognition (Chrome or Edge do).",
      readAloudWhy: SS ? "" : "This browser has no speech synthesis.",
    };
  }

  /* ---------------- preferences ---------------- */
  var DEFAULTS = {
    autoRead: false,      // speak each finished reply
    announce: true,       // speak turn-end / permission-needed even when
                          // autoRead is off — a parked run should not be silent
    rate: 1.0,
    pitch: 1.0,
    voice: "",            // voiceURI, "" = browser default
    interim: true,        // show partial dictation as it arrives
  };

  function prefs() {
    return Object.assign({}, DEFAULTS, C.prefs.get("voice", {}));
  }

  function setPrefs(patch) {
    var next = Object.assign({}, prefs(), patch || {});
    C.prefs.set("voice", next);
    return next;
  }

  /* ---------------- voices ---------------- */
  function loadVoices() {
    if (!SS) return Promise.resolve([]);
    var have = SS.getVoices();
    if (have && have.length) {
      state.voices = have;
      return Promise.resolve(have);
    }
    // Chrome populates the list asynchronously, once.
    return new Promise(function (resolve) {
      var done = false;
      var finish = function () {
        if (done) return;
        done = true;
        state.voices = SS.getVoices() || [];
        resolve(state.voices);
      };
      SS.addEventListener("voiceschanged", finish, { once: true });
      setTimeout(finish, 800);
    });
  }

  function voices() { return state.voices; }

  /* ---------------- dictation ---------------- */
  function startDictation(onText, onState) {
    if (!SR) {
      C.toast(support().dictationWhy, "err");
      return false;
    }
    if (state.listening) { stopDictation(); return false; }

    var r = new SR();
    r.continuous = true;
    r.interimResults = !!prefs().interim;
    r.lang = navigator.language || "en-US";

    var committed = "";
    r.onresult = function (e) {
      var interim = "";
      for (var i = e.resultIndex; i < e.results.length; i++) {
        var res = e.results[i];
        if (res.isFinal) committed += res[0].transcript;
        else interim += res[0].transcript;
      }
      if (onText) onText(committed, interim);
    };
    r.onerror = function (e) {
      // `no-speech` and `aborted` are ordinary, not faults worth shouting about.
      if (e.error && e.error !== "no-speech" && e.error !== "aborted") {
        C.toast("Dictation: " + e.error, "err");
      }
      stopDictation();
    };
    r.onend = function () {
      state.listening = false;
      state.recog = null;
      if (onState) onState(false);
    };

    try {
      r.start();
    } catch (err) {
      C.toast("Dictation could not start: " + err.message, "err");
      return false;
    }
    state.recog = r;
    state.listening = true;
    if (onState) onState(true);
    return true;
  }

  function stopDictation() {
    if (state.recog) {
      try { state.recog.stop(); } catch (e) { /* already stopping */ }
    }
    state.listening = false;
    if (state.recog) state.recog = null;
  }

  function listening() { return state.listening; }

  /* ---------------- read aloud ---------------- */
  function speak(text, onDone) {
    if (!SS) { C.toast(support().readAloudWhy, "err"); return false; }
    text = String(text || "").trim();
    if (!text) return false;

    // Strip the things that read badly: fenced code, inline backticks, link
    // syntax, and heading marks. Reading a code block aloud is noise.
    text = text
      .replace(/```[\s\S]*?```/g, " (code block) ")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/^#{1,6}\s*/gm, "")
      .replace(/\*\*|__|~~/g, "")
      .slice(0, 4000);

    var p = prefs();
    var u = new SpeechSynthesisUtterance(text);
    u.rate = Number(p.rate) || 1;
    u.pitch = Number(p.pitch) || 1;
    if (p.voice) {
      var match = (state.voices || []).filter(function (v) { return v.voiceURI === p.voice; })[0];
      if (match) u.voice = match;
    }
    u.onend = function () { state.speaking = false; if (onDone) onDone(); };
    u.onerror = function () { state.speaking = false; if (onDone) onDone(); };
    SS.cancel();          // one utterance at a time; overlapping is unintelligible
    SS.speak(u);
    state.speaking = true;
    return true;
  }

  function stopSpeaking() {
    if (SS) SS.cancel();
    state.speaking = false;
  }

  function speaking() { return state.speaking; }

  /* ---------------- controls ----------------
     Built here so the mic and the speaker look and behave the same wherever
     they appear, instead of each tab inventing its own. */
  function micButton(onText) {
    var btn = C.el("button", {
      class: "btn sm iconly", "aria-label": "Dictate", title: "Dictate (Web Speech)",
    }, [C.icon("mic")]);
    if (!SR) {
      btn.disabled = true;
      btn.title = support().dictationWhy;
      btn.classList.add("unavailable");
      return btn;
    }
    btn.addEventListener("click", function () {
      if (listening()) { stopDictation(); return; }
      startDictation(onText, function (on) {
        btn.classList.toggle("primary", on);
        btn.classList.toggle("running", on);
        btn.title = on ? "Stop dictation" : "Dictate (Web Speech)";
      });
    });
    return btn;
  }

  function speakButton(getText) {
    var btn = C.el("button", {
      class: "btn sm iconly", "aria-label": "Read aloud", title: "Read this reply aloud",
    }, [C.icon("speaker")]);
    if (!SS) {
      btn.disabled = true;
      btn.title = support().readAloudWhy;
      btn.classList.add("unavailable");
      return btn;
    }
    btn.addEventListener("click", function () {
      if (speaking()) { stopSpeaking(); btn.classList.remove("primary"); return; }
      btn.classList.add("primary");
      speak(getText(), function () { btn.classList.remove("primary"); });
    });
    return btn;
  }

  if (SS) loadVoices();

  return {
    support: support, prefs: prefs, setPrefs: setPrefs,
    loadVoices: loadVoices, voices: voices,
    startDictation: startDictation, stopDictation: stopDictation, listening: listening,
    speak: speak, stopSpeaking: stopSpeaking, speaking: speaking,
    micButton: micButton, speakButton: speakButton,
  };
})(window.Console);
