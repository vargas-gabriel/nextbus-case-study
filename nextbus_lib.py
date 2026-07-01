import time

import requests

BASE_URL = "https://svc.metrotransit.org/nextrip"


def get_json(path):
    resp = requests.get(f"{BASE_URL}/{path}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_routes():
    """Returns [{route_id, route_label, agency_id}, ...]"""
    return get_json("routes")


def get_directions(route_id):
    """Returns [{direction_id, direction_name}, ...] for a given route_id."""
    return get_json(f"directions/{route_id}")


def get_stops(route_id, direction_id):
    """Returns [{place_code, description}, ...] for a given route_id/direction_id."""
    return get_json(f"stops/{route_id}/{direction_id}")


def get_departures(route_id, direction_id, place_code):
    """Returns the raw list of departures for a route/direction/stop (may be empty)."""
    data = get_json(f"{route_id}/{direction_id}/{place_code}")
    return data.get("departures", [])


def next_departure_text(place_code, route_id, direction_id):
    """
    Returns a display string like "2 Minutes" for the soonest departure,
    or None if there are no more departures today.

    Computed from the departure's "departure_time" (Unix epoch seconds)
    rather than the API's own "departure_text" field, since that field
    switches formats (e.g. "2 Min" vs. a clock time like "3:44" for trips
    further out) and we want a consistent "N Minutes" output.
    """
    departures = get_departures(route_id, direction_id, place_code)
    if not departures:
        return None
    soonest = departures[0]
    minutes = round((soonest["departure_time"] - time.time()) / 60)
    return f"{max(minutes, 0)} Minutes"


# --- substring-matching helpers, used by the CLI (not needed by the UI,
# since the UI lets the user pick directly from full dropdown lists) ---

def _ambiguous_error(substring, key, matches):
    """Build an error message listing which candidates matched, not just the count."""
    if len(matches) == 0:
        return f"No match for '{substring}' in {key}"
    labels = ", ".join(repr(m[key]) for m in matches[:10])
    more = f" (+{len(matches) - 10} more)" if len(matches) > 10 else ""
    return f"'{substring}' matches {len(matches)} values in {key}, not 1: {labels}{more}"


def find_unique(items, key, substring):
    """Case-insensitive substring match; raises ValueError unless exactly one match."""
    matches = [i for i in items if substring.lower() in i[key].lower()]
    if len(matches) != 1:
        raise ValueError(_ambiguous_error(substring, key, matches))
    return matches[0]


def find_direction_by_word(directions, direction_word):
    """direction_word is one of north/south/east/west; direction_name always ends in '...bound'."""
    matches = [d for d in directions if d["direction_name"].lower().startswith(direction_word.lower())]
    if len(matches) != 1:
        raise ValueError(_ambiguous_error(direction_word, "direction_name", matches))
    return matches[0]