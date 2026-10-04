"""FR-12: `run_failures.parse_reset` turns a quota notice or reset prose into a
UTC `retry_not_before`, or "" when it cannot be sure. Fixed clocks only; the
real-zone cases skip (with a reason) when the host has no tz database."""

import zoneinfo
from datetime import datetime, timedelta, timezone

import pytest

from server import run_failures
from server.run_failures import classify, parse_reset

CFG = {"quota_parse_horizon_secs": 8 * 86400}


def _utc(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _chicago_fake(name):
    """Fixed CDT (-5) stand-in for America/Chicago: always available."""
    if name == "America/Chicago":
        return timezone(timedelta(hours=-5))
    raise zoneinfo.ZoneInfoNotFoundError(name)


def _real_chicago_available():
    try:
        zoneinfo.ZoneInfo("America/Chicago")
        return True
    except Exception:
        return False


FIXTURES = [  # (prose, now, expected UTC)
    ("You're out of extra usage · resets 4pm (America/Chicago)",
     "2026-04-22T15:15:00Z", "2026-04-22T21:00:00Z"),
    ("You've hit your session limit - resets at 4pm (America/Chicago).",
     "2026-04-22T15:15:00Z", "2026-04-22T21:00:00Z"),
    ("You've hit your limit · resets 2:30am (UTC)",
     "2026-08-28T22:30:00Z", "2026-08-29T02:30:00Z"),
    ("You're out of extra usage · resets 4:30pm (America/Chicago)",
     "2026-04-22T15:15:00Z", "2026-04-22T21:30:00Z"),
    # 4pm Chicago already passed today (18:30 local): rolls to tomorrow.
    ("You're out of extra usage · resets 4pm (America/Chicago)",
     "2026-04-22T23:30:00Z", "2026-04-23T21:00:00Z"),
]


class TestProse:
    @pytest.mark.parametrize("text,now,want", FIXTURES)
    def test_paperclip_fixtures_with_fixed_now(self, text, now, want):
        assert parse_reset(None, text, _utc(now), CFG, _zone=_chicago_fake) == want

    @pytest.mark.skipif(not _real_chicago_available(),
                        reason="no tz database on this host (zoneinfo America/Chicago)")
    @pytest.mark.parametrize("text,now,want", FIXTURES)
    def test_paperclip_fixtures_with_real_zoneinfo(self, text, now, want):
        # Dates are inside CDT, so the real database agrees with the fixed stand-in.
        assert parse_reset(None, text, _utc(now), CFG) == want

    def test_zoneinfo_not_found_returns_empty_class_stays_quota(self, monkeypatch):
        def boom(name):
            raise zoneinfo.ZoneInfoNotFoundError(name)
        monkeypatch.setattr(zoneinfo, "ZoneInfo", boom)
        text = "You've hit your limit · resets 4pm (America/Chicago)"
        now = _utc("2026-04-22T15:15:00Z")
        assert parse_reset(None, text, now, CFG) == ""
        turn = {"subtype": "success", "is_error": True, "result": text, "errors": [],
                "error": "", "api_error_status": None, "stop_reason": ""}
        out = classify(turn, None, 1, "", now=now, cfg=CFG)
        assert out["class"] == "quota" and out["retry_not_before"] == ""

    def test_utc_parses_without_tzdata(self, monkeypatch):
        def boom(name):
            raise zoneinfo.ZoneInfoNotFoundError(name)
        monkeypatch.setattr(zoneinfo, "ZoneInfo", boom)
        for zone in ("UTC", "utc", "GMT"):
            got = parse_reset(None, "You've hit your limit · resets 2:30am (%s)" % zone,
                              _utc("2026-08-28T22:30:00Z"), CFG)
            assert got == "2026-08-29T02:30:00Z"

    def test_host_local_when_no_zone_given(self):
        now = _utc("2026-04-22T15:15:00Z")
        got = parse_reset(None, "You've hit your limit · resets 4pm", now, CFG)
        assert got
        when = _utc(got)
        assert now < when <= now + timedelta(days=1)
        assert (when.astimezone().hour, when.astimezone().minute) == (16, 0)

    def test_12am_12pm_12_00am_and_13pm_rejected(self):
        now = _utc("2026-04-22T15:15:00Z")

        def at(t):
            return parse_reset(None, "You've hit your limit · resets %s (UTC)" % t, now, CFG)
        assert at("12am") == "2026-04-23T00:00:00Z"
        assert at("12:00am") == "2026-04-23T00:00:00Z"
        assert at("12pm") == "2026-04-23T12:00:00Z"  # 12:00 today is already past
        assert parse_reset(None, "You've hit your limit · resets 12pm (UTC)",
                           _utc("2026-04-22T09:00:00Z"), CFG) == "2026-04-22T12:00:00Z"
        assert at("13pm") == ""
        assert at("0am") == ""
        assert at("1:75pm") == ""

    def test_prose_without_a_quota_marker_is_ignored(self):
        assert parse_reset(None, "The cache resets 4pm (UTC) daily",
                           _utc("2026-04-22T15:15:00Z"), CFG) == ""


class TestNotice:
    NOW = _utc("2026-04-22T15:15:00Z")

    def _rl(self, resets_at, status="rejected"):
        return {"status": status, "resets_at": resets_at}

    def test_seconds_and_milliseconds_same_instant(self):
        secs = int(self.NOW.timestamp()) + 3 * 3600
        a = parse_reset(self._rl(secs), "", self.NOW, CFG)
        b = parse_reset(self._rl(secs * 1000), "", self.NOW, CFG)
        assert a == b == "2026-04-22T18:15:00Z"

    def test_past_or_beyond_horizon_is_empty(self):
        ts = int(self.NOW.timestamp())
        assert parse_reset(self._rl(ts - 60), "", self.NOW, CFG) == ""
        assert parse_reset(self._rl((ts - 60) * 1000), "", self.NOW, CFG) == ""
        assert parse_reset(self._rl(ts + 9 * 86400), "", self.NOW, CFG) == ""
        assert parse_reset(self._rl(ts + 8 * 86400), "", self.NOW, CFG) != ""

    def test_only_a_rejected_notice_counts_and_zero_means_unknown(self):
        ts = int(self.NOW.timestamp()) + 600
        assert parse_reset(self._rl(ts, "allowed"), "", self.NOW, CFG) == ""
        assert parse_reset(self._rl(0), "", self.NOW, CFG) == ""
        assert parse_reset(self._rl("soon"), "", self.NOW, CFG) == ""

    def test_classify_fills_retry_not_before_for_quota(self):
        ts = int(self.NOW.timestamp()) + 3600
        turn = {"subtype": "success", "is_error": True, "result": "stopped", "errors": [],
                "error": "", "api_error_status": None, "stop_reason": ""}
        out = classify(turn, self._rl(ts), 1, "", now=self.NOW, cfg=CFG)
        assert out["class"] == "quota" and out["retry_not_before"] == "2026-04-22T16:15:00Z"
        # No clock given: stays "" (classify itself never reads one).
        assert classify(turn, self._rl(ts), 1, "")["retry_not_before"] == ""
