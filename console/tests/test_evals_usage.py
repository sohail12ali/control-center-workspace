"""Usage is unknown when the raw result does not carry a number. Never inferred zero."""

from evals.runner import render_usage, replay_usage, totals, usage_of


def test_result_without_usage_key_is_unknown_not_zero(repo):
    usage = usage_of({"type": "result", "result": "ok"}, repo)
    assert usage["input_tokens"] is None
    assert usage["output_tokens"] is None
    assert usage["cost_usd"] is None
    assert render_usage(usage) == "UNKNOWN"


def test_reported_zero_usage_and_cost_stay_zero_with_cost_source_backend(repo):
    usage = usage_of({
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "total_cost_usd": 0,
    }, repo)
    assert usage["input_tokens"] == 0
    assert usage["output_tokens"] == 0
    assert usage["cost_usd"] == 0
    assert usage["cost_source"] == "backend"


def test_usage_block_with_one_key_missing_makes_only_that_key_unknown(repo):
    usage = usage_of({"usage": {"input_tokens": 4}, "total_cost_usd": 0.1}, repo)
    assert usage["input_tokens"] == 4
    assert usage["output_tokens"] is None
    assert usage["cost_usd"] == 0.1
    assert render_usage(usage) == "UNKNOWN"


def test_missing_cost_with_known_tokens_falls_back_to_telemetry_price_table_else_unknown(repo, monkeypatch):
    from server import telemetry

    def fake(root, model, inp, out):
        fake.called = (model, inp, out)
        if model == "priced":
            return 0.02, "table"
        return None, "unknown"

    monkeypatch.setattr(telemetry, "price", fake)
    priced = usage_of({"usage": {"input_tokens": 10, "output_tokens": 5}, "model": "priced"}, repo)
    assert fake.called == ("priced", 10, 5)
    assert priced["cost_usd"] == 0.02 and priced["cost_source"] == "table"
    unknown = usage_of({"usage": {"input_tokens": 10, "output_tokens": 5}, "model": "nope"}, repo)
    assert unknown["cost_usd"] is None and unknown["cost_source"] == "unknown"


def test_totals_sum_known_only_and_flag_incomplete_with_unknown_count():
    rows = [
        {"usage": {"input_tokens": 2, "output_tokens": 3, "cost_usd": 0.1, "cost_source": "backend"}},
        {"usage": {"input_tokens": None, "output_tokens": 4, "cost_usd": None, "cost_source": "unknown"}},
    ]
    rolled = totals(rows)
    assert rolled["input_tokens"] == 2
    assert rolled["output_tokens"] == 7
    assert rolled["complete"] is False
    assert rolled["unknown_scenarios"] == 1
    assert "partial"  # the table footer word lives with an incomplete run


def test_replay_usage_renders_n_a():
    usage = replay_usage()
    assert render_usage(usage) == "n/a (replay)"
    rolled = totals([{"usage": usage}, {"usage": usage}])
    assert rolled["complete"] is True
    assert rolled["unknown_scenarios"] == 0
