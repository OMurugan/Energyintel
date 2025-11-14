from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
from app import create_dash_app
import os
import numpy as np

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'CrossPlot.csv')


# ===================================
#  LOAD CSV (UTF-16 + TAB + PIVOT)
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
#  LAYOUT WITH DROPDOWNS + RANGE SLIDERS
# ===================================
def create_layout(dash_app=None):

    df = load_crossplot_data()

    return html.Div([
        # -------------------------
        # ROW OF DROPDOWNS
        # -------------------------
        html.Div([
            html.Div([
                html.Label("Select X Axis Property", style={'color': '#FF6600', 'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id="x-axis-dropdown",
                    options=[
                        {"label": "Gravity-API at 60 F", "value": "Gravity-API at 60°F"}
                    ],
                    value="Gravity-API at 60°F",
                    clearable=False
                ),
                html.Label("X Axis Range", style={'color': '#1a1a1a', 'fontWeight': 'normal', 'marginBottom': '5px'}),
                dcc.RangeSlider(
                    id="x-range-slider",
                    min=df["Gravity-API at 60°F"].min(),
                    max=df["Gravity-API at 60°F"].max(),
                    step=0.1,
                    value=[10.7, 68.6],
                    tooltip={"placement": "top", "always_visible": True},
                    marks=None
                )
            ], style={'width': '32%', 'display': 'inline-block'}),

            html.Div([
                html.Label("Select Y Axis Property", style={'color': '#FF6600', 'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id="y-axis-dropdown",
                    options=[
                        {"label": "Sulfur Content-% Wt", "value": "Sulfur Content %"}
                    ],
                    value="Sulfur Content %",
                    clearable=False
                ),
                html.Label("Y Axis Range", style={'color': '#1a1a1a', 'fontWeight': 'normal', 'marginBottom': '5px'}),
                dcc.RangeSlider(
                    id="y-range-slider",
                    min=df["Sulfur Content %"].min(),
                    max=df["Sulfur Content %"].max(),
                    step=0.01,
                    value=[0.00, 5.98],
                    tooltip={"placement": "top", "always_visible": True},
                    marks=None
                )
            ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '2%'}),

            html.Div([
                html.Label("Select Bubble Size Property", style={'color': '#FF6600', 'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id="bubble-size-dropdown",
                    options=[
                        {"label": "Volume-000 b/d", "value": "BubbleSize"}
                    ],
                    value="BubbleSize",
                    clearable=False
                ),
                html.Label("Bubble Size Range", style={'color': '#1a1a1a', 'fontWeight': 'normal', 'marginBottom': '5px'}),
                dcc.RangeSlider(
                    id="bubble-range-slider",
                    min=0,
                    max=int(df["BubbleSize"].max()),
                    step=1,
                    value=[0, int(df["BubbleSize"].max())],
                    tooltip={"placement": "top", "always_visible": True},
                    marks=None
                )
            ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '2%'})
        ]),

        html.Br(),

        dcc.Graph(id='crude-quality-chart')
    ])


def create_crude_quality_dashboard(server, url_base_pathname="/dash/crude-quality/"):
    from pathlib import Path
    
    # Get the directory where this file is located
    current_dir = Path(__file__).parent
    assets_dir = current_dir / "assets"
    
    # Create assets directory if it doesn't exist
    assets_dir.mkdir(exist_ok=True)
    
    dash_app = create_dash_app(server, url_base_pathname)
    
    # Set assets folder for this Dash app - Dash will automatically serve CSS files from here
    dash_app.assets_folder = str(assets_dir)
    
    # Simple index string without inline CSS
    dash_app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>Crude Quality Dashboard</title>
            {%favicon%}
            {%css%}
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    '''
    
    dash_app.layout = create_layout(dash_app)
    register_callbacks(dash_app)
    return dash_app


# ===================================
#  CALLBACK FOR UPDATED GRAPH
# ===================================
def register_callbacks(dash_app, server=None):

    @dash_app.callback(
        Output('crude-quality-chart', 'figure'),
        [
            Input("x-axis-dropdown", "value"),
            Input("y-axis-dropdown", "value"),
            Input("bubble-size-dropdown", "value"),
            Input("x-range-slider", "value"),
            Input("y-range-slider", "value"),
            Input("bubble-range-slider", "value"),
        ]
    )
    def update_crude_quality(x_col, y_col, size_col, x_range, y_range, size_range):

        df = load_crossplot_data()

        # Convert size column to numeric first
        df[size_col] = pd.to_numeric(df[size_col], errors="coerce").fillna(40)

        # Filter data based on ranges
        df = df[
            (df[x_col] >= x_range[0]) & (df[x_col] <= x_range[1]) &
            (df[y_col] >= y_range[0]) & (df[y_col] <= y_range[1]) &
            (df[size_col] >= size_range[0]) & (df[size_col] <= size_range[1])
        ]

        color_map = {
            'Null': '#000000',      # Black
            'FSU': '#008B8B',       # Dark Teal
            'OECD': '#696969',      # Dark Gray
            'OPEC': '#9370DB',      # Light Purple/Blue
            'Others': '#FFA500'     # Orange
        }

        fig = go.Figure()

        # Only add traces if there's data
        if len(df) > 0:
            for region in df["Region"].unique():
                group = df[df["Region"] == region]
                
                if len(group) > 0:
                    # Format volume values with commas
                    volume_formatted = group[size_col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A")
                    
                    fig.add_trace(go.Scatter(
                        x=group[x_col],
                        y=group[y_col],
                        mode="markers",
                        name=str(region),
                        text=group["Crude"],
                        customdata=volume_formatted,
                        marker=dict(
                            size=np.sqrt(group[size_col]) * 2,
                            color=color_map.get(region, "#444"),
                            opacity=0.80,
                            line=dict(width=1, color="white")
                        ),
                        hovertemplate=(
                            "<b>Crude:</b> %{text}<br>" +
                            "<b>Gravity-API at 60 F:</b> %{x:.1f}<br>" +
                            "<b>Sulfur Content-% Wt:</b> %{y:.2f}<br>" +
                            "<b>Volume-000 b/d:</b> %{customdata}<extra></extra>"
                        )
                    ))

        fig.update_layout(
            title=dict(text="Crude Oils Compared by Quality", x=0.5, font=dict(color="#FF6600", size=20)),
            xaxis=dict(
                title=x_col,
                range=[10.0, 65.0],
                dtick=5,
                tickmode="linear",
                showgrid=True,
                gridcolor="lightgray",
                gridwidth=1
            ),
            yaxis=dict(
                title=y_col,
                range=[0.00, 4.50],
                dtick=0.5,
                tickmode="linear",
                showgrid=True,
                gridcolor="lightgray",
                gridwidth=1
            ),
            height=400,
            width=900,
            autosize=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            hovermode="closest",
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="#999999",
                font_size=12,
                font_family='"Benton Sans Low-DPI", Arial, Helvetica, sans-serif',
                font_color="black",
                align="left"
            ),
            margin=dict(l=60, r=40, t=80, b=60),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                xanchor="right",
                x=1
            )
        )

        return fig
