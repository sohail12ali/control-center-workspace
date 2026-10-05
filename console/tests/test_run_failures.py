"""FR-11: `run_failures.classify`, the pure Claude failure classifier."""

import pytest

from server import run_failures
from server.run_failures import CLASSES, NON_RETRYABLE, classify

AUTH = "Failed to authenticate: OAuth session expired and could not be refreshed"


def _te(result="", *, subtype="success", is_error=True, errors=(), error="",
        status=None, stop=""):
    return {"type": "turn.end", "subtype": subtype, "is_error": is_error, "result": result,
            "errors": list(errors), "error": error, "api_error_status": status,
            "stop_reason": stop}


def _rl(status="rejected"):
    return {"type": "notice", "kind": "rate_limit", "status": status, "resets_at": 0}


# (id, turn_end, rate_limit, exit_code, stderr, expected class)
ROWS = [
    ("auth-real-sample", _te(AUTH), None, 0, "", "auth_required"),
    ("auth-status-401", _te("nope", status=401), None, 1, "", "auth_required"),
    ("auth-login-prompt", _te("Please run /login"), None, 1, "", "auth_required"),
    ("auth-beats-quota", _te(AUTH + " usage limit reached"), None, 1, "", "auth_required"),
    ("auth-beats-transient", _te(AUTH, status=529), None, 1, "", "auth_required"),
    ("model", _te("model not found: claude-x"), None, 1, "", "model_not_found"),
    ("max-turns-subtype", _te("", subtype="error_max_turns"), None, 1, "", "max_turns"),
    ("max-turns-stop", _te("x", stop="max_turns"), None, 1, "", "max_turns"),
    ("unknown-session", _te("No conversation found with session id abc"), None, 1, "",
     "unknown_session"),
    ("poisoned", _te("", errors=["diagnostics.previous_message_id starts with `msg_`"]),
     None, 1, "", "poisoned_session"),
    ("image", _te("Could not process image"), None, 1, "", "image_error"),
    ("refusal-structured", _te("I can't", is_error=False, stop="refusal"), None, 0, "",
     "refusal"),
    ("quota-text", _te("You've hit your limit · resets 4pm (America/Chicago)"), None, 1, "",
     "quota"),
    ("quota-notice", _te("stopped"), _rl("rejected"), 1, "", "quota"),
    ("quota-beats-transient", _te("usage limit reached, rate limit", status=429), None, 1, "",
     "quota"),
    ("transient-429", _te("API Error", status=429), None, 1, "", "transient_upstream"),
    ("transient-overloaded", _te("overloaded_error"), None, 1, "", "transient_upstream"),
    ("transient-stderr", _te("failed"), None, 1, "503 service unavailable",
     "transient_upstream"),
    ("process-lost-no-turn", None, None, 1, "", "process_lost"),
    ("process-lost-missing-exit", None, None, None, "", "process_lost"),
    ("process-exit-nonzero", _te("", subtype="process_exit", is_error=False), None, 137, "",
     "process_lost"),
    ("unknown-text", _te("something strange happened"), None, 1, "", "unclassified"),
    ("nonzero-exit-clean-turn", _te("done", is_error=False), None, 2, "", "unclassified"),
    ("unauthorized-in-success", _te("The API returns unauthorized for bad keys.",
                                    is_error=False), None, 0, "", ""),
    ("rate-limit-words-success", _te("Mind the rate limit, try again later.",
                                     is_error=False), None, 0, "", ""),
    ("rate-limit-notice-allowed-success", _te("ok", is_error=False), _rl("allowed"), 0, "", ""),
    ("process-exit-zero", _te("", subtype="process_exit", is_error=False), None, 0, "", ""),
    ("clean-success", _te("done", is_error=False), None, 0, "", ""),
]


class TestClassifyTable:
    @pytest.mark.parametrize("name,te,rl,code,err,want", ROWS, ids=[r[0] for r in ROWS])
    def test_twenty_plus_rows(self, name, te, rl, code, err, want):
        assert len(ROWS) >= 20
        out = classify(te, rl, code, err)
        assert out["class"] == want
        assert set(out) == {"class", "retryable_class", "detail", "retry_not_before"}

    def test_success_subtype_with_is_error_is_auth_required(self):
        out = classify(_te(AUTH, subtype="success", is_error=True), None, 0, "")
        assert out["class"] == "auth_required"
        assert AUTH[:40] in out["detail"]

    def test_rate_limit_words_in_successful_turn_not_failed(self):
        te = _te("Note: rate limit and usage limit reached are API terms.", is_error=False)
        assert classify(te, _rl("rejected"), 0, "")["class"] == ""

    def test_unknown_text_on_failed_turn_is_unclassified_never_transient(self):
        out = classify(_te("kaboom"), None, 1, "")
        assert out["class"] == "unclassified" and out["retryable_class"] is False

    def test_process_exit_zero_is_not_a_failure(self):
        out = classify(_te("", subtype="process_exit", is_error=False), None, 0, "")
        assert out["class"] == "" and out["retryable_class"] is False

    def test_retryable_flag_matches_non_retryable_set(self):
        assert classify(_te("x", status=429), None, 1, "")["retryable_class"] is True
        assert classify(_te(AUTH), None, 1, "")["retryable_class"] is False
        assert classify(None, None, 1, "")["retryable_class"] is True  # process_lost

    def test_class_sets(self):
        for c in ("auth_required", "model_not_found", "max_turns", "unknown_session",
                  "poisoned_session", "image_error", "refusal", "quota",
                  "transient_upstream", "process_lost", "output_cap", "stalled",
                  "unclassified"):
            assert c in CLASSES
        assert NON_RETRYABLE <= set(CLASSES)
        assert {"quota", "transient_upstream", "max_turns", "process_lost"}.isdisjoint(
            NON_RETRYABLE)
        assert {"output_cap", "stalled", "unclassified", "auth_required"} <= NON_RETRYABLE

    def test_detail_is_bounded_and_retry_not_before_empty_by_default(self):
        out = classify(_te("z" * 5000), None, 1, "")
        assert len(out["detail"]) <= 200 and out["retry_not_before"] == ""

    def test_assistant_prose_never_reaches_auth(self):
        # Terminal fields only: stderr text does not make auth either.
        out = classify(_te("boom"), None, 1, "unauthorized: please log in")
        assert out["class"] == "unclassified"


# -- FR-15: the retry table ---------------------------------------------------

import os  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

from server import boards, run_config  # noqa: E402
from server.run_failures import decide  # noqa: E402

T0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
CFG = {
    "max_total_retries": 3, "quota_max_wait_secs": 21600,
    "classes": {
        "transient_upstream": {"max": 2, "delays": [30, 120]},
        "quota": {"max": 2, "delays": [60]},
        "max_turns": {"max": 2, "delays": [1]},
        "process_lost": {"max": 1, "delays": [10]},
    },
}


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _fail(cls, reset=""):
    return {"class": cls, "retryable_class": cls in run_failures.RETRYABLE,
            "detail": "d-" + cls, "retry_not_before": reset}


def _run():
    return {"id": "r1", "created": _iso(T0), "attempt": 1, "attempts": [], "state": "running"}


def _chain(classes, cfg=CFG, reset_after=None):
    """Fail a Run once per class in order, applying each patch the way
    `runs.update` plus the retry executor (3b-3) would. Returns the patches."""
    r, out = _run(), []
    for i, cls in enumerate(classes):
        now = T0 + timedelta(minutes=i)
        reset = _iso(now + timedelta(seconds=reset_after)) if reset_after else ""
        patch = decide(r, _fail(cls, reset), now, cfg)
        out.append(patch)
        r.update(patch)
        if patch["state"] == "scheduled_retry":
            r.update(state="running", attempt=r["attempt"] + 1)
    return out


class TestRetryTable:
    @pytest.mark.parametrize("cls, n", [("transient_upstream", 2), ("max_turns", 2),
                                        ("process_lost", 1), ("quota", 2)])
    def test_n_plus_one_failures_give_n_retries_then_failed(self, cls, n):
        patches = _chain([cls] * (n + 1), reset_after=3600 if cls == "quota" else None)
        assert [p["state"] for p in patches] == ["scheduled_retry"] * n + ["failed"]
        last = patches[-1]
        assert last["end_reason"] == "retry_exhausted" and last["failure_class"] == cls
        assert last["ended"] and "retry_due" not in last
        assert len(last["attempts"]) == n + 1
        assert [a["n"] for a in last["attempts"]] == list(range(1, n + 2))
        assert all(a["failure_class"] == cls for a in last["attempts"])

    @pytest.mark.parametrize("cls", sorted(NON_RETRYABLE))
    def test_non_retryable_classes_fail_with_zero_retries(self, cls):
        patch = decide(_run(), _fail(cls), T0, CFG)
        assert patch["state"] == "failed" and patch["end_reason"] == cls
        assert patch["failure_class"] == cls and patch["ended"] == _iso(T0)
        assert "retry_due" not in patch
        assert [a["failure_class"] for a in patch["attempts"]] == [cls]

    def test_empty_class_is_unclassified_and_never_retried(self):
        patch = decide(_run(), _fail(""), T0, CFG)
        assert patch["state"] == "failed" and patch["failure_class"] == "unclassified"

    def test_delays_per_attempt_and_scheduled_shape(self):
        patches = _chain(["transient_upstream", "transient_upstream"])
        first, second = patches
        assert first["retry_due"] == _iso(T0 + timedelta(seconds=30))
        assert second["retry_due"] == _iso(T0 + timedelta(minutes=1, seconds=120))
        assert first["attempt"] == 1 and second["attempt"] == 2
        assert first["failure_class"] == "transient_upstream" and first["failure_detail"]
        assert first["retry_not_before"] == "" and "ended" not in first

    def test_quota_three_hours_ahead_due_not_before_reset_plus_sixty(self):
        reset = T0 + timedelta(hours=3)
        patch = decide(_run(), _fail("quota", _iso(reset)), T0, CFG)
        assert patch["state"] == "scheduled_retry"
        assert patch["retry_due"] == _iso(reset + timedelta(seconds=60))
        assert patch["retry_not_before"] == _iso(reset)

    @pytest.mark.parametrize("reset", ["", "3days"])
    def test_quota_unknown_or_three_days_fails_without_retry_and_keeps_reset_time(self, reset):
        stamp = _iso(T0 + timedelta(days=3)) if reset else ""
        patch = decide(_run(), _fail("quota", stamp), T0, CFG)
        assert patch["state"] == "failed" and "retry_due" not in patch
        assert patch["end_reason"] == "quota"
        assert patch["retry_not_before"] == stamp

    def test_never_before_retry_not_before(self):
        reset = T0 + timedelta(hours=1)
        patch = decide(_run(), _fail("transient_upstream", _iso(reset)), T0, CFG)
        assert patch["retry_due"] == _iso(reset)  # later than now + 30 s (BR-4)

    def test_total_cap_three_across_classes(self):
        patches = _chain(["transient_upstream", "transient_upstream", "process_lost",
                          "transient_upstream"])
        assert [p["state"] for p in patches] == ["scheduled_retry"] * 3 + ["failed"]
        assert patches[-1]["end_reason"] == "retry_exhausted"

    def test_max_total_retries_zero_disables_retry(self):
        cfg = dict(CFG, max_total_retries=0)
        patch = decide(_run(), _fail("transient_upstream"), T0, cfg)
        assert patch["state"] == "failed" and patch["end_reason"] == "retry_exhausted"

    def test_class_max_zero_disables_that_class_only(self):
        cfg = dict(CFG, classes=dict(CFG["classes"], max_turns={"max": 0, "delays": [1]}))
        assert decide(_run(), _fail("max_turns"), T0, cfg)["state"] == "failed"
        assert decide(_run(), _fail("process_lost"), T0, cfg)["state"] == "scheduled_retry"

    def test_attempts_keep_the_last_ten(self):
        r = dict(_run(), attempt=11, attempts=[
            {"n": i, "started": "", "ended": "", "failure_class": "x"} for i in range(1, 11)])
        cfg = dict(CFG, max_total_retries=50)
        patch = decide(r, _fail("process_lost"), T0, cfg)
        assert len(patch["attempts"]) == 10 and patch["attempts"][-1]["n"] == 11

    def test_delay_override_changes_due_and_bad_value_warns_once(self, repo, capsys):
        run_config.reset_warnings()
        path = os.path.join(repo, "console", "config", "console.toml")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write('\n[runs.retry]\ntransient_upstream_delays = [5, 7]\n'
                     'process_lost_delays = "soon"\n')
        boards._console_cache.clear()
        cfg = run_config.retry_cfg(repo)
        patch = decide(_run(), _fail("transient_upstream"), T0, cfg)
        assert patch["retry_due"] == _iso(T0 + timedelta(seconds=5))
        lost = decide(_run(), _fail("process_lost"), T0, cfg)
        assert lost["retry_due"] == _iso(T0 + timedelta(seconds=10))  # fell back
        run_config.retry_cfg(repo)
        warned = [ln for ln in capsys.readouterr().err.splitlines() if "process_lost_delays" in ln]
        assert len(warned) == 1
        run_config.reset_warnings()
