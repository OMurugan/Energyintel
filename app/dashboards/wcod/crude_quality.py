from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, callback_context
from app import create_dash_app
import os
import numpy as np

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'CrossPlot.csv')

# ===================================
# LOAD CSV
# ===================================
def load_crossplot_data():

    df = pd.read_csv(
        CSV_PATH,
        encoding="utf-16",
        sep="\t",
        header=None,
        engine="python"
    )

    df = df.dropna(how="all")
    df = df[~df.astype(str).apply(lambda x: x.str.contains("COPYRIGHT", na=False)).any(axis=1)]

    df = df.iloc[3:].reset_index(drop=True)
    df.columns = ["Region", "Crude", "Property", "Value"]

    df = df.pivot_table(
        index=["Region", "Crude"],
        columns="Property",
        values="Value",
        aggfunc="first"
    ).reset_index()

    df = df.rename(columns={
        "Avg. X Property Value": "Gravity-API at 60°F",
        "Avg. Y Property Value": "Sulfur Content %",
        "Avg. Bubble Size": "BubbleSize"
    })

    df["Gravity-API at 60°F"] = pd.to_numeric(df["Gravity-API at 60°F"], errors="coerce")
    df["Sulfur Content %"] = pd.to_numeric(df["Sulfur Content %"], errors="coerce")
    df["BubbleSize"] = pd.to_numeric(df["BubbleSize"], errors="coerce").fillna(40)

    df = df.dropna(subset=["Gravity-API at 60°F", "Sulfur Content %"])

    return df


# ===================================
# LAYOUT
# ===================================
def create_layout(dash_app=None):

    df = load_crossplot_data()

    return html.Div([

        # --------------------------------------------------
        # ROW OF DROPDOWNS
        # --------------------------------------------------
        html.Div([
            html.Div([
                html.Label("Select X Axis Property",
                    style={'color': '#FF6600', 'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id="x-axis-dropdown",
                    options=[{"label": "Gravity-API at 60 F", "value": "Gravity-API at 60°F"}],
                    value="Gravity-API at 60°F",
                    clearable=False,
                ),
                html.Label("X Axis Range",
                    style={'color': '#6E6E6E', 'fontWeight': 'normal', 'marginBottom': '5px'}),
                dcc.RangeSlider(
                    id="x-range-slider",
                    min=df["Gravity-API at 60°F"].min(),
                    max=df["Gravity-API at 60°F"].max(),
                    step=0.1,
                    value=[10.7, 68.6],
                    tooltip={"placement": "top", "always_visible": True},
                    marks=None,
                ),
            ], style={'width': '32%', 'display': 'inline-block'}),

            html.Div([
                html.Label("Select Y Axis Property",
                    style={'color': '#FF6600', 'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id="y-axis-dropdown",
                    options=[{"label": "Sulfur Content-% Wt", "value": "Sulfur Content %"}],
                    value="Sulfur Content %",
                    clearable=False,
                ),
                html.Label("Y Axis Range",
                    style={'color': '#6E6E6E', 'fontWeight': 'normal', 'marginBottom': '5px'}),
                dcc.RangeSlider(
                    id="y-range-slider",
                    min=df["Sulfur Content %"].min(),
                    max=df["Sulfur Content %"].max(),
                    step=0.01,
                    value=[0.00, 5.98],
                    tooltip={"placement": "top", "always_visible": True},
                    marks=None,
                ),
            ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '2%'}),

            html.Div([
                html.Label("Select Bubble Size Property",
                    style={'color': '#FF6600', 'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id="bubble-size-dropdown",
                    options=[{"label": "Volume-000 b/d", "value": "BubbleSize"}],
                    value="BubbleSize",
                    clearable=False,
                ),
                html.Label("Bubble Size Range",
                    style={'color': '#6E6E6E', 'fontWeight': 'normal', 'marginBottom': '5px'}),
                dcc.RangeSlider(
                    id="bubble-range-slider",
                    min=0,
                    max=int(df["BubbleSize"].max()),
                    step=1,
                    value=[0, int(df["BubbleSize"].max())],
                    tooltip={"placement": "top", "always_visible": True},
                    marks=None,
                ),
            ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '2%'}),

        ]),

        html.Br(),

        # --------------------------------------------------
        # MAIN CONTENT (CHART + RIGHT SIDEBAR)
        # --------------------------------------------------
        html.Div([

            # Chart
            html.Div([
                dcc.Graph(
                    id='crude-quality-chart',
                    config={
                        'displayModeBar': False,
                        'displaylogo': False,
                        'modeBarButtonsToRemove': [
                            'pan2d', 'zoom2d', 'select2d', 'lasso2d',
                            'autoScale2d', 'resetScale2d',
                            'hoverClosestCartesian', 'hoverCompareCartesian',
                            'zoomIn2d', 'zoomOut2d'
                        ]
                    }
                )
            ], style={'width': '80%', 'display': 'inline-block', 'verticalAlign': 'top'}),

            # Right Sidebar
            html.Div([

                # Key
                html.Div([
                    html.Div("Key",
                        style={'fontWeight': 'bold', 'marginBottom': '8px',
                               'fontSize': '14px', 'color': '#1a1a1a'}),
                    html.Div([
                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#313B49','marginRight': '8px'
                            }),
                            "Null"
                        ], style={'fontSize': '8pt'}),

                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#0075A8','marginRight': '8px'
                            }),
                            "FSU"
                        ], style={'fontSize': '8pt'}),

                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#595959','marginRight': '8px'
                            }),
                            "OECD"
                        ], style={'fontSize': '8pt'}),

                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#7986CB','marginRight': '8px'
                            }),
                            "OPEC"
                        ], style={'fontSize': '8pt'}),

                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#FE5000','marginRight': '8px'
                            }),
                            "Others"
                        ], style={'fontSize': '9pt'}),

                    ])
                ], style={'marginBottom': '15px'}),

                # CrudeOil Filter
                html.Div([
                    html.Div("CrudeOil",
                        style={'fontWeight': 'bold', 'marginBottom': '7px',
                               'fontSize': '14px', 'color': '#1a1a1a'}),
                    dcc.Checklist(
                        id='crude-filter-checklist-all',
                        options=[{'label': '(All)', 'value': 'all'}],
                        value=['all'],
                        style={'fontSize': '12px'}
                    ),
                    html.Div([
                        dcc.Checklist(
                            id='crude-filter-checklist-items',
                            options=[],
                            value=[],
                            style={'fontSize': '12px'}
                        )
                    ], style={'maxHeight': '400px', 'overflowY': 'auto', 'marginTop': '10px'})
                ])

            ], style={
                'width': '18%',
                'display': 'inline-block',
                'verticalAlign': 'top',
                'paddingTop': '40px',
                'marginLeft': '2%'
            })

        ])

    ])


# ===================================
# DASH APP CREATION
# ===================================
def create_crude_quality_dashboard(server, url_base_pathname="/dash/crude-quality/"):

    current_dir = Path(__file__).parent
    assets_dir = current_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    dash_app = create_dash_app(server, url_base_pathname)

    dash_app.assets_folder = str(assets_dir)

    # --------------------------------------------------------
    # INLINE CSS INJECTION — SLIDER + TOOLTIP + HANDLE
    # --------------------------------------------------------
    css_injected = """
        <style>
        .rc-slider-handle {
            width: 10px !important;
            height: 14px !important;

            background-color: #FFFFFF !important;
            border: 2px solid #6E6E6E !important;

            margin-top: -6px !important;
            box-shadow: none !important;
            cursor: pointer !important;
        }

        .rc-slider-handle-1 {
            border-radius: 7px 0 0 7px !important;
        }
        .rc-slider-handle-2 {
            border-radius: 0 7px 7px 0 !important;
        }

        /* Hover */
        .rc-slider-handle:hover {
            border-color: #4D4D4D !important;
        }

        /* Active press */
        .rc-slider-handle:active {
            border-color: #3A3A3A !important;
        }

        .rc-slider-track,
        .rc-slider-track-1,
        .rc-slider-track-2,
        div[class*="rc-slider-track"] {
            background: #6E6E6E !important;
            height: 4px !important;
        }

        .rc-slider-rail {
            background: #D3D3D3 !important;
            height: 4px !important;
        }

        /* Tooltip */
        .rc-slider-tooltip-inner {
            background: #ffffff !important;
            color: black !important;
            border: 1px solid #999 !important;
        }

        </style>
        """

    # Inject CSS into index_string
    dash_app.index_string = f"""
    <!DOCTYPE html>
    <html>
        <head>
            {{%metas%}}
            <title>Crude Quality Dashboard</title>
            {{%favicon%}}
            {{%css%}}
            {css_injected}
        </head>
        <body>
            {{%app_entry%}}
            <footer>
                {{%config%}}
                {{%scripts%}}
                {{%renderer%}}
            </footer>
        </body>
    </html>
    """

    # Layout + callbacks
    dash_app.layout = create_layout(dash_app)
    register_callbacks(dash_app)

    return dash_app


# ===================================
# CALLBACKS
# ===================================
def register_callbacks(dash_app, server=None):

    @dash_app.callback(
        [
            Output('crude-filter-checklist-items', 'options'),
            Output('crude-filter-checklist-items', 'value'),
            Output('crude-filter-checklist-all', 'value')
        ],
        [
            Input('crude-filter-checklist-all', 'value'),
            Input('crude-filter-checklist-items', 'value')
        ],
        prevent_initial_call=False
    )
    def update_crude_filter_list(all_selected, current_selected):

        df = load_crossplot_data()
        crude_list = sorted(df["Crude"].unique().tolist())

        options = [{'label': crude, 'value': crude} for crude in crude_list]

        ctx = callback_context
        trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

        if trigger == 'crude-filter-checklist-all':
            if all_selected and 'all' in all_selected:
                return options, crude_list, ['all']
            return options, [], []

        if trigger == 'crude-filter-checklist-items':
            if not current_selected:
                return options, [], []
            if len(current_selected) == len(crude_list):
                return options, current_selected, ['all']
            return options, current_selected, []

        return options, crude_list, ['all']


    @dash_app.callback(
        Output('crude-quality-chart', 'figure'),
        [
            Input("x-axis-dropdown", "value"),
            Input("y-axis-dropdown", "value"),
            Input("bubble-size-dropdown", "value"),
            Input("x-range-slider", "value"),
            Input("y-range-slider", "value"),
            Input("bubble-range-slider", "value"),
            Input('crude-filter-checklist-items', 'value'),
        ]
    )
    def update_crude_quality(x_col, y_col, size_col, x_range, y_range, size_range, selected_crudes):

        df = load_crossplot_data()
        df[size_col] = pd.to_numeric(df[size_col], errors="coerce").fillna(40)

        df = df[
            (df[x_col] >= x_range[0]) & (df[x_col] <= x_range[1]) &
            (df[y_col] >= y_range[0]) & (df[y_col] <= y_range[1]) &
            (df[size_col] >= size_range[0]) & (df[size_col] <= size_range[1])
        ]

        if not selected_crudes:
            fig = go.Figure()
            fig.update_layout(
                title=dict(text="Crude Oils Compared by Quality", x=0.5, font=dict(color="#FF6600", size=20)),
                xaxis=dict(title=x_col, range=[10, 65], dtick=5, showgrid=False),
                yaxis=dict(title=y_col, range=[0, 4.5], dtick=0.5, showgrid=False),
                height=500, plot_bgcolor="white"
            )
            return fig

        df = df[df["Crude"].isin(selected_crudes)]

        color_map = {
            'Null': '#313B49',
            'FSU': '#0075A8',
            'OECD': '#595959',
            'OPEC': '#7986CB',
            'Others': '#FE5000'
        }

        fig = go.Figure()

        for region in df["Region"].unique():
            grp = df[df["Region"] == region]
            custom = grp[size_col].apply(lambda x: f"{x:,.0f}")
            fig.add_trace(go.Scatter(
                x=grp[x_col], y=grp[y_col],
                mode="markers",
                text=grp["Crude"],
                customdata=custom,
                marker=dict(
                    size=np.sqrt(grp[size_col]) * 0.8,
                    color=color_map.get(region, "#444"),
                    opacity=0.8,
                    line=dict(width=1, color="white")
                ),
                hovertemplate="<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#787878;font-weight:normal;font-style:normal;text-decoration:none;\">Crude:</span> <span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#000000;font-weight:bold;font-style:normal;text-decoration:none;\">%{text}</span><br>"
                              "<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#787878;font-weight:normal;font-style:normal;text-decoration:none;\">Gravity:</span> <span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#000000;font-weight:bold;font-style:normal;text-decoration:none;\">%{x:.1f}</span><br>"
                              "<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#787878;font-weight:normal;font-style:normal;text-decoration:none;\">Sulfur:</span> <span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#000000;font-weight:bold;font-style:normal;text-decoration:none;\">%{y:.2f}</span><br>"
                              "<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#787878;font-weight:normal;font-style:normal;text-decoration:none;\">Volume:</span> <span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#000000;font-weight:bold;font-style:normal;text-decoration:none;\">%{customdata}</span><extra></extra>"
            ))

        fig.update_layout(
            title=dict(text="Crude Oils Compared by Quality", x=0.5, font=dict(color="#FF6600", size=20)),
            xaxis=dict(title=x_col, range=[10, 65], dtick=5, showgrid=False, showline=True, linecolor="black", mirror=True),
            yaxis=dict(title=y_col, range=[0, 4.5], dtick=0.5, showgrid=False, showline=True, linecolor="black", mirror=True),
            height=500, plot_bgcolor="white", paper_bgcolor="white",
            showlegend=False,
            margin=dict(l=60, r=10, t=50, b=50),
            hoverlabel=dict(
                bgcolor="#cbcbcb",
                font_size=13,
                font_family="Tahoma, arial, sans-serif"
            )
        )

        return fig
