import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px

# ======================
# Load data
# ======================
df = pd.read_csv(
    "cleaned_collisions_persons.csv",
    parse_dates=["CRASH_DATETIME"]
)

# ========= Extra derived columns =========

# Clean / normalize vehicle types into categories
def normalize_vehicle(v):
    if pd.isna(v):
        return "UNKNOWN"
    s = str(v).upper()

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
    if "PICK" in s or "PICK-UP" in s or "PICKUP" in s:
        return "TRUCK/VAN"
    if "TRUCK" in s or "VAN" in s:
        return "TRUCK/VAN"
    if "SEDAN" in s or "4 DOOR" in s or "4-DOOR" in s or "2 DOOR" in s or "2-DOOR" in s:
        return "CAR"
    return "OTHER"

# If YEAR column isn't already there (safety)
if "YEAR" not in df.columns:
    df["YEAR"] = df["CRASH_DATETIME"].dt.year

# If INJURY_TYPE column isn't already there (safety)
if "INJURY_TYPE" not in df.columns:
    def get_injury_type(person_type):
        if pd.isna(person_type):
            return "UNKNOWN"
        s = str(person_type).upper()
        if "PEDESTRIAN" in s:
            return "PEDESTRIAN"
        if "CYCLIST" in s or "BICYCLIST" in s:
            return "CYCLIST"
        return "MOTORIST"
    df["INJURY_TYPE"] = df["PERSON_TYPE"].apply(get_injury_type)

df["VEHICLE_CATEGORY"] = df["VEHICLE TYPE CODE 1"].apply(normalize_vehicle)

# Drop rows with no coordinates for the map (we'll reuse this after filtering)
# (We’ll still re-dropna after filtering, this is just a base)
df_map_base = df.dropna(subset=["LATITUDE", "LONGITUDE"])

# ======================
# Options for dropdowns
# ======================
borough_options = [
    {"label": b.title(), "value": b}
    for b in sorted(df["BOROUGH"].dropna().unique())
]

year_options = [
    {"label": str(int(y)), "value": int(y)}
    for y in sorted(df["YEAR"].dropna().unique())
]

vehicle_options = [
    {"label": v, "value": v}
    for v in sorted(df["VEHICLE_CATEGORY"].dropna().unique())
]

factor_options = [
    {"label": f.title(), "value": f}
    for f in sorted(df["CONTRIBUTING FACTOR VEHICLE 1"].dropna().unique())
]

injury_type_options = [
    {"label": i.title(), "value": i}
    for i in sorted(df["INJURY_TYPE"].dropna().unique())
]

# ======================
# Build app
# ======================
app = Dash(__name__)

app.layout = html.Div(
    style={"fontFamily": "Arial", "padding": "20px"},
    children=[
        html.H1("NYC Motor Vehicle Collisions – Interactive Report"),

        # ---- FILTERS ROW ----
        html.Div(
            style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
            children=[
                dcc.Dropdown(
                    id="filter-borough",
                    options=borough_options,
                    placeholder="Select Borough",
                    multi=True,
                    style={"width": "200px"},
                ),
                dcc.Dropdown(
                    id="filter-year",
                    options=year_options,
                    placeholder="Select Year",
                    multi=True,
                    style={"width": "150px"},
                ),
                dcc.Dropdown(
                    id="filter-vehicle",
                    options=vehicle_options,
                    placeholder="Vehicle Category",
                    multi=True,
                    style={"width": "220px"},
                ),
                dcc.Dropdown(
                    id="filter-factor",
                    options=factor_options,
                    placeholder="Contributing Factor",
                    multi=True,
                    style={"width": "280px"},
                ),
                dcc.Dropdown(
                    id="filter-injury",
                    options=injury_type_options,
                    placeholder="Injury Type (Pedestrian/Cyclist/Motorist)",
                    multi=True,
                    style={"width": "280px"},
                ),
            ],
        ),

        html.Br(),

        # ---- SEARCH + BUTTON ----
        html.Div(
            style={"display": "flex", "gap": "10px", "alignItems": "center"},
            children=[
                dcc.Input(
                    id="search-box",
                    type="text",
                    placeholder="Search (e.g. 'Brooklyn 2022 pedestrian crashes')",
                    style={"width": "400px"},
                ),
                html.Button(
                    "Generate Report",
                    id="btn-generate",
                    n_clicks=0,
                    style={"padding": "10px 20px", "fontWeight": "bold"},
                ),
            ],
        ),

        # message area (no data / how many rows)
        html.Div(
            id="no-data-message",
            style={"color": "red", "fontWeight": "bold", "marginTop": "10px"},
        ),

        html.Br(),

        # ---- GRAPHS ----
        html.Div(
            children=[
                dcc.Graph(id="graph-bar-borough"),
                dcc.Graph(id="graph-line-time"),
                dcc.Graph(id="graph-map"),
            ]
        ),
    ],
)

# ======================
# Helper: apply search text
# ======================
BOROUGHS = ["BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND"]

def apply_search_text(df_in, text):
    """
    Reads free text like:
    'Brooklyn 2022 pedestrian crashes'
    and applies borough, year, and injury type filters.
    """
    if not text:
        return df_in, None, None, None  # no extra filters

    text_u = text.upper()

    # Borough from text
    borough_from_text = None
    for b in BOROUGHS:
        if b in text_u:
            borough_from_text = b
            break

    # Year from text (first 4-digit number that looks like a year)
    year_from_text = None
    for token in text_u.split():
        if token.isdigit() and len(token) == 4:
            y = int(token)
            if 2012 <= y <= 2030:
                year_from_text = y
                break

    # Injury type from text
    injury_from_text = None
    if "PEDESTRIAN" in text_u:
        injury_from_text = "PEDESTRIAN"
    elif "CYCLIST" in text_u or "BICYCLE" in text_u:
        injury_from_text = "CYCLIST"
    elif "MOTORIST" in text_u or "DRIVER" in text_u:
        injury_from_text = "MOTORIST"

    df_out = df_in.copy()
    if borough_from_text:
        df_out = df_out[df_out["BOROUGH"] == borough_from_text]
    if year_from_text:
        df_out = df_out[df_out["YEAR"] == year_from_text]
    if injury_from_text:
        df_out = df_out[df_out["INJURY_TYPE"] == injury_from_text]

    return df_out, borough_from_text, year_from_text, injury_from_text

# ======================
# Main callback
# ======================
@app.callback(
    [
        Output("graph-bar-borough", "figure"),
        Output("graph-line-time", "figure"),
        Output("graph-map", "figure"),
        Output("no-data-message", "children"),
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
def update_report(n_clicks,
                  boroughs, years, vehicles, factors, injuries, search_text):

    # base df
    dff = df.copy()

    # --- apply dropdown filters ---
    if boroughs:
        dff = dff[dff["BOROUGH"].isin(boroughs)]
    if years:
        dff = dff[dff["YEAR"].isin(years)]
    if vehicles:
        dff = dff[dff["VEHICLE_CATEGORY"].isin(vehicles)]
    if factors:
        dff = dff[dff["CONTRIBUTING FACTOR VEHICLE 1"].isin(factors)]
    if injuries:
        dff = dff[dff["INJURY_TYPE"].isin(injuries)]

    # --- apply search text (extra filters) ---
    dff, _, _, _ = apply_search_text(dff, search_text)

    # If no data after filters → empty figs + message
    if dff.empty:
        empty_fig = px.scatter()
        empty_fig.update_layout(title="No data")
        msg = "No data for selected filters. Try removing some filters or changing your search."
        return empty_fig, empty_fig, empty_fig, msg

    # ========== BAR: crashes per borough ==========
    bar_df = (
        dff.groupby("BOROUGH")
        .size()
        .reset_index(name="crash_count")
        .sort_values("crash_count", ascending=False)
    )
    fig_bar = px.bar(
        bar_df,
        x="BOROUGH",
        y="crash_count",
        title="Number of Crashes by Borough",
    )

    # ========== LINE: crashes over time (by year) ==========
    time_df = (
        dff.groupby("YEAR")
        .size()
        .reset_index(name="crash_count")
        .sort_values("YEAR")
    )
    fig_line = px.line(
        time_df,
        x="YEAR",
        y="crash_count",
        markers=True,
        title="Crashes Over Time",
    )

    # ========== MAP: crash locations ==========
    map_df = dff.dropna(subset=["LATITUDE", "LONGITUDE"])
    # to avoid overloading, sample max 5000 points
    if len(map_df) > 5000:
        map_df = map_df.sample(5000, random_state=42)

    fig_map = px.scatter_mapbox(
        map_df,
        lat="LATITUDE",
        lon="LONGITUDE",
        color="INJURY_TYPE",
        zoom=9,
        height=500,
        hover_data=["CRASH DATE", "BOROUGH", "PERSON_INJURY"],
        title="Crash Locations (sample)",
    )
    fig_map.update_layout(mapbox_style="open-street-map")

    msg = f"Showing {len(dff)} matching records."
    return fig_bar, fig_line, fig_map, msg


# ======================
# Run server
# ======================
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host="0.0.0.0", port=port)