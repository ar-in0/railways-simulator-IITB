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

class Simulator:
    def __init__(self):
        self.app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.parser = None
        self.wttContents = None
        self.summaryContents = None

        # set initial layout
        self.app.layout = self.drawLayout()
        self.initCallbacks()
    
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
                        dcc.Markdown("##### Upload Required Files", className="subtitle"),

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
                        ], style={"padding": "0px 35px", "marginBottom": "25px"}),

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
                            className="generate-section",
                            style={
                                "padding": "0px 150px",
                                "textAlign": "left"  
                            }
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
                    html.Div("WTT Summary",
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
            [Input('upload-wtt-inline', 'contents'),
             Input('upload-summary-inline', 'contents')]
        )
        def enable_generate_button(wtt_contents, summary_contents):
            """Enable button only when both files are uploaded"""
            return not (wtt_contents is not None and summary_contents is not None)

    def _initButtonCallbacks(self):        
        @self.app.callback(
            Output('status-div', 'children'),
            Output('rake-3d-graph', 'figure'),
            Input('generate-button', 'n_clicks'),
            [State('upload-wtt-inline', 'contents'),
             State('upload-summary-inline', 'contents')],
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
                
                # Decode base64
                wttDecoded = base64.b64decode(wttContents.split(',')[1])
                summaryDecoded = base64.b64decode(summaryContents.split(',')[1])
                
                # Create file objects
                wttIO = io.BytesIO(wttDecoded)
                summaryIO = io.BytesIO(summaryDecoded)
                
                # Parse using the fromFileObjects class method
                self.parser = tt.TimeTableParser.fromFileObjects(wttIO, summaryIO)
                
                # Generate rake cycles
                self.parser.wtt.generateRakeCycles()

                # create 3D plot
                fig = self.visualizeLinks3D()
                
                # Success message
                num_cycles = len(self.parser.wtt.rakecycles)
                num_conflicting = len(self.parser.wtt.conflictingLinks)
                
                status = html.Div([
                    html.Div("✓ Success!", style={"color": "#188038", "fontWeight": "600", "fontSize": "16px"}),
                    html.Div(f"Generated {num_cycles} valid rake cycles", 
                            style={"fontSize": "14px", "color": "#334155", "marginTop": "8px"}),
                    html.Div(f"{num_conflicting} conflicting links were excluded", 
                            style={"fontSize": "12px", "color": "#64748b", "marginTop": "4px"}) if num_conflicting > 0 else None
                ])
                
                return status, fig
                
            except Exception as e:
                # Error message with details
                error_msg = html.Div([
                    html.Div("✗ Error", style={"color": "#ef4444", "fontWeight": "600", "fontSize": "16px"}),
                    html.Div(str(e), style={"fontSize": "12px", "color": "#64748b", "marginTop": "8px", "fontFamily": "monospace"})
                ])
                return error_msg, go.Figure()

    def visualizeLinks3D(self):
        # pick first valid rake cycle
        rakecycles = [rc for rc in self.parser.wtt.rakecycles if rc.servicePath]
        if not rakecycles:
            raise ValueError("No valid rakecycles found.")
        rc = rakecycles[0]

        # === collect stations in travel order from the WTT master list ===
        # wtt.stations is likely a dict: { 'STATION_CODE': StationObject }
        # so we take its keys (already uppercase codes)
        stations = list(self.parser.wtt.stations.keys())
        stations = [s.strip().upper() for s in stations]
        station_to_y = {st: i for i, st in enumerate(stations)}

        # === prepare data ===
        x, y, z = [], [], []
        for svc in rc.servicePath:
            for ev in svc.events:
                if not ev.atTime or not ev.atStation:
                    continue
                t_str = ev.atTime.strip()
                try:
                    t = datetime.strptime(t_str, "%H:%M:%S")
                except:
                    try:
                        t = datetime.strptime(t_str, "%H:%M")
                    except:
                        continue
                minutes = t.hour * 60 + t.minute + t.second / 60

                st_name = str(ev.atStation).strip().upper()
                if st_name not in station_to_y:
                    print("⚠ Skipping unmapped station:", st_name)
                    continue

                x.append(minutes)
                y.append(station_to_y[st_name])
                z.append(0)

        # === make plot ===
        fig = go.Figure(
            data=[go.Scatter3d(
                x=x, y=y, z=z,
                mode="lines+markers",
                line=dict(color="#2a6fd3", width=4),
                marker=dict(size=4, color="#2a6fd3"),
                hovertext=[f"{stations[yy]} @ {int(xx//60):02d}:{int(xx%60):02d}" for xx, yy in zip(x, y)],
                hoverinfo="text"
            )]
        )

        # === correct reversed time axis and viewing angle ===
        fig.update_layout(
            scene=dict(
                xaxis=dict(
                    title="Time (minutes →)",
                    
                ),
                yaxis=dict(
                    title="Station (distance ↑)",
                    tickvals=list(range(len(stations))),
                    ticktext=stations
                ),
                zaxis=dict(visible=False),
                camera=dict(
                    eye=dict(x=1.8, y=0.01, z=1.2),  # how far you are from the scene
                    up=dict(x=0, y=1, z=0),          # z-axis = "up"
                    center=dict(x=0, y=0, z=0)
                ),
                # aspectmode="manual",
                # aspectratio=dict(x=2, y=3, z=0.2)
            ),
            width=1300,
            height=800,
            margin=dict(l=10, r=10, b=10, t=40),
            # title=f"Rake Cycle {rc.linkName} — Time–Distance Plot"
        )

        return fig

    def run(self):
        self.app.run(debug=True, port=8051)

if __name__ == "__main__":
    sim = Simulator()
    sim.run()
