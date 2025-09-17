import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objs as go
import pandas as pd
import csv
import copy
import os
import base64

# ---------------------------------------------------------------------
# Configuration and Constants
# ---------------------------------------------------------------------
TRAVERSAL_TIME_ARR = [0, 13, 18, 27, 42, 72]  # CCG -> DR -> BA -> AND -> BOR -> VR
STATION_MAP = {"CCG": 0, "DR": 1, "BA": 2, "AND": 3, "BOR": 4, "VR": 5}
STATION_ORDER = ["CCG", "DR", "BA", "AND", "BOR", "VR"]

# ---------------------------------------------------------------------
# OD Pair Class
# ---------------------------------------------------------------------
class ODPair:
    def __init__(self, sr_num, originating_at_time, originating_stn, destin_stn, fast_or_slow,
                 traversal_time, destination_time, service_type, linkedToBefore=None,
                 linkedToAfter=None, induction=None, stabilizationAt=None, is_ac=False):
        self.sr_num = int(sr_num)
        self.originating_at_time = int(originating_at_time)
        self.originating_stn = originating_stn
        self.destin_stn = destin_stn
        self.fast_or_slow = fast_or_slow
        self.traversal_time = int(traversal_time)
        self.destination_time = int(destination_time)
        self.service_type = service_type
        self.is_ac = is_ac
        self.linkedToBefore = linkedToBefore
        self.linkedToAfter = linkedToAfter
        self.induction = induction
        self.stabilizationAt = stabilizationAt

    def __repr__(self):
        return (f"ODPair(SrNum={self.sr_num}, OriginTime={self.originating_at_time}, "
                f"From='{self.originating_stn}', To='{self.destin_stn}', "
                f"Type='{self.fast_or_slow}', Travel={self.traversal_time}, DestiTime={self.destination_time},"
                f" ServiceType={self.service_type}, AC={self.is_ac}, linkedToBefore={self.linkedToBefore}, linkedToAfter={self.linkedToAfter})")


# ---------------------------------------------------------------------
# Data Processing Functions
# ---------------------------------------------------------------------
def load_odpairs_from_csv(filepath):
    """Load OD pairs from CSV file, skipping dummy rows"""
    od_pairs = []
    with open(filepath, newline='') as csvfile:
        reader = csv.reader(csvfile)
        rows = list(reader)

        for row in rows:
            if not row or not row[0].isdigit():
                continue  # skip blank/dummy rows

            # Check if AC status provided (example column 9 or more). Adjust if your CSV layout differs.
            is_ac = False
            if len(row) > 9 and row[9].strip().lower() in ['true', 'ac', '1', 'yes']:
                is_ac = True

            od_pair = ODPair(
                sr_num=int(row[0]),
                originating_at_time=int(row[4]),
                originating_stn=row[5],
                destin_stn=row[6],
                fast_or_slow=row[7],
                traversal_time=int(row[8]),
                destination_time=int(row[4]) + int(row[8]),
                service_type=row[3],
                is_ac=is_ac
            )
            od_pairs.append(od_pair)
    return od_pairs


def correct_traversal_time(od_pairs):
    """Correct traversal times based on station positions"""
    for od in od_pairs:
        if od.service_type == "nonlocal":
            continue
        od.traversal_time = abs(TRAVERSAL_TIME_ARR[STATION_MAP[od.destin_stn]] -
                               TRAVERSAL_TIME_ARR[STATION_MAP[od.originating_stn]])
        od.destination_time = od.originating_at_time + od.traversal_time


def augment_od_pairs(od_pairs):
    """Augment OD pairs to create complete rake cycles (kept same logic as your original)"""
    od_pairs_new = od_pairs.copy()

    for od in od_pairs:
        if od.service_type == "nonlocal":
            continue

        direction = 1 if STATION_MAP[od.destin_stn] > STATION_MAP[od.originating_stn] else -1

        # Direction +1 (up). Kept same cases as earlier code.
        if direction == 1:
            if od.originating_stn == "CCG" and od.destin_stn != "VR":
                od_pair = ODPair(
                    sr_num=(od_pairs_new[-1].sr_num + 1),
                    originating_at_time=int(od.destination_time),
                    originating_stn=od.destin_stn,
                    destin_stn="VR",
                    fast_or_slow=od.fast_or_slow,
                    traversal_time=int(TRAVERSAL_TIME_ARR[5] - TRAVERSAL_TIME_ARR[STATION_MAP[od.destin_stn]]),
                    destination_time=int(od.destination_time + TRAVERSAL_TIME_ARR[5] - TRAVERSAL_TIME_ARR[STATION_MAP[od.destin_stn]]),
                    service_type=od.service_type,
                    is_ac=od.is_ac,
                    linkedToBefore=od.sr_num,
                    linkedToAfter=None
                )
                od.linkedToAfter = od_pair.sr_num

                od_pair2 = ODPair(
                    sr_num=(od_pairs_new[-1].sr_num + 2),
                    originating_at_time=int(od.originating_at_time + TRAVERSAL_TIME_ARR[5]),
                    originating_stn="VR",
                    destin_stn="CCG",
                    fast_or_slow=od.fast_or_slow,
                    traversal_time=int(TRAVERSAL_TIME_ARR[5]),
                    destination_time=int(od.originating_at_time + 2 * TRAVERSAL_TIME_ARR[5]),
                    service_type=od.service_type,
                    is_ac=od.is_ac,
                    linkedToBefore=od_pair.sr_num,
                    linkedToAfter=None
                )
                od_pair.linkedToAfter = od_pair2.sr_num
                od_pairs_new.append(od_pair)
                od_pairs_new.append(od_pair2)

            elif od.destin_stn == "VR" and od.originating_stn != "CCG":
                od_pair = ODPair(
                    sr_num=(od_pairs_new[-1].sr_num + 1),
                    originating_at_time=int(od.originating_at_time - TRAVERSAL_TIME_ARR[STATION_MAP[od.originating_stn]]),
                    originating_stn="CCG",
                    destin_stn=od.originating_stn,
                    fast_or_slow=od.fast_or_slow,
                    traversal_time=int(TRAVERSAL_TIME_ARR[STATION_MAP[od.originating_stn]]),
                    destination_time=int(od.originating_at_time),
                    service_type=od.service_type,
                    is_ac=od.is_ac,
                    linkedToBefore=None,
                    linkedToAfter=od.sr_num
                )
                od.linkedToBefore = od_pair.sr_num

                od_pair2 = ODPair(
                    sr_num=(od_pairs_new[-1].sr_num + 2),
                    originating_at_time=int(od.destination_time),
                    originating_stn="VR",
                    destin_stn="CCG",
                    fast_or_slow=od.fast_or_slow,
                    traversal_time=int(TRAVERSAL_TIME_ARR[5]),
                    destination_time=int(od.destination_time + TRAVERSAL_TIME_ARR[5]),
                    service_type=od.service_type,
                    is_ac=od.is_ac,
                    linkedToBefore=od.sr_num,
                    linkedToAfter=None
                )
                od.linkedToAfter = od_pair2.sr_num
                od_pairs_new.append(od_pair)
                od_pairs_new.append(od_pair2)

            elif od.originating_stn != "CCG" and od.destin_stn != "VR":
                od_pair_before = ODPair(
                    sr_num=(od_pairs_new[-1].sr_num + 1),
                    originating_at_time=int(od.originating_at_time - TRAVERSAL_TIME_ARR[STATION_MAP[od.originating_stn]]),
                    originating_stn="CCG",
                    destin_stn=od.originating_stn,
                    fast_or_slow=od.fast_or_slow,
                    traversal_time=int(TRAVERSAL_TIME_ARR[STATION_MAP[od.originating_stn]]),
                    destination_time=int(od.originating_at_time),
                    service_type=od.service_type,
                    is_ac=od.is_ac,
                    linkedToBefore=None,
                    linkedToAfter=od.sr_num
                )

                od_pair_after = ODPair(
                    sr_num=(od_pairs_new[-1].sr_num + 2),
                    originating_at_time=int(od.destination_time),
                    originating_stn=od.destin_stn,
                    destin_stn="VR",
                    fast_or_slow=od.fast_or_slow,
                    traversal_time=int(TRAVERSAL_TIME_ARR[5] - TRAVERSAL_TIME_ARR[STATION_MAP[od.destin_stn]]),
                    destination_time=int(od.destination_time + TRAVERSAL_TIME_ARR[5] - TRAVERSAL_TIME_ARR[STATION_MAP[od.destin_stn]]),
                    service_type=od.service_type,
                    is_ac=od.is_ac,
                    linkedToBefore=od.sr_num,
                    linkedToAfter=None
                )

                od_pair_return = ODPair(
                    sr_num=(od_pairs_new[-1].sr_num + 3),
                    originating_at_time=int(od.destination_time + TRAVERSAL_TIME_ARR[5] - TRAVERSAL_TIME_ARR[STATION_MAP[od.destin_stn]]),
                    originating_stn="VR",
                    destin_stn="CCG",
                    fast_or_slow=od.fast_or_slow,
                    traversal_time=int(TRAVERSAL_TIME_ARR[5]),
                    destination_time=int(od.destination_time + 2 * TRAVERSAL_TIME_ARR[5] - TRAVERSAL_TIME_ARR[STATION_MAP[od.destin_stn]]),
                    service_type=od.service_type,
                    is_ac=od.is_ac,
                    linkedToBefore=od_pair_after.sr_num,
                    linkedToAfter=None
                )

                od_pair_after.linkedToAfter = od_pair_return.sr_num
                od.linkedToBefore = od_pair_before.sr_num
                od.linkedToAfter = od_pair_after.sr_num

                od_pairs_new.append(od_pair_before)
                od_pairs_new.append(od_pair_after)
                od_pairs_new.append(od_pair_return)

            else:  # CCG to VR
                od_pair = ODPair(
                    sr_num=(od_pairs_new[-1].sr_num + 1),
                    originating_at_time=int(od.destination_time),
                    originating_stn="VR",
                    destin_stn="CCG",
                    fast_or_slow=od.fast_or_slow,
                    traversal_time=int(TRAVERSAL_TIME_ARR[5]),
                    destination_time=int(od.destination_time + TRAVERSAL_TIME_ARR[5]),
                    service_type=od.service_type,
                    is_ac=od.is_ac,
                    linkedToBefore=od.sr_num,
                    linkedToAfter=None
                )
                od.linkedToAfter = od_pair.sr_num
                od_pairs_new.append(od_pair)

        # Direction -1 (down) could be implemented similarly if you need it.
    return od_pairs_new


def change_time(od_pairs_linked, arr_idx, dep_idx):
    """Change timing of departure train and propagate to linked trains"""
    diff = od_pairs_linked[arr_idx].destination_time - od_pairs_linked[dep_idx].originating_at_time
    od_pairs_linked[dep_idx].originating_at_time += diff
    od_pairs_linked[dep_idx].destination_time += diff

    srnum_to_index = {od.sr_num: idx for idx, od in enumerate(od_pairs_linked)}

    current_idx = dep_idx
    while od_pairs_linked[current_idx].linkedToAfter is not None:
        next_srnum = od_pairs_linked[current_idx].linkedToAfter
        next_idx = srnum_to_index[next_srnum]
        od_pairs_linked[next_idx].originating_at_time += diff
        od_pairs_linked[next_idx].destination_time += diff
        current_idx = next_idx


def link_from_bottom(od_pairs_new):
    """Link trains from bottom station (CCG) for optimal rake utilization"""
    od_pairs_linked = copy.deepcopy(od_pairs_new)
    departures = [i for i, od in enumerate(od_pairs_linked)
                  if od.originating_stn == "CCG" and od.service_type == "local"]
    arrivals = [i for i, od in enumerate(od_pairs_linked)
                if od.destin_stn == "CCG" and od.service_type == "local"]

    for i, arr_idx in enumerate(arrivals):
        if arr_idx == -1:
            continue

        for j, dep_idx in enumerate(departures):
            if departures[j] == -1:
                continue

            arrival_time = od_pairs_linked[arr_idx].destination_time
            departure_time = od_pairs_linked[dep_idx].originating_at_time

            # Link trains with same type and within 20-minute turnaround
            if (od_pairs_linked[arr_idx].service_type == od_pairs_linked[dep_idx].service_type and
                    od_pairs_linked[arr_idx].fast_or_slow == od_pairs_linked[dep_idx].fast_or_slow and
                    od_pairs_linked[arr_idx].is_ac == od_pairs_linked[dep_idx].is_ac and
                    abs(arrival_time - departure_time) <= 20):

                change_time(od_pairs_linked, arr_idx, dep_idx)
                departures[j] = -1
                arrivals[i] = -1
                break

    return od_pairs_linked


# ---------------------------------------------------------------------
# Railway Visualizer
# ---------------------------------------------------------------------
class RailwayVisualizer:
    def __init__(self, od_pairs=None):
        # safe default
        self.od_pairs = od_pairs or []

        # Build station positions from STATION_ORDER to keep consistent vertical ordering
        self.station_positions = {stn: idx for idx, stn in enumerate(STATION_ORDER)}

        self.colors = {
            "AC": "#2E86C1",        # Blue
            "NONAC": "#E74C3C",     # Red
            "SELECTED": "rgba(46, 134, 193, 0.3)"
        }

    def interpolate_points(self, x1, y1, x2, y2, num_points=10):
        """Create interpolated points along a line segment"""
        if num_points <= 0:
            return [], []
        
        x_points = []
        y_points = []
        
        for i in range(num_points + 1):  # +1 to include both endpoints
            t = i / num_points
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            x_points.append(x)
            y_points.append(y)
            
        return x_points, y_points

    def make_figure(self, selected_services=None):
        selected_services = selected_services or []
        fig = go.Figure()

        for od in self.od_pairs:
            # service id consistent with selection strings used elsewhere
            service_id = f"S{od.sr_num}"

            # station y positions
            origin_y = self.station_positions.get(od.originating_stn, 0)
            dest_y = self.station_positions.get(od.destin_stn, 0)

            # color & style
            # if od.service_type.lower() == "nonlocal":
            #     color = self.colors["NONLOCAL"]
            #     line_style = "solid"
            #     line_width = 2
            #     marker_symbol = "circle"
            # else:
            color = self.colors["AC"] if od.is_ac else self.colors["NONAC"]
            line_style = "solid" if str(od.fast_or_slow).strip().lower() == "fast" else "dash"
            line_width = 3 if od.is_ac else 2
            marker_symbol = "circle" if od.is_ac else "square"

            hovertemplate = (
                f"Service: {service_id}<br>"
                f"From: {od.originating_stn} ({od.originating_at_time})<br>"
                f"To: {od.destin_stn} ({od.destination_time})<br>"
                f"Type: {od.fast_or_slow} {od.service_type}<br>"
                f"AC: {'Yes' if od.is_ac else 'No'}<extra></extra>"
            )

            # Create interpolated points for better selection along the line
            x_points, y_points = self.interpolate_points(
                od.originating_at_time, origin_y, 
                od.destination_time, dest_y, 
                num_points=20  # Increase this for even better coverage
            )

            # Main visible trace with interpolated points
            fig.add_trace(go.Scatter(
                x=x_points,
                y=y_points,
                mode="lines+markers",
                line=dict(color=color, width=line_width, dash=line_style),
                marker=dict(
                    size=[8 if i in [0, len(x_points)-1] else 4 for i in range(len(x_points))],  # Larger markers at endpoints
                    symbol=marker_symbol, 
                    color=color,
                    opacity=[1.0 if i in [0, len(x_points)-1] else 0.3 for i in range(len(x_points))]  # Semi-transparent intermediate points
                ),
                name=service_id,
                customdata=[service_id] * len(x_points),
                meta=service_id,
                hovertemplate=hovertemplate,
                showlegend=False,
                connectgaps=True
            ))

            # Optional: Add a thicker invisible overlay for even easier clicking
            # This creates a wider "hit area" around the line
            fig.add_trace(go.Scatter(
                x=[od.originating_at_time, od.destination_time],
                y=[origin_y, dest_y],
                mode="lines",
                line=dict(color="rgba(0,0,0,0.01)", width=20),  # Very transparent, wide line
                hoverinfo="skip",  # Don't show hover for this overlay
                customdata=[service_id, service_id],
                meta=service_id,
                showlegend=False
            ))

            # Highlight selected services
            if service_id in selected_services:
                fig.add_trace(go.Scatter(
                    x=[od.originating_at_time, od.destination_time],
                    y=[origin_y, dest_y],
                    mode="lines",
                    line=dict(color=self.colors["SELECTED"], width=12),
                    hoverinfo="skip",
                    showlegend=False,
                    customdata=[service_id, service_id],
                    meta=service_id
                ))

        # layout
        fig.update_layout(
            title="Railway Timetable Visualization",
            xaxis_title="Time (Minutes from Midnight)",
            yaxis=dict(
                tickmode="array",
                tickvals=list(self.station_positions.values()),
                ticktext=list(self.station_positions.keys())
            ),
            clickmode="event+select",
            hovermode="closest",
            height=600,
            margin=dict(l=50, r=50, t=60, b=50),
            showlegend=False
        )
        return fig

    def load_from_csv(self, filepath):
        od_pairs = load_odpairs_from_csv(filepath)
        correct_traversal_time(od_pairs)
        od_pairs_augmented = augment_od_pairs(od_pairs)
        od_pairs_linked = link_from_bottom(od_pairs_augmented)
        self.od_pairs = od_pairs_linked
        return self

    def to_records(self):
        return [
            {
                "sr_num": od.sr_num,
                "originating_at_time": od.originating_at_time,
                "originating_stn": od.originating_stn,
                "destin_stn": od.destin_stn,
                "fast_or_slow": od.fast_or_slow,
                "traversal_time": od.traversal_time,
                "destination_time": od.destination_time,
                "service_type": od.service_type,
                "is_ac": getattr(od, 'is_ac', False),
                "linkedToBefore": od.linkedToBefore,
                "linkedToAfter": od.linkedToAfter
            }
            for od in self.od_pairs
        ]

    @classmethod
    def from_records(cls, records):
        od_pairs = [
            ODPair(
                sr_num=r["sr_num"],
                originating_at_time=r["originating_at_time"],
                originating_stn=r["originating_stn"],
                destin_stn=r["destin_stn"],
                fast_or_slow=r["fast_or_slow"],
                traversal_time=r["traversal_time"],
                destination_time=r["destination_time"],
                service_type=r["service_type"],
                is_ac=r.get("is_ac", False),
                linkedToBefore=r.get("linkedToBefore"),
                linkedToAfter=r.get("linkedToAfter")
            )
            for r in records
        ]
        return cls(od_pairs)


# ---------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------
def create_sample_data():
    sample_od_pairs = [
        ODPair(1, 480, "CCG", "BA", "Fast", 45, 525, "local", is_ac=True),
        ODPair(2, 486, "CCG", "BA", "Slow", 60, 546, "local", is_ac=False),
        ODPair(3, 500, "CCG", "BA", "Slow", 60, 560, "local", is_ac=True),
        ODPair(4, 520, "CCG", "BA", "Fast", 45, 565, "local", is_ac=False),
        ODPair(5, 530, "CCG", "BA", "Slow", 60, 590, "local", is_ac=True),
        ODPair(6, 540, "BOR", "DR", "Fast", 30, 570, "local", is_ac=False),
        ODPair(7, 560, "DR", "VR", "Slow", 70, 630, "local", is_ac=True),
        ODPair(8, 600, "CCG", "VR", "Slow", 100, 700, "local", is_ac=False),
        ODPair(9, 530, "VR", "CCG", "Slow", 100, 630, "local", is_ac=True),
        ODPair(10, 530, "AND", "CCG", "Slow", 80, 610, "local", is_ac=False),
        ODPair(11, 530, "BOR", "BA", "Fast", 45, 575, "local", is_ac=True),
        ODPair(12, 550, "VR", "BA", "Fast", 40, 590, "nonlocal", is_ac=True),
    ]
    return sample_od_pairs


# ---------------------------------------------------------------------
# Dash App
# ---------------------------------------------------------------------
app = dash.Dash(__name__)

# initialize pipeline with sample
sample_data = create_sample_data()
correct_traversal_time(sample_data)
augmented_data = augment_od_pairs(sample_data)
linked_data = link_from_bottom(augmented_data)
visualizer = RailwayVisualizer(linked_data)

app.layout = html.Div([
    html.H3("Railway Timetable Visualizer", style={
        "textAlign": "center", "marginBottom": "20px", "fontFamily": "Arial, sans-serif", "fontWeight": "bold"
    }),
    # compact legend
    html.Div([
        html.H4("Legend"),
        html.Div([
            # AC
            html.Div([
                html.Div(style={
                    "width": "24px", "height": "0px",
                    "borderTop": "4px solid #2E86C1",
                    "marginRight": "6px"
                }),
                html.Span("AC")
            ], style={"display":"flex","alignItems":"center","gap":"4px"}),

            # Non-AC
            html.Div([
                html.Div(style={
                    "width": "24px", "height": "0px",
                    "borderTop": "4px solid #E74C3C",
                    "marginRight": "6px"
                }),
                html.Span("Non-AC")
            ], style={"display":"flex","alignItems":"center","gap":"4px"}),

            # Fast
            html.Div([
                html.Div(style={
                    "width": "24px", "height": "0px",
                    "borderTop": "3px solid black",  # solid line
                    "marginRight": "6px"
                }),
                html.Span("Fast")
            ], style={"display":"flex","alignItems":"center","gap":"4px"}),

            # Slow
            html.Div([
                html.Div(style={
                    "width": "24px", "height": "0px",
                    "borderTop": "3px dashed black",  # dashed line
                    "marginRight": "6px"
                }),
                html.Span("Slow")
            ], style={"display":"flex","alignItems":"center","gap":"4px"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap","justifyContent":"center"})
    ], style={"textAlign":"center","marginBottom":"10px"}),

    # upload
    html.Div([
        html.Label("Upload CSV Timetable:", style={"fontWeight": "bold"}),
        dcc.Upload(id="upload-data", children=html.Div(["Drag and Drop or ", html.A("Select Files")]),
                   style={"width":"100%","height":"60px","lineHeight":"60px","borderWidth":"1px","borderStyle":"dashed","borderRadius":"5px","textAlign":"center","margin":"10px 0"},
                   multiple=False)
    ], style={"padding": "0 20px", "marginBottom": "20px"}),

    # controls
        html.Div([
    html.Button("Make AC", id="make-ac-btn", n_clicks=0, 
                style={
                    "padding": "8px 16px",
                    "cursor": "pointer",
                    "background-color": "#5DADE2",  # Lighter blue
                    "color": "white",                # White text
                    "border": "none"                 # No border
                }),
    html.Button("Make Non-AC", id="make-nonac-btn", n_clicks=0, 
                style={
                    "padding": "8px 16px",
                    "cursor": "pointer",
                    "background-color": "#EC7063",  # Lighter red
                    "color": "white",                # White text
                    "border": "none"                 # No border
                }),
    html.Button("Clear Selection", id="clear-selection-btn", n_clicks=0, 
                style={
                    "padding": "8px 16px",
                    "cursor": "pointer",
                    "background-color": "#e7e7e7",   # Default light gray
                    "border": "none"                 # No border
                })
        ], style={
            "display":"flex",
            "justifyContent":"center",
            "gap":"10px",        # space between buttons
            "marginBottom":"12px",
            # "border":"1px solid #ccc",  # optional: visually group
            "padding":"8px",
            "borderRadius":"5px",
            # "backgroundColor":"#f9f9f9"
        }),

    html.Div(id="selection-count", style={"textAlign": "center","fontWeight":"bold","margin":"10px"}),

    dcc.Graph(id="timetable-graph"),
    dcc.Store(id="timetable-data", data=[]),
    dcc.Store(id="selected-services", data=[])
])


# ---------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------
@app.callback(
    Output("timetable-graph", "figure"),
    Input("timetable-data", "data"),
    Input("selected-services", "data"),
)
def update_graph(timetable_data, selected_services):
    if not timetable_data:  # nothing loaded yet
        return go.Figure(
            layout=dict(
                title="Railway Timetable Visualization",
                xaxis_title="Time (Minutes from Midnight)",
                yaxis_title="Stations",
                height=600,
                margin=dict(l=50, r=50, t=60, b=50)
            )
        )
    vis = RailwayVisualizer.from_records(timetable_data)
    return vis.make_figure(selected_services)


@app.callback(
    Output("selected-services", "data"),
    Input("timetable-graph", "clickData"),
    Input("clear-selection-btn", "n_clicks"),
    State("selected-services", "data"),
    prevent_initial_call=True
)
def select_service(click_data, clear_clicks, selected_services):
    ctx = callback_context
    if not ctx.triggered:
        return selected_services

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "clear-selection-btn":
        return []
    elif trigger == "timetable-graph" and click_data:
        point = click_data["points"][0]
        sid = point.get("meta") or point.get("customdata")
        if isinstance(sid, (list, tuple)):
            sid = sid[0] if sid else None
        if sid is None:
            return selected_services

        # sid should be like "S{sr_num}"
        if sid in selected_services:
            selected_services.remove(sid)
        else:
            selected_services.append(sid)

    return selected_services


@app.callback(
    Output("timetable-data", "data"),
    # Input("sample-btn", "n_clicks"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    prevent_initial_call=True
)
def process_data(upload_contents, upload_filename):
    if upload_contents:
        try:
            content_type, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string)
            tmp = 'temp_timetable.csv'
            with open(tmp, 'wb') as f:
                f.write(decoded)

            vis = RailwayVisualizer()
            vis.load_from_csv(tmp)

            os.remove(tmp)
            return vis.to_records()

        except Exception as e:
            print(f"Error processing file: {e}")
            return dash.no_update

    return dash.no_update


@app.callback(
    Output("selection-count", "children"),
    Input("selected-services", "data")
)
def update_selection_count(selected_services):
    return f"Selected services: {len(selected_services)}"

@app.callback(
    Output("timetable-data", "data", allow_duplicate=True),
    Input("make-ac-btn", "n_clicks"),
    Input("make-nonac-btn", "n_clicks"),
    State("selected-services", "data"),
    State("timetable-data", "data"),
    prevent_initial_call=True
)
def flip_ac_status(make_ac_clicks, make_nonac_clicks, selected_services, timetable_data):
    ctx = callback_context
    if not ctx.triggered or not selected_services or not timetable_data:
        return dash.no_update

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    vis = RailwayVisualizer.from_records(timetable_data)

    for od in vis.od_pairs:
        sid = f"S{od.sr_num}"
        if sid in selected_services:
            if trigger == "make-ac-btn":
                od.is_ac = True
            elif trigger == "make-nonac-btn":
                od.is_ac = False

    return vis.to_records()


# ---------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=8051)