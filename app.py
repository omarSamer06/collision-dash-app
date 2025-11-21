import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px

# ======================
# Load data
# ======================
df = pd.read_csv("cleaned_collisions_persons.csv", parse_dates=["CRASH_DATETIME"])

# ======================
# Vehicle category cleaner
# ======================
def normalize_vehicle(v):
    if pd.isna(v):
        return "UNKNOWN"
    s = str(v).upper()

    # Ambulance variants
    if "AMB" in s or "AMBUL" in s:
        return "AMBULANCE"

    if "TAXI" in s:
        return "TAXI"
    if "BUS" in s:
        return "BUS"
    if "MOTORCYCLE" in s or "SCOOTER" in s or "MOTORBIKE" in s:
        return "MOTORcycle"
    if "BICYCLE" in s or "BIKE" in s:
        return "BICYCLE"
    if "SUV" in s or "STATION WAGON" in s:
        return "SUV"
    if "PICK" in s or "PICK-UP" in s or "PICKUP" in s:
        return "TRUCK/VAN"
    if "TRUCK" in s or "VAN" in s:
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

# Apply cleaning
df["VEHICLE_CATEGORY"] = df["VEHICLE TYPE CODE 1"].apply(normalize_vehicle)

# ======================
# Dropdown options
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
# Build Dash app
# ======================
app = Dash(__name__)

app.layout = html.Div(
    style={"fontFamily": "Arial", "padding": "20px"},
    children=[
        html.H1("NYC Motor Vehicle Collisions – Interactive Dashboard"),

        # Filters row
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
                    placeholder="Vehicle Type",
                    multi=True,
                    style={"width": "200px"},
                ),
                dcc.Dropdown(
                    id="filter-factor",
                    options=factor_options,
                    placeholder="Contributing Factor",
                    multi=True,
                    style={"width": "250px"},
                ),
                dcc.Dropdown(
                    id="filter-injury",
                    options=injury_type_options,
                    placeholder="Injury Type",
                    multi=True,
                    style={"width": "220px"},
                ),
            ],
        ),

        html.Br(),

        # Search + Button
        html.Div(
            style={"display": "flex", "gap": "10px"},
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

        html.Br(),

        # Graphs
        dcc.Graph(id="graph-bar-borough"),
        dcc.Graph(id="graph-line-time"),
        dcc.Graph(id="graph-map"),
    ],
)

# ======================
# Search-text logic
# ======================
BOROUGHS = ["BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND"]

def apply_search_text(df_in, text):
    if not text:
        return df_in, None, None, None

    text_u = text.upper()

    # Find borough
    borough_from_text = next((b for b in BOROUGHS if b in text_u), None)

    # Year extraction
    year_from_text = None
    for token in text_u.split():
        if token.isdigit() and len(token) == 4:
            y = int(token)
            if 2012 <= y <= 2030:
                year_from_text = y
                break

    # Injury type
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

    # Dropdown filters
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

    # Apply search
    dff, _, _, _ = apply_search_text(dff, search_text)

    # Handle empty result
    if dff.empty:
        empty_fig = px.scatter(title="No data found.")
        return empty_fig, empty_fig, empty_fig

    # Bar chart
    bar_df = (
        dff.groupby("BOROUGH").size().reset_index(name="crash_count")
    )
    fig_bar = px.bar(
        bar_df,
        x="BOROUGH",
        y="crash_count",
        title="Crashes by Borough",
    )

    # Line chart
    time_df = (
        dff.groupby("YEAR").size().reset_index(name="crash_count")
    )
    fig_line = px.line(
        time_df,
        x="YEAR",
        y="crash_count",
        markers=True,
        title="Crashes Over Time",
    )

    # Map
    map_df = dff.dropna(subset=["LATITUDE", "LONGITUDE"])
    fig_map = px.scatter_mapbox(
        map_df.sample(min(5000, len(map_df))),
        lat="LATITUDE",
        lon="LONGITUDE",
        color="INJURY_TYPE",
        zoom=9,
        height=500,
        title="Crash Locations (sample)",
    )
    fig_map.update_layout(mapbox_style="open-street-map")

    return fig_bar, fig_line, fig_map

# ======================
# Render / Deployment config
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host="0.0.0.0", port=port)

    import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px

# ======================
# Load data
# ======================
df = pd.read_csv("cleaned_collisions_persons.csv", parse_dates=["CRASH_DATETIME"])

# If YEAR column is not already in the CSV, uncomment this:
# df["YEAR"] = df["CRASH_DATETIME"].dt.year

# ======================
# Vehicle category cleaner
# ======================
def normalize_vehicle(v):
    if pd.isna(v):
        return "UNKNOWN"
    s = str(v).upper()

    # Ambulance variants
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
    if "PICK" in s or "PICK-UP" in s or "PICKUP" in s:
        return "TRUCK/VAN"
    if "TRUCK" in s or "VAN" in s:
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

df["VEHICLE_CATEGORY"] = df["VEHICLE TYPE CODE 1"].apply(normalize_vehicle)

# ======================
# Dropdown options
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
# Build Dash app
# ======================
app = Dash(__name__)

app.layout = html.Div(
    style={"fontFamily": "Arial", "padding": "20px"},
    children=[
        html.H1("NYC Motor Vehicle Collisions – Interactive Dashboard"),

        # Filters row
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
                    placeholder="Vehicle Type",
                    multi=True,
                    style={"width": "200px"},
                ),
                dcc.Dropdown(
                    id="filter-factor",
                    options=factor_options,
                    placeholder="Contributing Factor",
                    multi=True,
                    style={"width": "250px"},
                ),
                dcc.Dropdown(
                    id="filter-injury",
                    options=injury_type_options,
                    placeholder="Injury Type",
                    multi=True,
                    style={"width": "220px"},
                ),
            ],
        ),

        html.Br(),

        # Search + Button
        html.Div(
            style={"display": "flex", "gap": "10px"},
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

        html.Br(),

        # Graphs (all interactive)
        dcc.Graph(id="graph-bar-borough"),
        dcc.Graph(id="graph-line-time"),
        dcc.Graph(id="graph-map"),   # heatmap-style map
    ],
)

# ======================
# Search-text logic
# ======================
BOROUGHS = ["BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND"]

def apply_search_text(df_in, text):
    if not text:
        return df_in, None, None, None

    text_u = text.upper()

    borough_from_text = next((b for b in BOROUGHS if b in text_u), None)

    year_from_text = None
    for token in text_u.split():
        if token.isdigit() and len(token) == 4:
            y = int(token)
            if 2012 <= y <= 2030:
                year_from_text = y
                break

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

    # Dropdown filters
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

    # Apply search text
    dff, _, _, _ = apply_search_text(dff, search_text)

    # Handle empty result
    if dff.empty:
        empty_fig = px.scatter(title="No data found for selected filters.")
        return empty_fig, empty_fig, empty_fig

    # ----- BAR: crashes by borough -----
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
        title="Crashes by Borough",
    )

    # ----- LINE: crashes over time -----
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

    # ----- HEATMAP MAP: density of crashes -----
    map_df = dff.dropna(subset=["LATITUDE", "LONGITUDE"])
    if map_df.empty:
        fig_map = px.scatter(title="No location data available.")
    else:
        map_sample = map_df.sample(min(8000, len(map_df)), random_state=0)
        fig_map = px.density_mapbox(
            map_sample,
            lat="LATITUDE",
            lon="LONGITUDE",
            radius=12,  # controls blur / heat radius
            center={"lat": 40.7128, "lon": -74.0060},
            zoom=9,
            height=500,
            hover_data={
                "BOROUGH": True,
                "CRASH_DATETIME": True,
                "INJURY_TYPE": True,
            },
            title="Crash Density Heatmap (sample)",
        )
        fig_map.update_layout(mapbox_style="open-street-map")

    return fig_bar, fig_line, fig_map

# ======================
# Render / Deployment config
# ======================
# ---- Required for Railway / Gunicorn ----
server = app.server

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))


    
