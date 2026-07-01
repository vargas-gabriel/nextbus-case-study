"""
app.py — Streamlit UI: pick a route, direction, and stop from cascading
dropdowns, see how long until the next departure.

Run with:
    streamlit run app.py
"""

import streamlit as st

from nextbus_lib import get_routes, get_directions, get_stops, next_departure_text

st.set_page_config(page_title="Next Bus", page_icon="🚌")
st.title("🚌 Next Bus")
st.caption("Live data from Metro Transit NexTrip v2")


routes = get_routes()
route_labels = sorted(r["route_label"] for r in routes)
route_label = st.selectbox("Route", route_labels)
route = next(r for r in routes if r["route_label"] == route_label)

directions = get_directions(route["route_id"])
direction_names = [d["direction_name"] for d in directions]
direction_name = st.selectbox("Direction", direction_names)
direction = next(d for d in directions if d["direction_name"] == direction_name)

stops = get_stops(route["route_id"], direction["direction_id"])
stop_descriptions = [s["description"] for s in stops]
stop_description = st.selectbox("Stop", stop_descriptions)
stop = next(s for s in stops if s["description"] == stop_description)

if st.button("Get next departure", type="primary"):
    result = next_departure_text(stop["place_code"], route["route_id"], direction["direction_id"])
    if result is None:
        st.warning("No more departures today for this route/stop/direction.")
    else:
        st.success(result)