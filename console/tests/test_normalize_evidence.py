"""FR-10: `turn.end` carries the failure evidence the classifier needs
(`errors`, `error`, `api_error_status`, `stop_reason`). Inline fixtures only."""

from server.agent_normalize import Normalizer


def _turn_end(raw):
    out = Normalizer().feed(dict(raw, type="result"))
    return [e for e in out if e["type"] == "turn.end"][0]


# Copied from a real claude 2.1.x transcript: subtype success, is_error true.
AUTH_SAMPLE = {
    "subtype": "success", "is_error": True, "api_error_status": 401,
    "result": "Failed to authenticate: OAuth session expired and could not be refreshed",
    "stop_reason": "stop_sequence", "errors": ["OAuth session expired"],
    "total_cost_usd": 0, "duration_ms": 5, "num_turns": 1,
}


class TestEvidence:
    def test_result_with_errors_status_and_stop_reason(self):
        e = _turn_end(AUTH_SAMPLE)
        assert e["errors"] == ["OAuth session expired"]
        assert e["api_error_status"] == 401
        assert e["stop_reason"] == "stop_sequence"
        assert e["is_error"] is True and e["subtype"] == "success"
        assert e["result"].startswith("Failed to authenticate")

    def test_result_without_fields_yields_empty_defaults(self):
        e = _turn_end({"subtype": "success", "result": "ok"})
        assert e["errors"] == [] and e["error"] == ""
        assert e["api_error_status"] is None and e["stop_reason"] == ""

    def test_error_string_is_kept_and_bounded(self):
        e = _turn_end({"is_error": True, "error": "x" * 900})
        assert e["error"] == "x" * 500

    def test_non_int_status_is_none(self):
        assert _turn_end({"api_error_status": "401"})["api_error_status"] is None
        assert _turn_end({"api_error_status": True})["api_error_status"] is None

    def test_errors_bounded_ten_by_five_hundred(self):
        raw = {"errors": ["e" * 900] * 25 + [{"message": "m"}], "stop_reason": "s" * 200}
        e = _turn_end(raw)
        assert len(e["errors"]) == 10
        assert all(len(x) == 500 for x in e["errors"])
        assert len(e["stop_reason"]) == 64

    def test_errors_not_a_list_is_empty(self):
        assert _turn_end({"errors": "boom"})["errors"] == []

    def test_existing_turn_end_keys_unchanged(self):
        e = _turn_end({"subtype": "success", "is_error": False, "total_cost_usd": 1.5,
                       "duration_ms": 7, "num_turns": 3,
                       "usage": {"input_tokens": 4, "output_tokens": 5}, "result": "r" * 5000})
        assert e["subtype"] == "success" and e["is_error"] is False
        assert e["cost_usd"] == 1.5 and e["duration_ms"] == 7 and e["num_turns"] == 3
        assert e["input_tokens"] == 4 and e["output_tokens"] == 5
        assert e["result"] == "r" * 4000

    def test_rate_limit_notice_shape_unchanged(self):
        out = Normalizer().feed({"type": "rate_limit_event", "rate_limit_info": {
            "status": "rejected", "rateLimitType": "five_hour", "resetsAt": 1760000000,
            "isUsingOverage": False}})
        assert out == [{"type": "notice", "level": "warn", "kind": "rate_limit",
                        "status": "rejected", "window": "five_hour", "resets_at": 1760000000,
                        "using_overage": False,
                        "text": "rate limit rejected (five_hour window)"}]
