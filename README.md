# nextbus

Tells you how long until the next bus/train on a given route, leaving from a
given stop, going a given direction — using the Metro Transit NexTrip v2 API
(`https://svc.metrotransit.org/nextrip/`). No API key required.

## Files

- `nextbus.py` + `nextbus_lib.py` — command-line script (substring args,
  matches the assignment spec) built on a shared API-helper module
- `nextbus_standalone.py` — the same CLI logic as a single self-contained
  file (no local imports besides `requests`)
- `app.py` — Streamlit UI with cascading dropdowns for route / direction / stop
- `list_data.py` — discovery helper: dumps current routes, or
  directions/stops for a route substring, so you can find valid test inputs
  without writing a one-off API call (depends on `nextbus_standalone.py`
  being in the same folder)

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## CLI usage

```
python nextbus.py "BUS ROUTE" "BUS STOP NAME" DIRECTION
```

`BUS ROUTE` and `BUS STOP NAME` are substrings that must uniquely identify a
route (across all routes) and a stop (on that route/direction), respectively.
`DIRECTION` is one of `north`, `south`, `east`, `west`. If a substring matches
more than one candidate, the error message lists what it matched so you can
narrow it down.

### Example

```
python nextbus.py "Route 94" "Union Depot" east
```

If the last departure of the day has already left, the script prints nothing.

## Finding valid test inputs

Route/stop names and which stops are currently in service can change (e.g.
during construction or detours), so a fixed example may stop working. Use:

```
python list_data.py                  # every current route
python list_data.py "Route 9"        # matching routes + their directions + stops
```

## UI usage

```
streamlit run app.py
```

Opens a browser tab. Pick a route, then a direction (populated for that
route), then a stop (populated for that route/direction), then click
"Get next departure".

## Tests

```
pip install -r requirements-dev.txt
pytest
```

`test_nextbus_lib.py` and `test_nextbus_cli.py` mock the API layer (`get_json`
et al.) rather than hitting the live NexTrip API, since real transit data
changes hour to hour — a test asserting against today's actual departures
would break tomorrow. They cover substring matching (unique / zero / multiple
matches), direction-word matching, the minutes-from-`departure_time`
calculation (including the URL-order regression that broke this earlier), and
the CLI's happy path / no-departures / ambiguous-input / invalid-direction
cases.

## API notes

- `GET /nextrip/routes` -> `[{route_id, route_label}, ...]`
- `GET /nextrip/directions/{route_id}` -> `[{direction_id, direction_name}, ...]`
- `GET /nextrip/stops/{route_id}/{direction_id}` -> `[{place_code, description}, ...]`
- `GET /nextrip/{route_id}/{direction_id}/{place_code}` -> `{stops, alerts,
  departures}`; each departure has a `departure_time` (Unix epoch seconds)
  used to compute the "N Minutes" output
