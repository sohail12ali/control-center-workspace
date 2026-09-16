"""Change-notification bus (T-017 FR-3/A5, decision-log a8 — task 1e-4).

Scoped to MCP resource subscribers only; nothing here talks to the console
board UI. See `bus.py`'s module docstring for the pull-not-push rationale.
"""

from server.bus import Bus


class TestSubscribeAndPublish:
    def test_a_subscribed_session_receives_a_published_change(self):
        bus = Bus()
        bus.subscribe("s1", "ticket://T-001")
        bus.publish("ticket://T-001")
        pending = bus.drain("s1")
        assert len(pending) == 1
        assert pending[0]["uri"] == "ticket://T-001"

    def test_an_unsubscribed_session_receives_nothing(self):
        bus = Bus()
        bus.publish("ticket://T-001")
        assert bus.drain("s1") == []

    def test_publish_to_a_uri_nobody_subscribed_to_is_a_no_op(self):
        bus = Bus()
        bus.subscribe("s1", "ticket://T-001")
        bus.publish("ticket://T-002")
        assert bus.drain("s1") == []

    def test_drain_clears_the_queue_delivered_at_most_once(self):
        bus = Bus()
        bus.subscribe("s1", "ticket://T-001")
        bus.publish("ticket://T-001")
        bus.drain("s1")
        assert bus.drain("s1") == []

    def test_multiple_sessions_each_get_their_own_copy(self):
        bus = Bus()
        bus.subscribe("s1", "ticket://T-001")
        bus.subscribe("s2", "ticket://T-001")
        bus.publish("ticket://T-001")
        assert len(bus.drain("s1")) == 1
        assert len(bus.drain("s2")) == 1

    def test_unsubscribe_one_uri_stops_future_notifications_for_it_only(self):
        bus = Bus()
        bus.subscribe("s1", "ticket://T-001")
        bus.subscribe("s1", "ticket://T-002")
        bus.unsubscribe("s1", "ticket://T-001")
        bus.publish("ticket://T-001")
        bus.publish("ticket://T-002")
        pending = bus.drain("s1")
        assert [p["uri"] for p in pending] == ["ticket://T-002"]

    def test_unsubscribe_with_no_uri_drops_every_subscription(self):
        bus = Bus()
        bus.subscribe("s1", "ticket://T-001")
        bus.subscribe("s1", "ticket://T-002")
        bus.unsubscribe("s1")
        bus.publish("ticket://T-001")
        bus.publish("ticket://T-002")
        assert bus.drain("s1") == []

    def test_subscribed_reports_current_state(self):
        bus = Bus()
        assert bus.subscribed("s1", "ticket://T-001") is False
        bus.subscribe("s1", "ticket://T-001")
        assert bus.subscribed("s1", "ticket://T-001") is True
