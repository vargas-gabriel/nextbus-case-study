import argparse
import sys
import time

import requests

BASE_URL = "https://svc.metrotransit.org/nextrip"


def get_json(path):
    resp = requests.get(f"{BASE_URL}/{path}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def _die_on_ambiguous(substring, kind, matches, label_key):
    """Print which candidates matched (not just the count) so the caller can pick a tighter substring."""
    if len(matches) == 0:
        sys.exit(f"No {kind} matching '{substring}'")
    labels = ", ".join(repr(m[label_key]) for m in matches[:10])
    more = f" (+{len(matches) - 10} more)" if len(matches) > 10 else ""
    sys.exit(f"'{substring}' matches {len(matches)} {kind}s, not 1: {labels}{more}")


def find_route(route_substring):
    """GET /routes -> the single route whose route_label contains route_substring."""
    routes = get_json("routes")
    matches = [r for r in routes if route_substring.lower() in r["route_label"].lower()]
    if len(matches) != 1:
        _die_on_ambiguous(route_substring, "route", matches, "route_label")
    return matches[0]


def find_direction(route_id, direction_word):
    """GET /directions/{route_id} -> the direction whose name starts with direction_word."""
    directions = get_json(f"directions/{route_id}")
    matches = [d for d in directions if d["direction_name"].lower().startswith(direction_word.lower())]
    if len(matches) != 1:
        _die_on_ambiguous(direction_word, "direction", matches, "direction_name")
    return matches[0]


def find_stop(route_id, direction_id, stop_substring):
    """GET /stops/{route_id}/{direction_id} -> the single stop whose description contains stop_substring."""
    stops = get_json(f"stops/{route_id}/{direction_id}")
    matches = [s for s in stops if stop_substring.lower() in s["description"].lower()]
    if len(matches) != 1:
        _die_on_ambiguous(stop_substring, "stop", matches, "description")
    return matches[0]


def get_next_departure_minutes(place_code, route_id, direction_id):
    """
    GET /{route_id}/{direction_id}/{place_code} -> departures for this stop/route/direction.

    Each departure has a "departure_time" (Unix epoch seconds). We compute
    minutes-from-now ourselves rather than parsing the API's own
    "departure_text" (e.g. "2 Min" vs. a clock time like "3:44" for trips
    further out), since that keeps the output format consistent.
    """
    data = get_json(f"{route_id}/{direction_id}/{place_code}")
    departures = data.get("departures", [])
    if not departures:
        return None  # no more departures today
    soonest = departures[0]
    minutes = round((soonest["departure_time"] - time.time()) / 60)
    return max(minutes, 0)


def main():
    parser = argparse.ArgumentParser(description="Time until next departure on a route/stop/direction.")
    parser.add_argument("route", help="Substring of the route name")
    parser.add_argument("stop", help="Substring of the stop name")
    parser.add_argument("direction", type=str.lower, choices=["north", "south", "east", "west"],
                        help="Direction of travel")
    args = parser.parse_args()

    route = find_route(args.route)
    direction = find_direction(route["route_id"], args.direction)
    stop = find_stop(route["route_id"], direction["direction_id"], args.stop)

    minutes = get_next_departure_minutes(stop["place_code"], route["route_id"], direction["direction_id"])
    if minutes is None:
        return  # last departure of the day already left; print nothing per spec

    print(f"{minutes} Minutes")


if __name__ == "__main__":
    main()

