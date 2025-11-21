# app.py
import os
import sys
import logging

import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px

# ------- Logging -------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("collision-dash-app")

# ------- Config -------
CSV_FILENAME = "cleaned_collisions_persons.csv"
DEFAULT_PORT = int(os.environ.get("PORT", 8050))

# ------- Load data (safe) -------
try:
    df = pd.read_csv(CSV_FILENAME, parse_dates=["CRASH_DATETIME"])
    log.info(f"Loaded {CSV_FILENAME}, {len(df)} rows")
except FileNotFoundError:
    log.exception(f"Could not find {CSV_FILENAME}. Make sure it is included in the repo root.")
    # create an empty minimal dataframe so the app still starts and shows "no data"
    df = pd.DataFrame(
        columns=[
            "CRASH_DATETIME",
            "VEHICLE TYPE CODE 1",
            "BOROUGH",
            "YEAR",
            "CONTRIBUTING FACTOR VEHICLE 1",
            "INJURY_TYPE",
            "LATITUDE",
            "LONGITUDE",
        ]
    )
except Exception:
    log.exception("Unexpected error while loading CSV")
    sys.exit(1)

# Ensure YEAR column exists
if "YEAR" not in df.columns and "CRASH_DATETIME" in df.columns:
    try:
        df["YEAR"] = pd.to_datetime(df["CRASH_DATETIME"], errors="coerce").dt.year
    except Exception:
        df["YEAR"] = None

# ------- Normalizer (fixed casing and typos) -------
def normalize_vehicle(v):
    if pd.isna(v):
        return "UNKNOWN"
    s = str(v).upper()

    if "AMB" in s or "AMBUL" in s:
        return "AMBULANCE"
    if "TAXI" in s:
        return "TAXI"
    if "BUS" in s:
        return "BUS"
    if "MOTORCYCLE" in s or "SCOOTER" in s or "MOTORBIKE" in s:
        return "MOTORCYCLE"
    if "BICYCLE" in s or "BIKE" in s:
        return "BICYCLE"
    if "SUV" in s or "STATION WAGON" in s:
        return "SUV"
    if "PICK" in s or "PICK-UP" in s or "PICKUP" in s or "VAN" in s or "TRUCK" in s:
        return "TRUCK/VAN"
    if (
        "SEDAN" in s
        or "4 DOOR" in s
        or "4-DOOR" in s
        or "2 DOOR" in s
        or "2-DOOR" in s
    ):
        return "CAR"
    return "OTHER"

# Only apply if column exists
if "VEHICLE TYPE CODE 1" in df.columns:
    df["VEHICLE_CATEGORY"] = df["VEHICLE TYPE CODE 1"].apply(normalize_vehicle)
else:
    df["VEHICLE_CATEGORY"] = "UNKNOWN"

# ------- Options helpers (safe: handle missing columns) -------
def unique_options(col):
    if col in df.columns:
        vals = sorted(df[col].dropna().unique())
        # convert numeric years to int safely
        options = []
        for v in vals:
            if isinstance(v, (float, int)) and pd.notna(v):
                try:
                    options.append({"label": str(int(v)), "value": int(v)})
                except Exception:
                    options.append({"label": str(v), "value": v})
            else:
                options.append({"label": str(v).title(), "value": v})
        return options
    return []

borough_options = unique_options("BOROUGH")
year_options = unique_options("YEAR")
vehicle_options = unique_options("VEHICLE_CATEGORY")
factor_options = unique_options("CONTRIBUTING FACTOR VEHICLE 1")
injury_type_options = unique_options("INJURY_TYPE")

# ------- Dash app -------
app = Dash(__name__)
app.title = "Collision Dash"

app.layout = html.Div(
    style={"fontFamily": "Arial", "padding": "20px"},
    children=[
        html.H1("NYC Motor Vehicle Collisions – Interactive Dashboard"),
        html.Div(
            style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
            children=[
                dcc.Dropdown(id="filter-borough", options=borough_options, placeholder="Select Borough", multi=True, style={"width": "200px"}),
                dcc.Dropdown(id="filter-year", options=year_options, placeholder="Select Year", multi=True, style={"width": "150px"}),
                dcc.Dropdown(id="filter-vehicle", options=vehicle_options, placeholder="Vehicle Type", multi=True, style={"width": "200px"}),
                dcc.Dropdown(id="filter-factor", options=factor_options, placeholder="Contributing Factor", multi=True, style={"width": "250px"}),
                dcc.Dropdown(id="filter-injury", options=injury_type_options, placeholder="Injury Type", multi=True, style={"width": "220px"}),
            ],
        ),
        html.Br(),
        html.Div(
            style={"display": "flex", "gap": "10px"},
            children=[
                dcc.Input(id="search-box", type="text", placeholder="Search (e.g. 'Brooklyn 2022 pedestrian crashes')", style={"width": "400px"}),
                html.Button("Generate Report", id="btn-generate", n_clicks=0, style={"padding": "10px 20px", "fontWeight": "bold"}),
            ],
        ),
        html.Br(),
        dcc.Graph(id="graph-bar-borough"),
        dcc.Graph(id="graph-line-time"),
        dcc.Graph(id="graph-map"),
    ],
)

# ------- Search parsing -------
BOROUGHS = [b.upper() for b in (df["BOROUGH"].dropna().unique() if "BOROUGH" in df.columns else ["BRONX","BROOKLYN","MANHATTAN","QUEENS","STATEN ISLAND"])]

def apply_search_text(df_in, text):
    if not text:
        return df_in, None, None, None
    text_u = text.upper()
    borough_from_text = next((b for b in BOROUGHS if b in text_u), None)
    year_from_text = None
    for token in text_u.split():
        if token.isdigit() and len(token) == 4:
            try:
                y = int(token)
                if 1900 <= y <= 2100:
                    year_from_text = y
                    break
            except Exception:
                continue
    injury_from_text = None
    if "PEDESTRIAN" in text_u:
        injury_from_text = "PEDESTRIAN"
    elif "CYCLIST" in text_u or "BICYCLE" in text_u:
        injury_from_text = "CYCLIST"
    elif "MOTORIST" in text_u or "DRIVER" in text_u:
        injury_from_text = "MOTORIST"

    df_out = df_in.copy(deep=False)
    if borough_from_text and "BOROUGH" in df_out.columns:
        df_out = df_out[df_out["BOROUGH"] == borough_from_text]
    if year_from_text and "YEAR" in df_out.columns:
        df_out = df_out[df_out["YEAR"] == year_from_text]
    if injury_from_text and "INJURY_TYPE" in df_out.columns:
        df_out = df_out[df_out["INJURY_TYPE"] == injury_from_text]
    return df_out, borough_from_text, year_from_text, injury_from_text

# ------- Callback -------
@app.callback(
    [
        Output("graph-bar-borough", "figure"),
        Output("graph-line-time", "figure"),
        Output("graph-map", "figure"),
    ],
    Input("btn-generate", "n_clicks"),
    [
        State("filter-borough", "value"),
        State("filter-year", "value"),
        State("filter-vehicle", "value"),
        State("filter-factor", "value"),
        State("filter-injury", "value"),
        State("search-box", "value"),
    ],
)
def update_report(n_clicks, boroughs, years, vehicles, factors, injuries, search_text):
    dff = df.copy()

    if boroughs and "BOROUGH" in dff.columns:
        dff = dff[dff["BOROUGH"].isin(boroughs)]
    if years and "YEAR" in dff.columns:
        dff = dff[dff["YEAR"].isin(years)]
    if vehicles and "VEHICLE_CATEGORY" in dff.columns:
        dff = dff[dff["VEHICLE_CATEGORY"].isin(vehicles)]
    if factors and "CONTRIBUTING FACTOR VEHICLE 1" in dff.columns:
        dff = dff[dff["CONTRIBUTING FACTOR VEHICLE 1"].isin(factors)]
    if injuries and "INJURY_TYPE" in dff.columns:
        dff = dff[dff["INJURY_TYPE"].isin(injuries)]

    dff, _, _, _ = apply_search_text(dff, search_text)

    if dff.empty:
        empty_fig = px.scatter(title="No data found for selected filters.")
        return empty_fig, empty_fig, empty_fig

    # Bar chart
    if "BOROUGH" in dff.columns:
        bar_df = dff.groupby("BOROUGH").size().reset_index(name="crash_count")
        fig_bar = px.bar(bar_df, x="BOROUGH", y="crash_count", title="Crashes by Borough")
    else:
        fig_bar = px.scatter(title="No borough data available.")

    # Line chart
    if "YEAR" in dff.columns:
        time_df = dff.groupby("YEAR").size().reset_index(name="crash_count").sort_values("YEAR")
        fig_line = px.line(time_df, x="YEAR", y="crash_count", markers=True, title="Crashes Over Time")
    else:
        fig_line = px.scatter(title="No time-series data available.")

    # Map (density if location exists)
    if "LATITUDE" in dff.columns and "LONGITUDE" in dff.columns:
        map_df = dff.dropna(subset=["LATITUDE", "LONGITUDE"])
        if map_df.empty:
            fig_map = px.scatter(title="No location data available.")
        else:
            sample = map_df.sample(min(8000, len(map_df)), random_state=0)
            try:
                fig_map = px.density_mapbox(
                    sample,
                    lat="LATITUDE",
                    lon="LONGITUDE",
                    radius=10,
                    center={"lat": sample["LATITUDE"].mean(), "lon": sample["LONGITUDE"].mean()},
                    zoom=9,
                    height=500,
                    title="Crash Density (sample)",
                )
                fig_map.update_layout(mapbox_style="open-street-map")
            except Exception:
                # Fallback to scatter_mapbox if density_mapbox fails
                fig_map = px.scatter_mapbox(sample, lat="LATITUDE", lon="LONGITUDE", zoom=9, height=500, title="Crash Locations (sample)")
                fig_map.update_layout(mapbox_style="open-street-map")
    else:
        fig_map = px.scatter(title="No location columns present.")

    return fig_bar, fig_line, fig_map

# ------- WSGI server for gunicorn/railway/render -------
server = app.server

if __name__ == "__main__":
    # Local debug run
    log.info(f"Starting local server on 0.0.0.0:{DEFAULT_PORT}")
    app.run(host="0.0.0.0", port=DEFAULT_PORT, debug=False)
