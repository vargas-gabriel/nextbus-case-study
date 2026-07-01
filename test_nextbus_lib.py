"""
Tests for nextbus_lib.py.

These mock get_json / time.time rather than hitting the live NexTrip API —
real transit data changes hour to hour (routes get replaced by buses during
construction, stop lists shrink for detours, etc.), so tests need fixed,
known inputs to be reliable.

Run with:
    pytest test_nextbus_lib.py
"""

import pytest

import nextbus_lib as lib


# --- find_unique -----------------------------------------------------------

def test_find_unique_single_match():
    items = [{"route_label": "METRO Green Line"}, {"route_label": "Route 2"}]
    result = lib.find_unique(items, "route_label", "green")
    assert result["route_label"] == "METRO Green Line"


def test_find_unique_no_match_raises():
    items = [{"route_label": "METRO Green Line"}]
    with pytest.raises(ValueError, match="No match"):
        lib.find_unique(items, "route_label", "purple")


def test_find_unique_multiple_matches_raises_with_labels():
    items = [{"route_label": "Route 2"}, {"route_label": "Route 25"}, {"route_label": "Route 27"}]
    with pytest.raises(ValueError) as exc_info:
        lib.find_unique(items, "route_label", "Route 2")
    message = str(exc_info.value)
    assert "matches 3 values" in message
    assert "Route 25" in message  # lists the actual candidates, not just a count


def test_find_unique_is_case_insensitive():
    items = [{"route_label": "METRO Green Line"}]
    result = lib.find_unique(items, "route_label", "GREEN")
    assert result["route_label"] == "METRO Green Line"


# --- find_direction_by_word -------------------------------------------------

def test_find_direction_by_word_matches_prefix():
    directions = [{"direction_id": 0, "direction_name": "Eastbound"},
                  {"direction_id": 1, "direction_name": "Westbound"}]
    result = lib.find_direction_by_word(directions, "west")
    assert result["direction_id"] == 1


def test_find_direction_by_word_no_match_raises():
    directions = [{"direction_id": 0, "direction_name": "Eastbound"}]
    with pytest.raises(ValueError):
        lib.find_direction_by_word(directions, "north")


# --- next_departure_text -----------------------------------------------------

def test_next_departure_text_computes_minutes(monkeypatch):
    fake_now = 1_000_000_000
    monkeypatch.setattr(lib.time, "time", lambda: fake_now)
    monkeypatch.setattr(
        lib, "get_departures",
        lambda route_id, direction_id, place_code: [{"departure_time": fake_now + 300}],  # 5 min out
    )
    result = lib.next_departure_text("ABCD", "94", 0)
    assert result == "5 Minutes"


def test_next_departure_text_no_departures_returns_none(monkeypatch):
    monkeypatch.setattr(lib, "get_departures", lambda route_id, direction_id, place_code: [])
    result = lib.next_departure_text("ABCD", "94", 0)
    assert result is None


def test_next_departure_text_never_negative(monkeypatch):
    """A departure_time slightly in the past (clock skew / just-departed edge case)
    should clamp to 0 rather than print a negative number."""
    fake_now = 1_000_000_000
    monkeypatch.setattr(lib.time, "time", lambda: fake_now)
    monkeypatch.setattr(
        lib, "get_departures",
        lambda route_id, direction_id, place_code: [{"departure_time": fake_now - 30}],
    )
    result = lib.next_departure_text("ABCD", "94", 0)
    assert result == "0 Minutes"


# --- get_json / get_departures: verify the URL shape, not live data --------

def test_get_departures_calls_correct_url_order(monkeypatch):
    """Regression test for the route_id/direction_id/place_code URL bug."""
    captured = {}

    def fake_get_json(path):
        captured["path"] = path
        return {"departures": []}

    monkeypatch.setattr(lib, "get_json", fake_get_json)
    lib.get_departures("94", 0, "5CED")
    assert captured["path"] == "94/0/5CED"


def test_get_stops_calls_correct_url(monkeypatch):
    captured = {}

    def fake_get_json(path):
        captured["path"] = path
        return []

    monkeypatch.setattr(lib, "get_json", fake_get_json)
    lib.get_stops("94", 1)
    assert captured["path"] == "stops/94/1"
