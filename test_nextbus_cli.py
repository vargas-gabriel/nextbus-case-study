"""
Tests for the standalone nextbus.py (single-file version: no nextbus_lib
import, everything goes through its own get_json()).

Everything is driven through monkeypatching nextbus.get_json (and
nextbus.time.time where needed) rather than hitting the live NexTrip API —
real transit data changes hour to hour, so tests need fixed, known inputs.

Run with:
    pytest test_nextbus_cli.py
"""

import sys

import pytest

import nextbus


FIXED_NOW = 1_000_000_000


def fake_get_json_factory(departure_offset_seconds=300):
    """Builds a fake get_json() covering the full route -> direction -> stop ->
    departures chain for a single known-good route (id 94)."""
    def fake_get_json(path):
        if path == "routes":
            return [{"route_id": "94", "route_label": "Route 94"}]
        if path == "directions/94":
            return [
                {"direction_id": 0, "direction_name": "Eastbound"},
                {"direction_id": 1, "direction_name": "Westbound"},
            ]
        if path == "stops/94/0":
            return [{"place_code": "UNDP", "description": "Union Depot"}]
        if path == "94/0/UNDP":
            return {"departures": [{"departure_time": FIXED_NOW + departure_offset_seconds}]}
        raise AssertionError(f"unexpected path passed to get_json: {path!r}")
    return fake_get_json


# --- find_route / find_direction / find_stop --------------------------------

def test_find_route_unique_match(monkeypatch):
    monkeypatch.setattr(nextbus, "get_json", lambda path: [{"route_id": "94", "route_label": "Route 94"}])
    result = nextbus.find_route("Route 94")
    assert result["route_id"] == "94"


def test_find_route_ambiguous_exits_with_candidates(monkeypatch):
    monkeypatch.setattr(nextbus, "get_json", lambda path: [
        {"route_id": "2", "route_label": "Route 2"},
        {"route_id": "25", "route_label": "Route 25"},
    ])
    # sys.exit(message) stores the message as the SystemExit's .code / str()
    # value — it's only ever *printed* to stderr if the exception reaches the
    # top of the interpreter unhandled, which pytest.raises intercepts before
    # that happens. So assert against the exception itself, not capsys.
    with pytest.raises(SystemExit) as exc_info:
        nextbus.find_route("Route 2")
    message = str(exc_info.value)
    assert "matches 2 routes" in message
    assert "Route 25" in message  # lists what it matched, not just a count


def test_find_route_no_match_exits(monkeypatch):
    monkeypatch.setattr(nextbus, "get_json", lambda path: [{"route_id": "94", "route_label": "Route 94"}])
    with pytest.raises(SystemExit):
        nextbus.find_route("Purple Line")


def test_find_direction_matches_prefix(monkeypatch):
    monkeypatch.setattr(nextbus, "get_json", lambda path: [
        {"direction_id": 0, "direction_name": "Eastbound"},
        {"direction_id": 1, "direction_name": "Westbound"},
    ])
    result = nextbus.find_direction("94", "west")
    assert result["direction_id"] == 1


def test_find_stop_unique_match(monkeypatch):
    monkeypatch.setattr(nextbus, "get_json", lambda path: [{"place_code": "UNDP", "description": "Union Depot"}])
    result = nextbus.find_stop("94", 0, "Union Depot")
    assert result["place_code"] == "UNDP"


# --- get_next_departure_minutes ---------------------------------------------

def test_get_next_departure_minutes_computes_correctly(monkeypatch):
    monkeypatch.setattr(nextbus.time, "time", lambda: FIXED_NOW)
    monkeypatch.setattr(nextbus, "get_json", lambda path: {"departures": [{"departure_time": FIXED_NOW + 300}]})
    assert nextbus.get_next_departure_minutes("UNDP", "94", 0) == 5


def test_get_next_departure_minutes_no_departures_returns_none(monkeypatch):
    monkeypatch.setattr(nextbus, "get_json", lambda path: {"departures": []})
    assert nextbus.get_next_departure_minutes("UNDP", "94", 0) is None


def test_get_next_departure_minutes_never_negative(monkeypatch):
    monkeypatch.setattr(nextbus.time, "time", lambda: FIXED_NOW)
    monkeypatch.setattr(nextbus, "get_json", lambda path: {"departures": [{"departure_time": FIXED_NOW - 30}]})
    assert nextbus.get_next_departure_minutes("UNDP", "94", 0) == 0


def test_get_next_departure_minutes_url_order(monkeypatch):
    """Regression test for the route_id/direction_id/place_code URL bug."""
    captured = {}

    def fake_get_json(path):
        captured["path"] = path
        return {"departures": []}

    monkeypatch.setattr(nextbus, "get_json", fake_get_json)
    nextbus.get_next_departure_minutes("UNDP", "94", 0)
    assert captured["path"] == "94/0/UNDP"


# --- main() end-to-end (get_json mocked, nothing else) -----------------------

def test_main_happy_path_prints_minutes(monkeypatch, capsys):
    monkeypatch.setattr(nextbus, "get_json", fake_get_json_factory(departure_offset_seconds=300))
    monkeypatch.setattr(nextbus.time, "time", lambda: FIXED_NOW)
    monkeypatch.setattr(sys, "argv", ["nextbus.py", "Route 94", "Union Depot", "east"])

    nextbus.main()

    assert capsys.readouterr().out.strip() == "5 Minutes"


def test_main_prints_nothing_when_no_departures(monkeypatch, capsys):
    def fake_get_json(path):
        if path == "routes":
            return [{"route_id": "94", "route_label": "Route 94"}]
        if path == "directions/94":
            return [{"direction_id": 0, "direction_name": "Eastbound"}]
        if path == "stops/94/0":
            return [{"place_code": "UNDP", "description": "Union Depot"}]
        if path == "94/0/UNDP":
            return {"departures": []}
        raise AssertionError(path)

    monkeypatch.setattr(nextbus, "get_json", fake_get_json)
    monkeypatch.setattr(sys, "argv", ["nextbus.py", "Route 94", "Union Depot", "east"])

    nextbus.main()

    assert capsys.readouterr().out == ""


def test_main_exits_on_ambiguous_route(monkeypatch):
    monkeypatch.setattr(nextbus, "get_json", lambda path: [
        {"route_id": "2", "route_label": "Route 2"},
        {"route_id": "25", "route_label": "Route 25"},
    ])
    monkeypatch.setattr(sys, "argv", ["nextbus.py", "Route 2", "Union Depot", "east"])

    with pytest.raises(SystemExit) as exc_info:
        nextbus.main()

    assert "matches 2 routes" in str(exc_info.value)


def test_main_rejects_invalid_direction(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["nextbus.py", "Route 94", "Union Depot", "northeast"])
    with pytest.raises(SystemExit):
        nextbus.main()  # argparse itself rejects it before any API code runs
