"""
list_data.py — dump current routes/directions/stops from the live NexTrip API,
so you can eyeball valid (unique) substrings to test nextbus.py with instead
of writing a one-off `requests` call each time.

This deliberately does NOT enforce uniqueness like nextbus.py does — it's a
discovery tool, so it shows every match.

Usage:
    python list_data.py                     # list every route
    python list_data.py "ROUTE SUBSTRING"   # list matching routes + their
                                             # directions + stops per direction
"""

import argparse

from nextbus import get_json


def get_routes():
    return get_json("routes")


def get_directions(route_id):
    return get_json(f"directions/{route_id}")


def get_stops(route_id, direction_id):
    return get_json(f"stops/{route_id}/{direction_id}")


def list_all_routes():
    routes = sorted(get_routes(), key=lambda r: r["route_label"].lower())
    print(f"{len(routes)} routes:\n")
    for r in routes:
        print(f"  {r['route_label']!r}  (route_id={r['route_id']})")


def list_route_detail(route_substring):
    routes = [r for r in get_routes() if route_substring.lower() in r["route_label"].lower()]
    if not routes:
        print(f"No routes matching '{route_substring}'")
        return

    print(f"{len(routes)} route(s) matching '{route_substring}':\n")
    for route in routes:
        print(f"= {route['route_label']!r} (route_id={route['route_id']}) =")
        directions = get_directions(route["route_id"])
        for direction in directions:
            print(f"  -- {direction['direction_name']} (direction_id={direction['direction_id']}) --")
            stops = get_stops(route["route_id"], direction["direction_id"])
            if not stops:
                print("     (no stops)")
            for stop in stops:
                print(f"     {stop['description']!r}  (place_code={stop['place_code']})")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="List live routes, or directions/stops for routes matching a substring."
    )
    parser.add_argument("route", nargs="?", default=None,
                        help="Optional substring to filter routes (shows directions + stops if given)")
    args = parser.parse_args()

    if args.route is None:
        list_all_routes()
    else:
        list_route_detail(args.route)


if __name__ == "__main__":
    main()