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
# Dash App
# ======================
app = Dash(__name__)
server = app.server   # VERY IMPORTANT FOR RAILWAY + GUNICORN

app.layout = html.Div(
    style={"fontFamily": "Arial", "padding": "20px"},
    children=[
        html.H1("NYC Motor Vehicle Collisions – Interactive Dashboard"),

        html.Div(
            style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
            children=[
                dcc.Dropdown(id="filter-borough", options=borough_options,
                             placeholder="Select Borough", multi=True, style={"width": "200px"}),
                dcc.Dropdown(id="filter-year", options=year_options,
                             placeholder="Select Year", multi=True, style={"width": "150px"}),
                dcc.Dropdown(id="filter-vehicle", options=vehicle_options,
                             placeholder="Vehicle Type", multi=True, style={"width": "200px"}),
                dcc.Dropdown(id="filter-factor", options=factor_options,
                             placeholder="Contributing Factor", multi=True, style={"width": "250px"}),
                dcc.Dropdown(id="filter-injury", options=injury_type_options,
                             placeholder="Injury Type", multi=True, style={"width": "220px"}),
            ],
        ),

        html.Br(),

        html.Div(
            style={"display": "flex", "gap": "10px"},
            children=[
                dcc.Input(id="search-box", type="text",
                          placeholder="Search crashes...", style={"width": "400px"}),
                html.Button("Generate Report", id="btn-generate",
                            n_clicks=0, style={"padding": "10px 20px", "fontWeight": "bold"}),
            ],
        ),

        html.Br(),
        html.Div(id="output")
    ],
)

# ======================
# Callbacks
# ======================
@app.callback(
    Output("output", "children"),
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
def update_report(n, borough, year, vehicle, factor, injury, search):
    if not n:
        return ""

    filtered = df.copy()

    if borough:
        filtered = filtered[filtered["BOROUGH"].isin(borough)]
    if year:
        filtered = filtered[filtered["YEAR"].isin(year)]
    if vehicle:
        filtered = filtered[filtered["VEHICLE_CATEGORY"].isin(vehicle)]
    if factor:
        filtered = filtered[filtered["CONTRIBUTING FACTOR VEHICLE 1"].isin(factor)]
    if injury:
        filtered = filtered[filtered["INJURY_TYPE"].isin(injury)]

    if search:
        search_lower = search.lower()
        filtered = filtered[
            filtered.apply(lambda row: search_lower in str(row).lower(), axis=1)
        ]

    fig = px.histogram(
        filtered, x="CRASH_DATETIME",
        title="Crashes Over Time", nbins=50
    )

    return dcc.Graph(figure=fig)

# ======================
# Local Debug
# ======================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
