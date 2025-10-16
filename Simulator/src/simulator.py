# Dash Application to generate an interactive rake-cycle visualization ###
## 0. Import CSV Timetable.
# 
## 1. CSV Timetable is parsed to generate a list of OD Pairs. An OD Pair 
# is an instance of a service with various attributes relevant to operations.
#
## 2. Creation of Rake-Cycles from OD-Pair Data. The time between planned arrival-departure 
# at a station causes gaps in the rake visualization. These need to be corrected to 
# show that every continuous curve in the graph represents a unique rake that performs
# a set of services. (i.e. a rake cycle)
# 
## 3. The corrected OD Pairs are plotted in a graph, indexed by stations on the Y axis
# and time intervals on the X-axis. For each OD-Pair, a dot is marked at the
# (Origin, ArrivalTime) on the graph, and the dots belonging to a single rake are
# identified and joined by a line.
# ---
# Core functionalities and Usability
# This application facilitates: Visualizing effect of swapping non-AC rakes
# with AC rakes. All functionality should be towards this goal. 
# The independent variable in our analysis is **whether a rake is AC or non-AC**. 
# a. Graph Interactions
# ------------------
# - Rake-Cycle Selection: The user must have the ability to isolate (select) a service
# or entire rake-cycles by clicking on line segments.
#
# - AC/Non-AC Toggle: Changing AC/Non-AC status of selected rakes/services and visualizing the effect
# on the graph. The AC/NonAC status should feed into other planned analyses
# such as station and service crowd simulation.
#
# - Selected Services Details: The user should be able to view the details of
# selected rakes/services. 
#
# - Station Crowd Visualization: Bhavani's simulator run ends with an assignment
# of passenger counts at each station at every time interval. This needs to be 
# visualized with the rake cycles providing background context. Perhaps bubbles?
#
# - Arbitrary region selection: Isolate a cross-section of rake cycles and 
# summarize OD-Pair information.
#
# - Exporting: Modified timetables, summaries should be export-able 
import pandas as pd
import dash
from dash import Dash, html, dcc, Input, Output, State, callback_context
import io
import base64
import plotly.graph_objs as go
import copy

# CCG->DR (13 mins from CCG to dadar)
# CCG->DR->BA (18mins from CCG to Bandra )
# ..etc
# Q1. Are there multiple routes to a particular station?
# A. No. Each "line" (harbour, western etc.) has unique route to each station.
# Currently we are working with a single line. (western)
TRAVERSAL_TIME_ARR = [0, 13, 18, 27, 42, 72] 
STATION_MAP = {"CCG": 0, "DR": 1, "BA": 2, "AND": 3, "BOR": 4, "VR": 5}
STATION_ORDER = ["CCG", "DR", "BA", "AND", "BOR", "VR"]

import timetable

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

class RailwayVisualizer(): 
    def __init__(self):
        self.od_pairs = None
        self.station_positions = STATION_MAP

        self.colors = {
            "AC": "#2E86C1",        # Blue
            "NONAC": "#E74C3C",     # Red
            "SELECTED": "rgba(46, 134, 193, 0.3)"
        }

    def get_rake_cycle(self, sr_num):
        """Return all sr_nums in the same rake cycle as sr_num"""
        srnum_to_od = {od.sr_num: od for od in self.od_pairs}
        cycle = set()
        
        # go backwards
        current = srnum_to_od[sr_num]
        while current.linkedToBefore is not None:
            current = srnum_to_od[current.linkedToBefore]
        
        # now traverse forward
        while current:
            cycle.add(f"S{current.sr_num}")
            if current.linkedToAfter is not None:
                current = srnum_to_od[current.linkedToAfter]
            else:
                break
        print(list(cycle))
        return list(cycle)

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
    
    def make_figure(self, selected_services=None, selected_region=None):
        selected_services = selected_services or []
        # print(selected_services)
        fig = go.Figure()
        
        if not self.od_pairs:
            return fig
        
        for od in self.od_pairs:
            # service id consistent with selection strings used elsewhere
            service_id = f"S{od.sr_num}"

            # station y positions
            origin_y = self.station_positions.get(od.originating_stn, 0)
            dest_y = self.station_positions.get(od.destin_stn, 0)

            # color & style
            color = self.colors["AC"] if od.is_ac else self.colors["NONAC"]
            line_style = "solid" if str(od.fast_or_slow).strip().lower() == "fast" else "dash"
            line_width = 3 if od.is_ac else 2
            marker_symbol = "circle" if od.is_ac else "square"

            x_points, y_points = self.interpolate_points(
                od.originating_at_time, origin_y, 
                od.destination_time, dest_y, 
                num_points=20  # Increase this for even better coverage
            )
            # print(x_points)

            # Main visible trace with interpolated points
            fig.add_trace(go.Scattergl(
                x=x_points,
                y=y_points,
                mode="lines+markers",
                line=dict(color=color, width=line_width, dash=line_style),
                marker=dict(
                    size=[8 if i in [0, len(x_points)-1] else 1 for i in range(len(x_points))],  # Larger markers at endpoints
                    symbol=marker_symbol, 
                    color=color,
                    opacity=[1.0 if i in [0, len(x_points)-1] else 0.1 for i in range(len(x_points))]  # Semi-transparent intermediate points
                ),
                name=service_id,
                customdata=[service_id] * len(x_points),
                meta=service_id,
                # hovertemplate=hovertemplate,
                showlegend=False,
                connectgaps=True
            ))

            # Optional: Add a thicker invisible overlay for even easier clicking
            # This creates a wider "hit area" around the line
            fig.add_trace(go.Scattergl(
                x=[od.originating_at_time, od.destination_time],
                y=[origin_y, dest_y],
                mode="lines",
                line=dict(color="rgba(0,0,0,0.001)", width=20),  # Very transparent, wide line
                hoverinfo="skip",  # Don't show hover for this overlay
                customdata=[service_id, service_id],
                meta=service_id,
                showlegend=False
            ))

            # Highlight selected services
            if service_id in selected_services:
                fig.add_trace(go.Scattergl(
                    x=[od.originating_at_time, od.destination_time],
                    y=[origin_y, dest_y],
                    mode="lines",
                    line=dict(color=self.colors["SELECTED"], width=12),
                    hoverinfo="skip",
                    showlegend=False,
                    customdata=[service_id, service_id],
                    meta=service_id
                ))

        fig.update_layout(
            xaxis_title="Time (Minutes from Midnight)",
            yaxis=dict(
                tickmode="array",
                tickvals=list(self.station_positions.values()),
                ticktext=list(self.station_positions.keys())
            ),
            clickmode="event+select",
            dragmode="select",  # Enable box/lasso select
            selectdirection="any",  # Allow any direction selection
            hovermode="closest",
            height=600,
            margin=dict(l=50, r=50, t=60, b=50),
            showlegend=False
        )
        
        return fig

    def makeODPairs(self, df):
        """Load OD pairs from a pandas DataFrame, skipping dummy rows"""
        od_pairs = []
        # row_idx, row_data
        # row[0] is str
        for _, row in df.iterrows():
            if pd.isna(row[0]) or not row[0].isdigit():
                continue  # skip blank/dummy rows

            # Check if AC status provided (example col index 9 or col name)
            is_ac = False
            if len(row) > 9:
                val = str(row[9]).strip().lower()
                if val in ['true', 'ac', '1', 'yes']:
                    is_ac = True
            
            # values in the timetable csv are the desired
            # characteristics of the service.
            # Ideally TimeTable should have rake-id info too
            # A Rake-id-Service linkage would be useful.
            # A Rake Class as an attribute of a Service()
            # {1: Service()}
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

    def loadFromDF(self, df: pd.DataFrame):
        ods = self.makeODPairs(df)
        self.makeRakeCycles(ods)

    def makeRakeCycles(self, ods):
        # Q. Why correct traversal time?
        # A: 
        self.correct_traversal_time(ods)
        od_pairs_augmented = self.augment_od_pairs(ods)
        for x in od_pairs_augmented:
            print(x)
        od_pairs_linked = self.link_from_bottom(od_pairs_augmented)
        self.od_pairs = od_pairs_linked

    def correct_traversal_time(self, od_pairs):
        """Correct traversal times based on station positions"""
        for od in od_pairs:
            if od.service_type == "nonlocal":
                continue
            od.traversal_time = abs(TRAVERSAL_TIME_ARR[STATION_MAP[od.destin_stn]] -
                                TRAVERSAL_TIME_ARR[STATION_MAP[od.originating_stn]])
            od.destination_time = od.originating_at_time + od.traversal_time

    # Rake-Cycle Invariants:
    # 1. Rake Cycle must always end at CCG, even if a return service is not listed in the timetable.
    # 2. Rake Cycle must always start from CCG, even if a starting is 
    def augment_od_pairs(self, od_pairs):
        """Augment OD pairs to create complete rake cycles"""
        od_pairs_new = od_pairs.copy()
        max_sr = max(od.sr_num for od in od_pairs_new)  # FIX: Track max sr_num manually

        for od in od_pairs:
            if od.service_type == "nonlocal":
                continue

            direction = 1 if STATION_MAP[od.destin_stn] > STATION_MAP[od.originating_stn] else -1

            if direction == 1:
                if od.originating_stn == "CCG" and od.destin_stn != "VR":
                    max_sr += 1
                    od_pair = ODPair(
                        sr_num=max_sr,
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

                    max_sr += 1
                    od_pair2 = ODPair(
                        sr_num=max_sr,
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
                    max_sr += 1
                    od_pair = ODPair(
                        sr_num=max_sr,
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

                    max_sr += 1
                    od_pair2 = ODPair(
                        sr_num=max_sr,
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
                    max_sr += 1
                    od_pair_before = ODPair(
                        sr_num=max_sr,
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

                    max_sr += 1
                    od_pair_after = ODPair(
                        sr_num=max_sr,
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

                    max_sr += 1
                    od_pair_return = ODPair(
                        sr_num=max_sr,
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
                    max_sr += 1
                    od_pair = ODPair(
                        sr_num=max_sr,
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

            # direction == -1 not handled
        return od_pairs_new


    def change_time(self, od_pairs_linked, arr_idx, dep_idx):
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

    def link_from_bottom(self, od_pairs_new):
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

                    self.change_time(od_pairs_linked, arr_idx, dep_idx)
                    departures[j] = -1
                    arrivals[i] = -1
                    break

        return od_pairs_linked
    
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
        instance = cls()
        instance.od_pairs = [
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
        return instance


class Simulator:
    def __init__(self):
        self.app = Dash()
        self.visualizer = RailwayVisualizer()
        self.drawLayout()
        self.initCallbacks()

    def initCallbacks(self):
        self._initLayoutCallbacks()
        self._initButtonCallbacks()
        self._initGraphCallbacks()
    
    def _initLayoutCallbacks(self):
        @self.app.callback(
        Output("controls-container", "style"),
        Input("timetable-csv", "data")
        )
        def toggle_controls(timetable_csv):
            if timetable_csv:
                # show controls when CSV uploaded
                return {"display": "block"}
            # hide otherwise
            return {"display": "none"}
        
        @self.app.callback(
            Output("graph-container", "style"),
            Input("timetable-csv", "data")
        )
        def toggle_graph_visibility(timetable_csv):
            if timetable_csv:
                return {"visibility": "visible", "height": "600px"}
            return {"visibility": "hidden", "height": "600px"}

    def _initButtonCallbacks(self):
        @self.app.callback(
            Output("timetable-csv", "data"),
            Input("upload-TT-button", "contents"),
            State("upload-TT-button", "filename"),
            prevent_initial_call=True
        )
        def parse_csv(contents, filename):
            if contents is not None:
                try:
                    _, csv_string = contents.split(',')
                    decoded = base64.b64decode(csv_string)
                    df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
                    self.visualizer.loadFromDF(df)  
                    return self.visualizer.to_records()
                except Exception as e:
                    print(f"Error processing file: {e}")
                    return []
            return []

    def _initGraphCallbacks(self):
        # Callback to show/hide the main content based on CSV upload
        @self.app.callback(
            Output("main-content", "children"),
            Input("timetable-csv", "data"),
        )
        def update_main_content(timetable_csv):
            if not timetable_csv:
                return html.Div([])
                #     html.P("Please upload a CSV file to begin visualization.", 
                #            style={"textAlign": "center", "color": "#666", "marginTop": "50px"})
                # ])
            
            # Return all the components when data is loaded
            return html.Div([
                self.drawSelectedCount(),
                self.drawLegend(),
                # self.drawGraph(),
                # self.drawGInteractionButtons(),
                html.Div([
                    dcc.Checklist(
                        id="rake-cycle-toggle",
                        options=[{"label": " Select entire rake cycles", "value": "enabled"}],
                        value=[],
                        style={"display": "inline-block"}
                    )
                ], style={"textAlign": "center"})
            ])

        @self.app.callback(
            Output("rake-cycle-graph", "figure"),
            Input("timetable-csv", "data"),
            Input("selected-services", "data"),
            prevent_initial_call=True
        )
        def update_graph(timetable_csv, selected_services=None):
            if not timetable_csv:  # nothing loaded yet
                return go.Figure(
                    layout=dict(
                    # title="Railway Timetable Visualization - Click and drag to select region",
                        xaxis_title="Time (Minutes from Midnight)",
                        yaxis_title="Stations",
                        height=600,
                        margin=dict(l=50, r=50, t=60, b=50),
                        dragmode="select",
                        selectdirection="any"
                    )
                )
            vis = RailwayVisualizer.from_records(timetable_csv)
            return vis.make_figure(selected_services, None)
        
        @self.app.callback(
            Output("selected-services", "data"),
            Input("rake-cycle-graph", "clickData"),
            Input("clear-selection-button", "n_clicks"),
            State("selected-services", "data"),
            State("rake-cycle-toggle", "value"),
            State("timetable-csv", "data"),
            prevent_initial_call=True
        )
        def select_service(click_data, clear_clicks, selected_services, rake_cycle_toggle, timetable_data):
            ctx = callback_context
            if not ctx.triggered:
                return selected_services or []

            prop = ctx.triggered[0]["prop_id"]

            # Clear button pressed
            if prop.startswith("clear-selection-button"):
                return []

            # Only handle actual click events
            if prop.endswith("clickData") and click_data:
                pts = click_data.get("points")
                if not pts:
                    return selected_services or []

                point = pts[0]
                sid = point.get("meta") or point.get("customdata")
                # normalize if customdata/meta is list-like
                if isinstance(sid, (list, tuple)):
                    sid = sid[0] if sid else None
                if sid is None or not sid.startswith("S"):
                    return selected_services or []

                # Extract sr_num from service ID
                sr_num = int(sid[1:])
                selected_services = selected_services or []
                
                if "enabled" in rake_cycle_toggle and timetable_data:
                    odPairs = self.visualizer.od_pairs
                    rakeCycle = self.isolateRakeCycle(sr_num)
                    print(rakeCycle)
                else:
                    # Individual service selection
                    if sid in selected_services:
                        selected_services.remove(sid)
                    else:
                        selected_services.append(sid)

                return selected_services
        
        return dash.no_update

    def isolateRakeCycle(self, sr_num):
        """Get all services in the same rake cycle as the given service"""
        # Can one service belong to multiple rake-cycles?
        # - Can one rake perform the same service?
        # - A service is an OD-Pair. A-B cannot occur more than 
        # once unless x-A occurs. i.e. indegree of a node must be >= 1 
        od_map = {od.sr_num: od for od in self.visualizer.od_pairs}
        if sr_num not in od_map:
            return []

        start_od = od_map[sr_num]
        cycle_services = [sr_num]
        
        # Follow links backward
        current = start_od
        print(current)
        while current.linkedToBefore is not None:
            prev_sr_num = current.linkedToBefore
            if prev_sr_num in od_map:
                cycle_services.insert(0, prev_sr_num)
                current = od_map[prev_sr_num]
            else:
                break
        
        # Follow links forward
        current = start_od
        while current.linkedToAfter is not None:
            next_sr_num = current.linkedToAfter
            if next_sr_num in od_map:
                cycle_services.append(next_sr_num)
                current = od_map[next_sr_num]
            else:
                break
        
        return cycle_services

    def drawLegend(self):
        return html.Div([     
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
    ], style={"textAlign":"center","marginBottom":"10px"})

    def drawUploadButton(self):
        return html.Div([
        dcc.Upload(
            id="upload-TT-button", 
            children=html.Div(["Upload CSV Timetable"]),
            style={
                "width":"100%",
                "height":"60px",
                "lineHeight":"60px",
                "borderWidth":"1px",
                "borderStyle":"dashed",
                "borderRadius":"5px",
                "textAlign":"center",
                "margin":"10px 0"
            },
            multiple=False
        )
    ], style={"padding": "0 20px", "marginBottom": "20px"})

    def drawGInteractionButtons(self):
        return html.Div([
        html.Button("Make AC", id="make-ac-button", n_clicks=0, 
                    style={
                        "padding": "8px 16px",
                        "cursor": "pointer",
                        "background-color": "#5DADE2",
                        "color": "white",
                        "border": "none"
                    }),
        html.Button("Make Non-AC", id="make-nonac-button", n_clicks=0, 
                    style={
                        "padding": "8px 16px",
                        "cursor": "pointer",
                        "background-color": "#EC7063",
                        "color": "white",
                        "border": "none"
                    }),
        html.Button("Clear Selection", id="clear-selection-button", n_clicks=0, 
                    style={
                        "padding": "8px 16px",
                        "cursor": "pointer",
                        "background-color": "#e7e7e7",
                        "border": "none"
                    }),
        html.Button("View Selected Services", id="view-services-button", n_clicks=0, 
                    style={
                        "padding": "8px 16px",
                        "cursor": "pointer",
                        "background-color": "#17a2b8",
                        "color": "white",
                        "border": "none"
                    })
    ], style={
        "display":"flex",
        "justifyContent":"center",
        "gap":"10px",
        "marginBottom":"12px",
        "padding":"8px",
        "borderRadius":"5px",
    })

    def drawSelectedCount(self):
        return html.Div(
            id="selection-count", 
            style={
                "textAlign": "center",
                "fontFamily": "Arial, sans-serif", 
                "fontWeight":"bold",
                "margin":"10px"
            }
        )

    def drawGraph(self):
        return html.Div(dcc.Graph(id="rake-cycle-graph"), id="graph-container", style={"visibility": "hidden", "height": "600px"})

    def drawServicesDetails(self):
        return html.Div(id="selected-services-details", style={
        "margin": "20px", 
        "padding": "15px", 
        "backgroundColor": "#fff", 
        "borderRadius": "8px",
        "border": "1px solid #dee2e6",
        "display": "none"  # Initially hidden
    })

    def drawLayout(self):
        self.app.layout = html.Div([
            html.H3("Rake Cycle Visualizer", style={
                "textAlign": "center", 
                "marginBottom": "20px", 
                "fontFamily": "Arial, sans-serif", 
                "fontWeight": "bold"
            }),
            self.drawUploadButton(),
            self.drawServicesDetails(),
            
            # Store for timetable data
            dcc.Store(id="timetable-csv", data=[]),
            dcc.Store(id="selected-services", data=[]),
            dcc.Store(id="show-services-details", data=False),

            html.Div(
                id="controls-container",
                children=self.drawGInteractionButtons(),
                style={"display": "none"}  # hide initially
            ),
            
            # Main content area that will be populated after CSV upload
            html.Div(id="main-content"),
            self.drawGraph()
        ])

    def run(self):
        self.app.run(debug=True, port=8051)

if __name__ == "__main__":
    sim = Simulator()
    sim.run()