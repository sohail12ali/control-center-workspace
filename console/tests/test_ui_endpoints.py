"""The endpoints the tabs read, driven through the real router.

These exist because of a specific failure this console already had: verbs,
jobs, schedules, worktrees, audit and telemetry were all built, tested and
reachable only from a terminal. `/api/jobs` was even registered and then never
called by anything. A route with no caller is indistinguishable from a broken
one until someone opens the tab.

So each test here asks the question the tab asks, through the router the
server actually builds, and checks the answer is shaped the way the panel
expects. What a panel does with that answer is JS and is not tested here —
what is tested is that the contract between them exists and holds.

The other property under test throughout: **every one of these degrades.** A
checkout with no git, no schedules, no telemetry and no Telegram credentials
is an ordinary checkout, and a panel that 500s on it would be a worse answer
than one that says "none".
"""

import json
import os

import pytest

from server import boards, httpd
from server.paths import find_repo_root
from server.plugins import registry as plugin_registry


class App:
    """A built console: the shipped plugin set, wired against a scratch root."""

    def __init__(self, repo_root, router):
        self.repo_root = repo_root
        self.router = router


@pytest.fixture
def app(repo):
    """The real router, built from the SHIPPED plugins.toml, against a
    throwaway workspace.

    The registry is copied in from the checkout rather than invented here, so
    these tests exercise the plugin set this template actually ships. A row
    added to plugins.toml without a module, or a module that stops exposing
    its routes, fails here.
    """
    real = find_repo_root()
    src = os.path.join(real, "console", "config", "plugins.toml")
    dst = os.path.join(repo, "console", "config", "plugins.toml")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, encoding="utf-8") as fh:
        text = fh.read()
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(text)

    boards._console_cache.clear()
    config = boards.load_console_config(repo)
    _ctx, router = plugin_registry.build(repo, config)
    return App(repo, router)


def routed(app, method, path):
    """Whether a route exists, without invoking it."""
    handler, _args = app.router.resolve(method, path)
    return handler is not None


def call(app, method, path, query=None, body=None):
    """Dispatch one request the way httpd does, returning the handler's data."""
    handler, args = app.router.resolve(method, path)
    assert handler is not None, "no route for %s %s" % (method, path)
    req = httpd.Request(method, path, query or {}, body, app.repo_root,
                        client_addr="100.64.0.9", user_agent="pytest")
    return handler(req, *args)


class TestRoutesExist:
    """A panel whose endpoint is missing renders nothing and says nothing.

    This is the test that would have caught `/api/jobs` having no caller had
    it been written the other way round.
    """

    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/jobs"),
        ("GET", "/api/schedules"),
        ("GET", "/api/worktrees"),
        ("GET", "/api/notify"),
        ("GET", "/api/work/audit"),
        ("GET", "/api/analytics"),
        # The composer's inline pickers and its model list.
        ("GET", "/api/agents/files"),
        ("GET", "/api/agents/models"),
    ])
    def test_the_tab_endpoints_are_routed(self, app, method, path):
        assert routed(app, method, path), "%s %s is not routed" % (method, path)

    def test_job_cancel_is_a_post_not_a_get(self, app):
        # A GET that cancels work is a GET a browser will happily repeat, and
        # a prefetcher will call without being asked.
        assert routed(app, "POST", "/api/jobs/abc123/cancel")
        assert not routed(app, "GET", "/api/jobs/abc123/cancel")

    def test_refreshing_models_is_a_post_not_a_get(self, app):
        # Same rule, sharper: this one leaves the machine and spends the
        # workspace's credentials. Reading the CACHE is the GET.
        assert routed(app, "POST", "/api/agents/models/refresh")
        assert not routed(app, "GET", "/api/agents/models/refresh")


class TestFilePicker:
    """`#` offers workspace paths. What it must never offer is the file that
    holds every key this console authenticates with."""

    def test_it_finds_a_file_by_substring(self, app, repo):
        _write(repo, "src/widget.py", "x = 1\n")
        paths = [f["path"] for f in call(app, "GET", "/api/agents/files",
                                         {"q": "widget"})["files"]]
        assert "src/widget.py" in paths

    def test_it_never_offers_dotenv(self, app, repo):
        _write(repo, ".env", "OPENROUTER_API_KEY=sk-secret\n")
        for query in ("", "env", ".env"):
            paths = [f["path"] for f in call(app, "GET", "/api/agents/files",
                                             {"q": query, "limit": "50"})["files"]]
            assert not any(p.endswith(".env") for p in paths), query

    def test_an_absurd_limit_is_clamped_not_obeyed(self, app):
        out = call(app, "GET", "/api/agents/files", {"q": "", "limit": "99999"})
        assert len(out["files"]) <= 50

    def test_a_junk_limit_falls_back(self, app):
        out = call(app, "GET", "/api/agents/files", {"q": "", "limit": "banana"})
        assert isinstance(out["files"], list)

    def test_an_empty_workspace_returns_a_list_not_an_error(self, app):
        assert call(app, "GET", "/api/agents/files", {"q": "zzz"})["files"] == []


class TestModelsEndpoint:
    def test_with_no_backend_it_summarises_providers(self, app):
        out = call(app, "GET", "/api/agents/models")
        assert isinstance(out["providers"], list)

    def test_a_cli_backend_is_told_it_has_no_catalogue(self, app):
        # "alpha" is the scratch workspace's own CLI row (see conftest), not a
        # real product — these tests must not depend on what is installed on
        # the machine running them.
        out = call(app, "GET", "/api/agents/models", {"backend": "alpha"})
        assert out["count"] == 0 and "is a CLI" in out["error"]

    def test_an_unknown_backend_says_unknown(self, app):
        out = call(app, "GET", "/api/agents/models", {"backend": "nope"})
        assert "unknown backend" in out["error"]

    def test_reading_the_cache_never_reaches_the_network(self, app, monkeypatch):
        # The property that makes this safe as a GET. If the handler ever
        # starts fetching, this fails rather than quietly costing money on
        # every back-navigation.
        import urllib.request

        def forbidden(*a, **k):
            raise AssertionError("a GET reached the network")

        monkeypatch.setattr(urllib.request, "urlopen", forbidden)
        call(app, "GET", "/api/agents/models", {"backend": "alpha"})
        call(app, "GET", "/api/agents/models")

    def test_a_refresh_with_no_backend_is_refused(self, app):
        with pytest.raises(ValueError):
            call(app, "POST", "/api/agents/models/refresh", body={})

    def test_a_failed_refresh_is_still_audited(self, app, repo):
        from server import audit
        call(app, "POST", "/api/agents/models/refresh", body={"backend": "alpha"})
        row = audit.read(repo)[0]
        assert row["action"] == "models.refresh"
        assert row["target"] == "alpha" and "error" in row["outcome"]


class TestSchedules:
    def test_an_empty_workspace_reports_none_rather_than_failing(self, app):
        out = call(app, "GET", "/api/schedules")
        assert out["schedules"] == [] and out["error"] == ""

    def test_schedules_are_listed_with_their_next_run(self, app, repo):
        _write(repo, "console/config/schedules.toml", """
[[schedule]]
id = "nightly"
label = "Nightly lint"
expr = "0 2 * * *"
verb = "harness-lint"
enabled = true
""")
        out = call(app, "GET", "/api/schedules")
        row = out["schedules"][0]
        assert row["id"] == "nightly" and row["enabled"] is True
        assert row["next_run"], "an enabled schedule must say when it next runs"
        assert out["enabled_count"] == 1

    def test_a_parked_schedule_has_no_next_run(self, app, repo):
        # Showing a next-run time for something that will never fire is a lie
        # the panel would repeat every time it loaded.
        _write(repo, "console/config/schedules.toml", """
[[schedule]]
id = "parked"
expr = "0 2 * * *"
verb = "harness-lint"
enabled = false
""")
        out = call(app, "GET", "/api/schedules")
        assert out["schedules"][0]["next_run"] == ""
        assert out["enabled_count"] == 0

    def test_a_bad_expression_is_reported_not_swallowed(self, app, repo):
        # The panel must be able to show this. A config error hidden here is
        # discovered on the morning the job did not run.
        _write(repo, "console/config/schedules.toml", """
[[schedule]]
id = "broken"
expr = "@daily"
verb = "harness-lint"
enabled = true
""")
        out = call(app, "GET", "/api/schedules")
        assert out["error"] and "broken" in out["error"]
        assert out["schedules"] == []

    def test_enabled_schedules_sort_before_parked_ones(self, app, repo):
        _write(repo, "console/config/schedules.toml", """
[[schedule]]
id = "zzz-on"
expr = "0 2 * * *"
verb = "harness-lint"
enabled = true

[[schedule]]
id = "aaa-off"
expr = "0 2 * * *"
verb = "harness-lint"
enabled = false
""")
        rows = call(app, "GET", "/api/schedules")["schedules"]
        assert [r["id"] for r in rows] == ["zzz-on", "aaa-off"]


class TestWorktrees:
    def test_a_non_git_workspace_reports_an_error_it_can_show(self, app):
        out = call(app, "GET", "/api/worktrees")
        # Not an exception: plenty of workspaces are not git checkouts, and
        # the panel should say so rather than vanish.
        assert out["worktrees"] == [] and out["error"]


class TestNotify:
    def test_status_reports_presence_and_never_values(self, app, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "12345:super-secret-token")
        out = call(app, "GET", "/api/notify")
        assert "super-secret-token" not in json.dumps(out)
        assert set(["ready", "reason", "token_present", "chat_id_present"]) <= set(out)

    def test_a_disabled_channel_says_why(self, app):
        out = call(app, "GET", "/api/notify")
        assert out["ready"] is False and out["reason"]


class TestAudit:
    def test_an_empty_trail_is_a_normal_answer(self, app):
        out = call(app, "GET", "/api/work/audit")
        assert out["entries"] == [] and out["actions"]

    def test_entries_come_back_newest_first(self, app, repo):
        from server import audit
        for target in ("first", "second", "third"):
            audit.record(repo, "verb.run", target=target)
        rows = call(app, "GET", "/api/work/audit")["entries"]
        assert [r["target"] for r in rows] == ["third", "second", "first"]

    def test_the_limit_is_clamped_rather_than_trusted(self, app, repo):
        from server import audit
        for i in range(5):
            audit.record(repo, "verb.run", target="t%d" % i)
        assert len(call(app, "GET", "/api/work/audit",
                        {"limit": "2"})["entries"]) == 2
        # A hostile or fat-fingered limit must not turn one request into a
        # read of the entire history.
        assert len(call(app, "GET", "/api/work/audit",
                        {"limit": "999999"})["entries"]) == 5
        assert len(call(app, "GET", "/api/work/audit",
                        {"limit": "not-a-number"})["entries"]) == 5

    def test_the_actor_address_survives_to_the_panel(self, app, repo):
        # The whole point of the trail once more than one device can start
        # work: "was that me?" needs an answer.
        from server import audit
        audit.record(repo, "chat.start", actor={"addr": "100.64.0.9", "agent": "x"},
                     target="claude")
        row = call(app, "GET", "/api/work/audit")["entries"][0]
        assert row["actor"]["addr"] == "100.64.0.9"


class TestSpendOnAnalytics:
    """Cost is folded into /api/analytics rather than given its own endpoint,
    so the tab makes one request and cannot half-load."""

    def test_the_analytics_payload_carries_a_spend_block(self, app):
        out = call(app, "GET", "/api/analytics", {"window": "30"})
        assert "spend" in out, "the Analytics tab reads d.spend"
        assert out["spend"]["available"] is True

    def test_no_recorded_turns_is_zero_not_missing(self, app):
        # The panel distinguishes "nothing has run" from "telemetry is
        # broken", and needs a real zero to do it.
        spend = call(app, "GET", "/api/analytics", {"window": "30"})["spend"]
        assert spend["totals"]["turns"] == 0
        assert spend["totals"]["cost_complete"] is True

    def test_an_unpriced_turn_is_counted_and_flagged_never_free(self, app, repo):
        """The property this whole section exists to protect.

        A model with no entry in pricing.toml contributes tokens but no cost.
        If that arrived as a plain number the dashboard would under-report
        spend and be believed.
        """
        from server import telemetry
        telemetry.record_turn(repo, session="s1", backend="openrouter",
                              model="some/unknown-model", ticket="CC-T001",
                              input_tokens=1000, output_tokens=500)
        spend = call(app, "GET", "/api/analytics", {"window": "30"})["spend"]
        totals = spend["totals"]
        assert totals["turns"] == 1
        assert totals["tokens"] == 1500, "tokens are known even when price is not"
        assert totals["unpriced_turns"] == 1
        assert totals["cost_complete"] is False, "the panel renders the * from this"

    def test_a_priced_turn_reports_a_complete_cost(self, app, repo):
        from server import telemetry
        _write(repo, "console/config/pricing.toml", """
[[model]]
id = "test/model"
input_per_mtok = 1.0
output_per_mtok = 2.0
""")
        telemetry.load_pricing(repo, force=True)
        telemetry.record_turn(repo, session="s1", backend="openrouter",
                              model="test/model", ticket="CC-T001",
                              input_tokens=1_000_000, output_tokens=1_000_000)
        spend = call(app, "GET", "/api/analytics", {"window": "30"})["spend"]
        assert spend["totals"]["cost_complete"] is True
        assert spend["totals"]["cost_usd"] == pytest.approx(3.0)

    def test_rows_are_capped_so_one_panel_cannot_render_hundreds(self, app, repo):
        from server import telemetry
        for i in range(20):
            telemetry.record_turn(repo, session="s", backend="openrouter",
                                  model="m%02d" % i, ticket="T%02d" % i,
                                  input_tokens=10, output_tokens=10)
        spend = call(app, "GET", "/api/analytics", {"window": "30"})["spend"]
        assert len(spend["by_model"]) == 8
        assert len(spend["by_ticket"]) == 8
        # The totals still cover everything, not just what is shown.
        assert spend["totals"]["turns"] == 20


class TestJobCancel:
    def test_cancelling_a_queued_job_works_and_is_audited(self, app, repo):
        from server import audit, jobs
        _write(repo, "console/config/verbs.toml", """
[[verb]]
id = "noop"
label = "No-op"
handler = "verb_handlers.ticket_blockers"
needs_ticket = false
""")
        queue = jobs.JobQueue(repo)
        job = queue.submit("noop", submitted_by="test")
        out = call(app, "POST", "/api/jobs/%s/cancel" % job["id"])
        assert out["state"] == "cancelled"
        assert audit.read(repo)[0]["action"] == "job.cancel"

    def test_cancelling_an_unknown_job_raises_rather_than_lying(self, app):
        with pytest.raises(Exception):
            call(app, "POST", "/api/jobs/deadbeef/cancel")

    def test_a_refused_cancel_is_still_recorded(self, app, repo):
        # "I tried to stop it and could not" is exactly the fact you want in
        # the trail afterwards.
        from server import audit
        with pytest.raises(Exception):
            call(app, "POST", "/api/jobs/deadbeef/cancel")
        row = audit.read(repo)[0]
        assert row["action"] == "job.cancel" and "refused" in row["outcome"]


def _write(root, rel, text):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    # These modules cache their config by root; a test that writes one has to
    # clear it or it reads the previous test's answer.
    from server import schedules, telemetry, verbs
    schedules._cache.clear()
    telemetry._pricing_cache.clear()
    verbs._cache.clear()
    boards._console_cache.clear()
