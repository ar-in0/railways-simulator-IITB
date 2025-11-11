import timetable as tt
import dash
import pandas as pd
from dash import Dash, html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import io
import base64
import plotly.graph_objs as go
import copy
from datetime import datetime

from enum import Enum

class FilterType(Enum):
    RAKELINK = 'rakelink'
    SERVICE = 'service'

class FilterQuery:
    def __init__(self):
        self.type = None

        # stations
        self.startStation = None
        self.endStation = None

        # passing through this list of stations
        # atleast once
        self.passingThrough = []
        self.inDirection = None # none if rakelink filter, radiobutton value if service filter

        # time
        self.inTimePeriod = None # a time range

        # ac/non ac
        self.ac = None

class Simulator:
    def __init__(self):
        self.app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.parser = None
        self.wttContents = None
        self.summaryContents = None

        # set initial layout
        self.app.layout = self.drawLayout()
        self.initCallbacks()
        self.linkTimingsCreated = False

        self.query = FilterQuery()
    
    def drawLayout(self):
        return html.Div(
            [
                # Hidden store (optional)
                dcc.Store(id="app-state"),

                # === LEFT SIDEBAR ===
                html.Div(
                    [
                        # Title + Subtitle
                        html.Div(
                            [
                                dcc.Markdown(
                                    """
                                    ### Western Railways – Timetable Visualizer
                                    """.replace("  ", ""),
                                    className="title",
                                ),
                                dcc.Markdown(
                                    """
                                    Interactive tool to analyze rake-links during migration to AC.
                                    """.replace("  ", ""),
                                    className="subtitle",
                                ),
                            ]
                        ),

                        html.Hr(),
                        html.Div([
                            dcc.Markdown("##### Upload Required Files", className="subtitle"),
                        ], style={"padding": "8px 0px"}),

                        # Upload components
                        dbc.Row([
                            # Upload Full WTT
                            dbc.Col([
                                dcc.Upload(
                                    id="upload-wtt-inline",
                                    children=html.Div([
                                        html.Img(
                                            src="/assets/excel-icon.png",
                                            style={
                                                "width": "28px",
                                                "height": "28px",
                                                "marginBottom": "6px"
                                            }
                                        ),
                                        html.Div("Full WTT", 
                                                style={"fontWeight": "500", "color": "#334155", "fontSize": "14px"}),
                                        html.Div("Click to upload",
                                                style={"fontSize": "11px", "color": "#94a3b8", "marginTop": "4px"})
                                    ], className="text-center"),
                                    style={
                                        "height": "140px",
                                        "borderWidth": "2px",
                                        "borderStyle": "dashed",
                                        "borderRadius": "12px",
                                        "borderColor": "#cbd5e1",
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center",
                                        "cursor": "pointer",
                                        "transition": "all 0.2s ease",
                                    },
                                    multiple=False
                                )
                            ], xs=12, md=6, className="mb-3 mb-md-0"),

                            # Upload Rake-Link Summary
                            dbc.Col([
                                dcc.Upload(
                                    id="upload-summary-inline",
                                    children=html.Div([
                                        html.Img(
                                            src="/assets/excel-icon.png",
                                            style={
                                                "width": "28px",
                                                "height": "28px",
                                                "marginBottom": "6px"
                                            }
                                        ),
                                        html.Div("Rake-Link Summary", 
                                                style={"fontWeight": "500", "color": "#334155", "fontSize": "14px"}),
                                        html.Div("Click to upload",
                                                style={"fontSize": "11px", "color": "#94a3b8", "marginTop": "4px"})
                                    ], className="text-center"),
                                    style={
                                        "height": "140px",
                                        "borderWidth": "2px",
                                        "borderStyle": "dashed",
                                        "borderRadius": "12px",
                                        "borderColor": "#cbd5e1",
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center",
                                        "cursor": "pointer",
                                        "transition": "all 0.2s ease",
                                    },
                                    multiple=False
                                )
                            ], xs=12, md=6)
                        ], style={"padding": "0px 35px", "marginBottom": "20px"}),

                        html.Hr(),  

                        # Filters
                        html.Div([
                            html.Div(id="filter-overlay", style={"display": "none"}), 
                        html.Div([
                            dcc.Markdown("##### Rake Link Filters", className="subtitle"),
                        ], style={"padding": "0px 0px"}),

                        dbc.Card(
                            [
                                dbc.CardBody([
                                    # Start & End Stations side by side
                                    dbc.Row([
                                        dbc.Col([
                                            html.Label("Start Station", className="criteria-label"),
                                            dcc.Dropdown(
                                                id="start-station",
                                                # options=[{"label": s, "value": s} for s in ["Churchgate", "Bandra", "Borivali", "Virar"]],
                                                options=[],
                                                placeholder="Select Station...",
                                                className="mb-3",
                                                persistence = True,
                                                persistence_type = 'session'
                                            )
                                        ], width=6),

                                        dbc.Col([
                                            html.Label("End Station", className="criteria-label"),

                                            dcc.Dropdown(
                                                id="end-station",
                                                # options=[{"label": s, "value": s} for s in self.parser.wtt.stations],
                                                options=[],
                                                placeholder="Select Station...",
                                                className="mb-3",
                                            )
                                        ], width=6),
                                    ], className="gx-2"),

                                    # Intermediate Stations full width below
                                    html.Label("Passing Through", className="criteria-label"),
                                    dcc.Dropdown(
                                        id="intermediate-stations",
                                        options=[],
                                        multi=True,
                                        placeholder="Add intermediate stations",
                                        className="mb-3",
                                    ),
                                    html.Label("In time period", className="criteria-label"),
                                    dcc.RangeSlider(
                                        id="time-range-slider",
                                        min=0,
                                        max=1440,  # minutes in a full day
                                        step=15,   # 15-min precision
                                        value=[165, 1605],  # default: 2:45 AM to 2:45 AM next day
                                        marks={
                                            i: f"{(i // 60):02d}:{(i % 60):02d}" for i in range(0, 1441, 120)
                                        },
                                        tooltip={"placement": "bottom", "always_visible": False},
                                        allowCross=False,
                                    )
                                ])
                            ],
                            className="criteria-card mb-4",
                            style={"margin": "0px 0px"}  # Add consistent margin
                        ),
                    ], style={"position": "relative"}),

                        # Generate button
                        html.Div(
                            [
                                html.Button(
                                    "Generate Rake Cycles",
                                    id="generate-button",
                                    n_clicks=0,
                                    className="generate-button",
                                    disabled=True,
                                )
                            ],
                            style={"padding": "0px 35px"}  # Match other elements
                        ),
                    ],
                    className="four columns sidebar",
                ),

                # === RIGHT PANEL ===
                html.Div(
                    [
                        html.Div(id="status-div", className="text-box"),
                        dcc.Graph(id="rake-3d-graph", style={"height": "75vh"}),
                    ],
                    className="eight columns",
                    id="page",
                ),
            ],
            className="row flex-display",
            style={"height": "100vh"},
        )

    def initCallbacks(self):
        self._initFileUploadCallbacks()
        self._initButtonCallbacks()
        self._initFilterQueryCallbacks() 
    
    def _initFilterQueryCallbacks(self):
        '''Each UI filter updates self.query attributes directly.'''

        @self.app.callback(
            Input('start-station', 'value'),
        )
        def update_start_station(value):
            self.query.startStation = value
            return None

        @self.app.callback(
            Input('end-station', 'value'),
        )
        def update_end_station(value):
            self.query.endStation = value
            return None

        @self.app.callback(
            Input('intermediate-stations', 'value'),
        )
        def update_intermediate_stations(value):
            self.query.passingThrough = value or []
            return None

        @self.app.callback(
            Input('time-range-slider', 'value'),
        )
        def update_time_period(value):
            self.query.inTimePeriod = value
            return None
        
    def _initFileUploadCallbacks(self):
        """Handle file uploads and update UI"""
        @self.app.callback(
            Output('upload-wtt-inline', 'children'),
            Output('upload-wtt-inline', 'style'),
            Input('upload-wtt-inline', 'contents'),
            State('upload-wtt-inline', 'filename')
        )
        def update_wtt_filename(contents, filename):
            base_style = {
                "height": "140px",
                "borderWidth": "2px",
                "borderStyle": "dashed",
                "borderRadius": "12px",
                "borderColor": "#cbd5e1",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "cursor": "pointer",
                "transition": "all 0.2s ease",
            }

            if contents is None:
                return html.Div([
                    html.Img(src="/assets/excel-icon.png",
                            style={"width": "28px", "height": "28px", "marginBottom": "6px"}),
                    html.Div("Full WTT",
                            style={"fontWeight": "500", "color": "#334155", "fontSize": "14px"}),
                    html.Div("Click to upload",
                            style={"fontSize": "11px", "color": "#94a3b8", "marginTop": "4px"})
                ], className="text-center"), base_style

            # When uploaded
            self.wttContents = contents
            display_name = filename if len(filename) <= 40 else filename[:37] + "..."
            
            success_style = copy.deepcopy(base_style)
            success_style.update({
                "borderStyle": "solid",
                "borderColor": "#188038",  # Google Sheets green
            })
            
            return html.Div([
                html.Img(src="/assets/excel-icon.png",
                        style={"width": "24px", "height": "24px", "marginBottom": "4px"}),
                html.Div(display_name,
                        style={"fontSize": "11px", "color": "#188038", "fontWeight": "500", "wordBreak": "break-all"})
            ], className="text-center"), success_style

        @self.app.callback(
            Output('upload-summary-inline', 'children'),
            Output('upload-summary-inline', 'style'),
            Input('upload-summary-inline', 'contents'),
            State('upload-summary-inline', 'filename')
        )
        def update_summary_filename(contents, filename):
            base_style = {
                "height": "140px",
                "borderWidth": "2px",
                "borderStyle": "dashed",
                "borderRadius": "12px",
                "borderColor": "#cbd5e1",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "cursor": "pointer",
                "transition": "all 0.2s ease",
            }
            if contents is None:
                return html.Div([
                    html.Img(src="/assets/excel-icon.png",
                            style={"width": "28px", "height": "28px", "marginBottom": "6px"}),
                    html.Div("WTT Link Summary",
                            style={"fontWeight": "500", "color": "#334155", "fontSize": "14px"}),
                    html.Div("Click to upload",
                            style={"fontSize": "11px", "color": "#94a3b8", "marginTop": "4px"})
                ], className="text-center"), base_style
            
            self.summaryContents = contents
            # Truncate long filenames
            display_name = filename if len(filename) <= 40 else filename[:37] + "..."
            
            success_style = copy.deepcopy(base_style)
            success_style.update({
                "borderStyle": "solid",
                "borderColor": "#188038",  # Google Sheets green
            })
            
            return html.Div([
                html.Img(src="/assets/excel-icon.png",
                        style={"width": "24px", "height": "24px", "marginBottom": "4px"}),
                html.Div(display_name,
                        style={"fontSize": "11px", "color": "#188038", "fontWeight": "500", "wordBreak": "break-all"})
            ], className="text-center"), success_style

        @self.app.callback(
            Output('generate-button', 'disabled'),
            Output('generate-button', 'style'),
            [Input('upload-wtt-inline', 'contents'),
            Input('upload-summary-inline', 'contents')]
        )
        def enable_generate_button(wtt_contents, summary_contents):
            """Enable button only when both files are uploaded"""
            base_style = {
                "border": "none",
                "width": "100%",
                "height": "42px",
                "borderRadius": "8px",
                # "border": "dashed",
                "fontWeight": "600",
                "fontSize": "14px",
                "cursor": "pointer",
                "transition": "all 0.2s ease",
            }

            if wtt_contents is not None and summary_contents is not None:
                # Both uploaded → enable + green border
                enabled_style = base_style | {
                    # "border": "2px solid #188038",
                    # "backgroundColor": "white",
                    # "color": "#188038",
                    "opacity":"1",
                }
                return False, enabled_style
            else:
                # Default → disabled grayish border
                disabled_style = base_style | {
                    # "border": "2px solid #cbd5e1",
                    # "backgroundColor": "#f1f5f9",
                    "color": "#94a3b8",
                    # "cursor": "not-allowed",
                    "cursor": "not-allowed",
                    "opacity": "0.65",
                }
                return True, disabled_style

        @self.app.callback(
            [Output('start-station', 'disabled'),
            Output('end-station', 'disabled'),
            Output('intermediate-stations', 'disabled'),
            Output('time-range-slider', 'disabled'),
            Output('filter-overlay', 'style')],
            [Input('upload-wtt-inline', 'contents'),
            Input('upload-summary-inline', 'contents')]
        )
        def toggle_filters(wtt_contents, summary_contents):
            """Enable filters only when both files are uploaded"""
            if wtt_contents is not None and summary_contents is not None:
                # Both uploaded -> enable filters
                overlay_style = {"display": "none"}
                return False, False, False, False, overlay_style
            else:
                # Not uploaded -> disable filters
                overlay_style = {
                    "position": "absolute",
                    "top": "0",
                    "left": "0",
                    "right": "0",
                    "bottom": "0",
                    "backgroundColor": "rgba(243, 246, 250, 0.7)",
                    "zIndex": "10",
                    "cursor": "not-allowed",
                    "borderRadius": "12px"
                }
                return True, True, True, True, overlay_style

        @self.app.callback(
            [Output('app-state', 'data'),
            Output('start-station', 'options'),
            Output('end-station', 'options'),
            Output('intermediate-stations', 'options')],
            [Input('upload-wtt-inline', 'contents'),
            Input('upload-summary-inline', 'contents')],
            # prevent_initial_call=True
        )
        def initBackend(wttContents, summaryContents):
            if wttContents is None or summaryContents is None:
                return None,[],[],[]
            
            try:
            # Decode base64
                wttDecoded = base64.b64decode(wttContents.split(',')[1])
                summaryDecoded = base64.b64decode(summaryContents.split(',')[1])
                
                # Create file objects
                wttIO = io.BytesIO(wttDecoded)
                summaryIO = io.BytesIO(summaryDecoded)
                
                # Parse using the fromFileObjects class method
                self.parser = tt.TimeTableParser.fromFileObjects(wttIO, summaryIO)
                stations = [s for s in self.parser.wtt.stations]
                options = [{"label": s, "value": s} for s in stations]

                return {"initialized": True}, options, options, options
            
            except Exception as e:
                print(f"Error initializing backend: {e}")
                return None, [],[],[]

    def _initButtonCallbacks(self):        
        @self.app.callback(
            Output('status-div', 'children'),
            Output('rake-3d-graph', 'figure'),
            Input('generate-button', 'n_clicks'),
            State('upload-wtt-inline', 'contents'),
            State('upload-summary-inline', 'contents'),
            prevent_initial_call=True
        )
        def onGenerateClick(n_clicks, wttContents, summaryContents):
            if n_clicks == 0 or wttContents is None or summaryContents is None:
                return "", go.Figure()
            
            try:
                # Show loading message
                status_msg = html.Div([
                    html.Div("Processing files...", style={"color": "#3b82f6", "fontWeight": "500"}),
                    html.Div("This may take a few moments.", style={"fontSize": "12px", "color": "#64748b", "marginTop": "4px"})
                ])
                
                # # Decode base64
                # wttDecoded = base64.b64decode(wttContents.split(',')[1])
                # summaryDecoded = base64.b64decode(summaryContents.split(',')[1])
                
                # # Create file objects
                # wttIO = io.BytesIO(wttDecoded)
                # summaryIO = io.BytesIO(summaryDecoded)
                
                # # Parse using the fromFileObjects class method
                # self.parser = tt.TimeTableParser.fromFileObjects(wttIO, summaryIO)
                
                # Generate rake cycles
                # pass in the filters object
                qq = self.query
                print("hahahaha")
                print(qq.passingThrough)
                # print(f"len is {len(rakecycles)}")
                if self.linkTimingsCreated:
                    self.applyLinkFilters(qq) # updates the self.render filed of the required rakecyeles
                else:
                    print("first time rc gen")
                    self.parser.wtt.generateRakeCycles()
                    self.applyLinkFilters(qq)
                    self.linkTimingsCreated = True
                    
                # for svc in self.parser.wtt.suburbanServices:
                #     print(f"[{svc.serviceId}]  init:{svc.initStation.name}, final: {svc.finalStation.name}")

                # create 3D plot
                fig = self.visualizeLinks3D()
                
                # Success message
                num_cycles = len(self.parser.wtt.rakecycles)
                num_conflicting = len(self.parser.wtt.conflictingLinks)
                num_rendered = len([rc for rc in self.parser.wtt.rakecycles if getattr(rc, "render", True)])
                
                status = html.Div([
                    html.Div("✓ Success!", style={"color": "#188038", "fontWeight": "600", "fontSize": "16px"}),
                    html.Div(f"Generated {num_cycles} valid rake cycles", 
                            style={"fontSize": "14px", "color": "#334155", "marginTop": "8px"}),
                    html.Div(f"{num_conflicting} conflicting links were excluded", 
                            style={"fontSize": "12px", "color": "#64748b", "marginTop": "4px"}) if num_conflicting > 0 else None,
                    html.Div(f"{num_rendered} rake cycles match the current filter", 
                               style={"fontSize": "13px", "marginTop": "6px"}),
                ])
                
                return status, fig
                
            except Exception as e:
                # Error message with details
                error_msg = html.Div([
                    html.Div("✗ Error", style={"color": "#ef4444", "fontWeight": "600", "fontSize": "16px"}),
                    html.Div(str(e), style={"fontSize": "12px", "color": "#64748b", "marginTop": "8px", "fontFamily": "monospace"})
                ])
                return error_msg, go.Figure()
    
    def applyTerminalStationFilters(self, start, end):
        print(f"Applying filters: start={start}, end={end}")

        for rc in self.parser.wtt.rakecycles:
            rc.render = True  # reset all first
            if not rc.servicePath:
                rc.render = False
                continue

            first = rc.servicePath[0].events[0].atStation
            last = rc.servicePath[-1].events[-1].atStation
            # print(f"is {end} == {last}")

            if start and start.upper() != first:
                rc.render = rc.render and False
            if end and end.upper() != last:
                rc.render = rc.render and False
            else:
                print(f"Match! {rc.linkName}")
    
    def applyPassingThroughFilter(self, qq):
        '''Make rakecycles visible that have events at every station in passingThru within the specified timeperiod'''
        selected = qq.passingThrough
        if not selected:
            # self.applyTimeFilter(qq)
            return
        
        selected = [s.upper() for s in selected]
        t_start, t_end = qq.inTimePeriod if qq.inTimePeriod else (None, None)

        for rc in self.parser.wtt.rakecycles:
            rc.render = rc.render and True
            if not rc.servicePath:
                rc.render = rc.render and False
                continue

            # flatten all events in this rakecycle
            el = []
            for s in rc.servicePath:
                el.extend(s.events)

            # --- Filter by time period, if specified ---
            if qq.inTimePeriod:
                filtered = []
                for e in el:
                    if not e.atTime:
                        continue
                    try:
                        t = datetime.strptime(e.atTime.strip(), "%H:%M:%S")
                    except:
                        try:
                            t = datetime.strptime(e.atTime.strip(), "%H:%M")
                        except:
                            continue

                    minutes = t.hour * 60 + t.minute + t.second / 60
                    if minutes < 165:
                        minutes += 1440

                    if t_start <= minutes <= t_end:
                        filtered.append(e)
                el = filtered  # keep only events inside window

            # --- Check that all required stations are present in el ---
            seen = set()
            for e in el:
                if not e.atStation:
                    continue
                stName = str(e.atStation).strip().upper()
                if stName in selected:
                    seen.add(stName)
                if len(seen) == len(selected):
                    break

            if len(seen) < len(selected):
                rc.render = False

    def applyTimeFilter(self, qq):
        '''old: Only render rakecycles whose every event lies in the interval
           new: Highlight the time interval specified in the filter, thats it.'''
        assert(qq.inTimePeriod)
        for rc in self.parser.wtt.rakecycles:
            rc.render = True  
            if not rc.servicePath:
                rc.render = False
                continue
            
            # Since the events are sorted, check if the earliest
            # event time is >= t_lower and if last event time is <= t_upper.
            # if times are stored as integers then were ok, the comparison will
            # be consistent even for wraparound.
            e_tFirst = rc.servicePath[0].events[0].atTime
            e_tLast = rc.servicePath[-1].events[-1].atTime

            # --- Convert both to minutes since midnight ---
            def to_minutes(time_str):
                try:
                    t = datetime.strptime(time_str.strip(), "%H:%M:%S")
                except:
                    try:
                        t = datetime.strptime(time_str.strip(), "%H:%M")
                    except:
                        return None
                minutes = t.hour * 60 + t.minute + t.second / 60
                if minutes < 165:
                    minutes += 1440
                return minutes

            t_first = to_minutes(e_tFirst)
            t_last = to_minutes(e_tLast)

            t_start, t_end = qq.inTimePeriod if qq.inTimePeriod else (None, None)

            # If any parsing failed, skip this rakecycle
            if t_first is None or t_last is None:
                rc.render = False
                continue

            # Perform the actual comparison
            if not (t_first >= t_start and t_last <= t_end):
                rc.render = False  

    
    def applyLinkFilters(self, qq):
        '''Filter rake cycles based on selected start and end stations.'''

        self.applyTerminalStationFilters(qq.startStation, qq.endStation)
        self.applyPassingThroughFilter(qq)

        visible_count = len([r for r in self.parser.wtt.rakecycles if r.render])
        print(f"Visible rake cycles after filter: {visible_count}")

    def visualizeLinks3D(self):
        rakecycles = [rc for rc in self.parser.wtt.rakecycles if rc.servicePath]
        print(f"We have  len {len(rakecycles)}")
        if not rakecycles:
            raise ValueError("No valid rakecycles found.")

        distanceMap = tt.TimeTableParser.distanceMap
        stationToY = {st.upper(): distanceMap[st.upper()] for st in distanceMap}

        all_traces = []
        z_labels = []
        z_offset = 0

        for rc in rakecycles:
            x, y, z, stationLabels = [], [], [], []

            for svc in rc.servicePath:
                for ev in svc.events:
                    if not ev.atTime or not ev.atStation:
                        continue

                    tStr = ev.atTime.strip()
                    try:
                        t = datetime.strptime(tStr, "%H:%M:%S")
                    except:
                        try:
                            t = datetime.strptime(tStr, "%H:%M")
                        except:
                            continue

                    minutes = t.hour * 60 + t.minute + t.second / 60
                    if minutes < 165:
                        minutes += 1440

                    stName = str(ev.atStation).strip().upper()
                    if stName not in stationToY:
                        print("Skipping unmapped station:", stName)
                        continue

                    x.append(minutes)
                    y.append(stationToY[stName])
                    z.append(z_offset)
                    stationLabels.append(stName)
            
            if rc.rake.isAC:
                color = "rgba(66,133,244,0.8)"   # Google Sheets blue
            else:
                color = "rgba(90,90,90,0.8)"    # Light transparent gray

            if x:
                # visible = getattr(rc, 'render', True)
                # visible = False
                visible = rc.render
                all_traces.append(
                    go.Scatter3d(
                        x=x, y=y, z=z,
                        mode="lines+markers",
                        line=dict(color=color),
                        marker=dict(size=2, color=color),
                        # line=dict(color="#444444"),
                        # marker=dict(size=2, color="#444444"),
                        hovertext=[
                            f"{rc.linkName}: {st} @ {(int(xx)//60) % 24:02d}:{int(xx%60):02d}"
                            for xx, st in zip(x, stationLabels)
                        ],
                        hoverinfo="text",
                        name=rc.linkName,
                        visible=visible,
                    )
                )
                z_labels.append((z_offset, rc.linkName))
                z_offset += 40  # increment z for next rakecycle
        
        x_start  = 165 # 245am
        x_end = 1605 # 245 am next day
        tickPositions = list(range(x_start, x_end + 1, 120))
        tickLabels = [f"{(t // 60) % 24:02d}:{int(t % 60):02d}" for t in tickPositions]

        yTickVals = list(stationToY.values())
        yTickText = list(stationToY.keys())

        fig = go.Figure(data=all_traces)

        fig.update_layout(
            font=dict(size=12, color="#CCCCCC"),
            scene=dict(
                xaxis=dict(
                    showgrid=True,
                    showspikes=False,
                    title="Time of Day →",
                    range=[x_start, x_end],
                    tickvals=tickPositions,
                    ticktext=tickLabels,
                ),
                yaxis=dict(
                    showgrid=True,
                    showspikes=False,
                    title="",
                    tickvals=yTickVals,
                    ticktext=yTickText,
                    range=[min(yTickVals), max(yTickVals)],
                    autorange=False
                ),
                zaxis=dict(
                    showgrid=True,
                    showspikes=False,
                    title="Rake Cycle",
                    tickvals=[zv for zv, _ in z_labels],
                    ticktext=[zl for _, zl in z_labels],
                ),
                # camera=dict(
                #     eye=dict(x=1.6, y=0.01, z=1.4),
                #     up=dict(x=0, y=1, z=0),
                #     center=dict(x=0, y=0, z=0)
                # ),
                camera=dict(
                    eye=dict(x=0, y=0, z=2.5),
                    up=dict(x=0, y=1, z=0),
                    center=dict(x=0, y=0, z=0)
                ),
                aspectmode="manual",
                aspectratio=dict(x=2.8, y=1.2, z=1)
            ),
            scene_camera_projection_type="orthographic",
            width=1300,
            height=800,
            margin=dict(t=5, l=5, b=5, r=5),
        )

        return fig

    def run(self):
        self.app.run(debug=True, port=8051)

if __name__ == "__main__":
    sim = Simulator()
    sim.run()
