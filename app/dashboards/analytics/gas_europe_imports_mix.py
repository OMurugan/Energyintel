import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table, State, ctx, ALL, no_update
import os
from datetime import datetime
from sqlalchemy import create_engine, text
import time

# Database connection
_engine = None

def get_db_connection():
    """Get database connection using existing config with singleton pattern"""
    global _engine
    if _engine is None:
        try:
            from core.data_helpers import get_db_connection_string
            _engine = create_engine(
                get_db_connection_string(),
                pool_size=5,
                max_overflow=10,
                pool_recycle=3600,
                pool_pre_ping=True,
                pool_timeout=30,
                echo=False
            )
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    return _engine

# Constants
LNG_COLOR = '#1f77b4'  # Blue
PIPELINE_COLOR = '#ff7f0e'  # Orange
TITLE_COLOR = '#fe5000'

# Standard Tableau-like color palette for Gas Origins
COLOR_PALETTE = px.colors.qualitative.T10 + px.colors.qualitative.Alphabet

# Explicit color mapping for key Gas Origins to match Image 1
GAS_ORIGIN_COLORS = {
    'Algeria': '#7681c6',
    'Austria': '#9ecde4',
    'Azerbaijan': '#bfd391',
    'Belgium': '#7882c4',
    'Bulgaria': '#565656',
    'Croatia': '#a3952d',
    'Czech Republic': '#efc85e',
    'Denmark': '#428d8f',
    'Finland': '#88b5aa',
    'France': '#df5858',
    'Germany': '#4c4c4c',
    'Greece': '#726863',
    'Hungary': '#b5a9a1',
    'Ireland': '#d07093',
    'Italy': '#f8bcd1',
    'Joint Baltic Zone EE/LV': '#9e6c93',
    'Libya': '#9a9a9a',
    'Lithuania': '#98715b',
    'LNG': '#006699',
    'Luxembourg': '#e4af95',
    'Moldova': '#4b71aa',
    'Morocco': '#9ecce4',
    'Netherlands': '#f3841a',
    'Norway': '#263e6a',
    'Poland': '#569f4d',
    'Portugal': '#86d079',
    'Romania': '#b4972b',
    'Russia': '#c74d28',
    'Serbia': '#469692',
    'Slovakia': '#80bab4',
    'Slovenia': '#e9595a',
    'Spain': '#b7afa9',
    'Switzerland': '#444444',
    'United Kingdom': '#d17094',
}

def hex_to_rgba(h, a):
    """Convert hex color to rgba string."""
    if not h: return f'rgba(0,0,0,{a})'
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join([c*2 for c in h])
    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({rgb[0]},{rgb[1]},{rgb[2]},{a})'

def load_data(query, params=None):
    """Execute query and return DataFrame"""
    engine = get_db_connection()
    if not engine:
        return pd.DataFrame()
    try:
        with engine.connect() as connection:
            df = pd.read_sql(text(query), connection, params=params)
        return df
    except Exception as e:
        print(f"Query error: {e}")
        return pd.DataFrame()

def create_layout():
    """Create the European Gas Imports Mix layout"""
    # Initial data for filters
    country_query = """
    SELECT DISTINCT tr.target_country
    FROM dev.european_gas_trade tr
    WHERE tr.target_country IS NOT NULL AND TRIM(tr.target_country) <> ''
    ORDER BY tr.target_country;
    """
    countries_df = load_data(country_query)
    countries = countries_df['target_country'].tolist() if not countries_df.empty else []

    origin_query = """
    SELECT DISTINCT tr.source_country
    FROM dev.european_gas_trade tr
    WHERE tr.source_country IS NOT NULL AND TRIM(tr.source_country) <> ''
    ORDER BY tr.source_country;
    """
    origins_df = load_data(origin_query)
    origins = origins_df['source_country'].tolist() if not origins_df.empty else []

    return html.Div([
        # Main Container
        html.Div([
            # Left/Center: Charts Area
            html.Div([
                # Chart 1
                html.Div([
                    html.H2("European Gas Imports - Pipeline vs. LNG - Billion Cubic Meters",
                            style={'color': TITLE_COLOR, 'fontSize': '18px', 'marginBottom': '10px', 'fontFamily': 'Lato, sans-serif'}),
                    dcc.Loading(dcc.Graph(id='chart-1', config={'displayModeBar': False}, figure={}))
                ], style={'marginBottom': '30px', 'backgroundColor': 'white', 'padding': '10px'}),

                # Chart 2
                html.Div([
                    html.H2("All Monthly Gas Imports by Source-Billion Cubic Meters",
                            style={'color': TITLE_COLOR, 'fontSize': '18px', 'marginBottom': '10px', 'fontFamily': 'Lato, sans-serif'}),
                    dcc.Loading(dcc.Graph(id='chart-2', config={'displayModeBar': False}, figure={}))
                ], style={'marginBottom': '30px', 'backgroundColor': 'white', 'padding': '10px'}),

                # Chart 3
                html.Div([
                    html.H2("All Gas Imports Daily - Pipeline vs. LNG - Billion Cubic Meters",
                            style={'color': TITLE_COLOR, 'fontSize': '18px', 'marginBottom': '10px', 'fontFamily': 'Lato, sans-serif'}),
                    dcc.Loading(dcc.Graph(id='chart-3', config={'displayModeBar': False}, figure={}))
                ], style={'marginBottom': '30px', 'backgroundColor': 'white', 'padding': '10px'}),

                # Chart 4 (Table)
                html.Div([
                    html.H2("Gas Flows to Europe by Country and Source-Billion Cubic Meters",
                            style={'color': TITLE_COLOR, 'fontSize': '18px', 'marginBottom': '10px', 'fontFamily': 'Lato, sans-serif'}),
                    dcc.Loading(html.Div(id='table-container'))
                ], style={'marginBottom': '30px', 'marginTop': '20px', 'backgroundColor': 'white', 'padding': '10px'}),
                
                # Source info
                html.P("Source: Energy Intelligence, Transmission System Operators, Federal Agencies",
                       style={'fontSize': '10px', 'color': '#666', 'fontStyle': 'italic', 'paddingLeft': '10px'})

            ], style={'width': 'calc(100% - 210px)', 'padding': '5px', 'display': 'inline-block', 'verticalAlign': 'top'}),

            # Right Side Panel: Filters
            html.Div([
                html.Div([
                    html.Div([
                        html.Label("Country", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        dcc.Dropdown(
                            id='country-dropdown',
                            options=[{'label': '(All)', 'value': '(All)'}] + [{'label': c, 'value': c} for c in countries],
                            value='(All)',
                            clearable=False,
                            style={'fontSize': '12px'}
                        ),
                    ], style={'marginBottom': '15px'}),

                    html.Div([
                        html.Label("Start Date", style={'fontWeight': 'normal', 'fontSize': '12px', 'color': '#333'}),
                        dcc.Input(
                            id='start-date-picker',
                            type='date',
                            value='2021-01-01',
                            max=datetime.now().strftime('%Y-%m-%d'),
                            style={'width': '100%', 'padding': '4px', 'fontSize': '12px', 'border': '1px solid #ccc', 'borderRadius': '4px'}
                        ),
                    ], style={'marginBottom': '10px'}),

                    html.Div([
                        html.Label("End Date", style={'fontWeight': 'normal', 'fontSize': '12px', 'color': '#333'}),
                        dcc.Input(
                            id='end-date-picker',
                            type='date',
                            value=datetime.now().strftime('%Y-%m-%d'),
                            max=datetime.now().strftime('%Y-%m-%d'),
                            style={'width': '100%', 'padding': '4px', 'fontSize': '12px', 'border': '1px solid #ccc', 'borderRadius': '4px'}
                        ),
                    ], style={'marginBottom': '20px'}),

                    html.Div([
                        html.Label("Gas Origin", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        html.Div(id='gas-origin-legend-container', style={'maxHeight': '400px', 'overflowY': 'auto', 'border': '1px solid #eee', 'padding': '8px', 'backgroundColor': 'white'})
                    ], style={'marginBottom': '20px'}),

                    dcc.Store(id='selected-origins-store'),
                    dcc.Store(id='chart1-selection', data=None),
                    dcc.Store(id='chart2-selection', data=None),
                    dcc.Store(id='chart3-selection', data=None),

                    html.Div([
                        html.Label("Flow Type", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        dcc.Checklist(
                            id='flow-type-1',
                            options=[{'label': ' (All)', 'value': '(All)'}, {'label': ' LNG', 'value': 'lng'}, {'label': ' pipeline', 'value': 'pipeline'}],
                            value=['(All)', 'lng', 'pipeline'],
                            labelStyle={'display': 'block', 'fontSize': '11px', 'marginBottom': '2px'},
                            style={'marginBottom': '20px'}
                        ),
                    ]),

                    html.Div([
                        html.Label("Flow Type", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        dcc.Checklist(
                            id='flow-type-2',
                            options=[{'label': ' (All)', 'value': '(All)'}, {'label': ' LNG', 'value': 'LNG'}, {'label': ' pipeline', 'value': 'pipeline'}],
                            value=['(All)', 'LNG', 'pipeline'],
                            labelStyle={'display': 'block', 'fontSize': '11px', 'marginBottom': '2px'},
                            style={'marginBottom': '20px'}
                        ),
                    ], style={'marginTop': '180px'}),

                    # Legend for LNG/Pipeline
                    html.Div([
                        html.Label("Flow Type", style={'fontWeight': 'bold', 'fontSize': '12px', 'color': '#333', 'marginBottom': '5px', 'display': 'block'}),
                        html.Div([
                            html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': LNG_COLOR, 'display': 'inline-block', 'marginRight': '8px'}),
                            html.Span("LNG", style={'fontSize': '11px'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'}),
                        html.Div([
                            html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': PIPELINE_COLOR, 'display': 'inline-block', 'marginRight': '8px'}),
                            html.Span("pipeline", style={'fontSize': '11px'})
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    ], style={'marginTop': '10px'})

                ], style={'padding': '15px', 'backgroundColor': '#fcfcfc', 'borderLeft': '1px solid #eee', 'minHeight': '100vh'})
            ], style={'width': '210px', 'display': 'inline-block', 'verticalAlign': 'top', 'position': 'sticky', 'top': '0'})

        ], style={'display': 'flex', 'flexDirection': 'row', 'width': '100%', 'maxWidth': '1600px', 'margin': '0 auto'})
    ], style={'backgroundColor': '#ffffff', 'fontFamily': 'Lato, sans-serif'})

def register_callbacks(dash_app, server):
    
    # Callback to handle legend item clicks
    @dash_app.callback(
        Output('selected-origins-store', 'data', allow_duplicate=True),
        Input({'type': 'origin-legend-item', 'index': ALL}, 'n_clicks'),
        [State('selected-origins-store', 'data')],
        prevent_initial_call=True
    )
    def handle_legend_click(n_clicks, current_selected):
        if not ctx.triggered or not current_selected:
            return no_update
            
        triggered_id = ctx.triggered_id
        if not triggered_id or triggered_id == '':
            return no_update
            
        clicked_origin = triggered_id['index']
        selected = list(current_selected)
        
        if clicked_origin == '(All)':
            # If All is clicked, we toggle between selecting everything or just the first item
            # But usually Tableau behavior is: Click "All" -> Select all
            if '(All)' in selected:
                # If All was selected, maybe we keep it as is or deselect all but first
                # For simplicity: Always select all if "All" is clicked and not fully selected
                return selected # We'll handle this in the UI callback to reset if needed
            else:
                return ['(All)'] # UI callback will expand this
        
        if '(All)' in selected:
            # If clicking a specific origin while "All" is active, 
            # we switch to only that origin
            return [clicked_origin]
            
        if clicked_origin in selected:
            if len(selected) > 1:
                selected.remove(clicked_origin)
            else:
                # If it's the only one, maybe don't allow deselect or switch to All
                return ['(All)']
        else:
            selected.append(clicked_origin)
            
        return selected

    # Callback to handle "(All)" logic for data flows
    @dash_app.callback(
        Output('selected-origins-store', 'data', allow_duplicate=True),
        Input('selected-origins-store', 'data'),
        State('gas-origin-legend-container', 'children'),
        prevent_initial_call=True
    )
    def sync_all_origins(selected, legend_children):
        if not selected or not legend_children: return selected
        
        # Get all possible origins from legend items (excluding All)
        all_possible = []
        for child in legend_children:
            idx = child['props']['id']['index']
            if idx != '(All)':
                all_possible.append(idx)
        
        if '(All)' in selected and len(selected) == 1:
            return ['(All)'] + all_possible
            
        if set(selected).issuperset(set(all_possible)) and '(All)' not in selected:
            return ['(All)'] + all_possible
            
        if '(All)' in selected and len(selected) > 1 and len(selected) < len(all_possible) + 1:
            return [s for s in selected if s != '(All)']
            
        return selected

    # Similar logic for Flow Type 1 and 2
    @dash_app.callback(
        Output('flow-type-1', 'value'),
        Input('flow-type-1', 'value'),
        prevent_initial_call=True
    )
    def handle_flow1_all(selected):
        all_vals = ['lng', 'pipeline']
        if not selected: return []
        if '(All)' in selected and selected[-1] == '(All)': return ['(All)'] + all_vals
        if '(All)' in selected and len(selected) < 3: return [v for v in selected if v != '(All)']
        if '(All)' not in selected and len(selected) == 2: return ['(All)'] + all_vals
        return selected

    @dash_app.callback(
        Output('flow-type-2', 'value'),
        Input('flow-type-2', 'value'),
        prevent_initial_call=True
    )
    def handle_flow2_all(selected):
        all_vals = ['LNG', 'pipeline']
        if not selected: return []
        if '(All)' in selected and selected[-1] == '(All)': return ['(All)'] + all_vals
        if '(All)' in selected and len(selected) < 3: return [v for v in selected if v != '(All)']
        if '(All)' not in selected and len(selected) == 2: return ['(All)'] + all_vals
        return selected

    @dash_app.callback(
        [Output('gas-origin-legend-container', 'children'),
         Output('selected-origins-store', 'data', allow_duplicate=True)],
        [Input('country-dropdown', 'value'),
         Input('selected-origins-store', 'data')],
        prevent_initial_call='initial_duplicate'
    )
    def update_origin_legend(country, selected):
        # 1. If Country changed (or first load), we reset selection to 'All' for that country
        if not ctx.triggered_id or ctx.triggered_id == 'country-dropdown':
            query = "SELECT DISTINCT source_country FROM dev.european_gas_trade tr WHERE source_country IS NOT NULL AND TRIM(source_country) <> ''"
            params = {}
            if country and country != '(All)':
                query += " AND tr.target_country = :country"
                params['country'] = country
            query += " ORDER BY source_country;"
            df = load_data(query, params)
            origins = df['source_country'].tolist() if not df.empty else []
            selected = ['(All)'] + origins
            # We return selected here to update the store, and we'll build UI below
        
        # 2. Build UI based on 'selected' and 'country'
        query = "SELECT DISTINCT source_country FROM dev.european_gas_trade tr WHERE source_country IS NOT NULL AND TRIM(source_country) <> ''"
        params = {}
        if country and country != '(All)':
            query += " AND tr.target_country = :country"
            params['country'] = country
        query += " ORDER BY source_country;"
        df = load_data(query, params)
        origins = df['source_country'].tolist() if not df.empty else []
        
        if not selected:
            selected = ['(All)'] + origins

        items = []
        is_all_selected = '(All)' in (selected or [])
        
        items.append(html.Div([
            html.Div(style={'width': '12px', 'height': '12px', 'marginRight': '8px', 'border': '1px solid #ccc', 'backgroundColor': '#fff' if is_all_selected else 'transparent'}),
            html.Span("(All)", style={'fontSize': '11px', 'fontWeight': 'bold' if is_all_selected else 'normal', 'color': '#333' if is_all_selected else '#999'})
        ], id={'type': 'origin-legend-item', 'index': '(All)'}, style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '6px', 'cursor': 'pointer'}))

        for i, origin in enumerate(origins):
            is_sel = origin in (selected or [])
            m_color = GAS_ORIGIN_COLORS.get(origin)
            if not m_color:
                m_color = COLOR_PALETTE[i % len(COLOR_PALETTE)]
            
            items.append(html.Div([
                html.Div(style={
                    'width': '12px', 'height': '12px', 'backgroundColor': m_color, 
                    'marginRight': '8px', 'opacity': 1.0 if is_sel else 0.2,
                    'border': '1px solid #eee'
                }),
                html.Span(origin, style={
                    'fontSize': '11px', 
                    'fontWeight': 'normal',
                    'color': '#333' if is_sel else '#999'
                })
            ], id={'type': 'origin-legend-item', 'index': origin}, 
               style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px', 'cursor': 'pointer'}))
               
        return items, selected

    # Selection callback for Chart 3 (Lines)
    @dash_app.callback(
        [Output('chart1-selection', 'data'),
         Output('chart2-selection', 'data'),
         Output('chart3-selection', 'data'),
         Output('chart-1', 'clickData'),
         Output('chart-2', 'clickData'),
         Output('chart-3', 'clickData')],
        [Input('chart-1', 'clickData'),
         Input('chart-2', 'clickData'),
         Input('chart-3', 'clickData'),
         Input('country-dropdown', 'value'),
         Input('start-date-picker', 'value'),
         Input('end-date-picker', 'value'),
         Input('flow-type-1', 'value'),
         Input('flow-type-2', 'value')],
        [State('chart1-selection', 'data'),
         State('chart2-selection', 'data'),
         State('chart3-selection', 'data')]
    )
    def update_chart_selections(c1_click, c2_click, c3_click, country, start, end, f1, f2, s1, s2, s3):
        triggered_id = ctx.triggered_id
        if not triggered_id: return no_update
        
        # 1. Reset all selections if global filters change
        if any(x in triggered_id for x in ['dropdown', 'picker', 'flow-type']):
            return None, None, None, None, None, None
            
        # 2. Handle Chart 1 Click
        if triggered_id == 'chart-1':
            if not c1_click: return no_update
            cdata = c1_click['points'][0].get('customdata', [])
            if not cdata or len(cdata) < 3: return no_update
            
            val = str(cdata[0]) # Year
            flow = str(cdata[1])
            ctype = str(cdata[2])
            
            # Toggle logic
            if ctype == "YEAR_CLICK":
                if s1 and s1.get('mode') == 'year' and str(s1.get('year')) == val:
                    return None, no_update, no_update, None, no_update, no_update
                return {'mode': 'year', 'year': val}, no_update, no_update, None, no_update, no_update
            else:
                if s1 and s1.get('mode') == 'bar' and str(s1.get('year')) == val and str(s1.get('flow')) == flow:
                    return None, no_update, no_update, None, no_update, no_update
                return {'mode': 'bar', 'year': val, 'flow': flow}, no_update, no_update, None, no_update, no_update

        # 3. Handle Chart 2 Click
        if triggered_id == 'chart-2':
            if not c2_click: return no_update
            try:
                raw_m = str(c2_click['points'][0].get('x'))
                clicked_m = pd.to_datetime(raw_m).strftime('%Y-%m-%d')
            except:
                return no_update

            if str(s2) == clicked_m:
                return no_update, None, no_update, no_update, None, no_update
            return no_update, clicked_m, no_update, no_update, None, no_update

        # 4. Handle Chart 3 Click
        if triggered_id == 'chart-3':
            if not c3_click: return no_update
            clicked_f = c3_click['points'][0].get('fullData', {}).get('name')
            if s3 == clicked_f:
                return no_update, no_update, None, no_update, no_update, None
            return no_update, no_update, clicked_f, no_update, no_update, None
            
        return no_update

    # Shared logic helper to reduce code duplication in separate callbacks
    def get_query_params(country, start_date, end_date, origins, flow1, flow2):
        today = datetime.now()
        def parse_dt(d_str, default):
            if not d_str: return default
            try: return pd.to_datetime(d_str, format='%Y-%m-%d')
            except:
                try: return pd.to_datetime(d_str, dayfirst=True)
                except: return default

        start_dt = parse_dt(start_date, pd.to_datetime('2021-01-01'))
        end_dt = parse_dt(end_date, today)
        if end_dt > today: end_dt = today

        # Basic filtering
        where_clause = "WHERE tr.date >= :start AND tr.date <= :end"
        params = {'start': start_dt, 'end': end_dt}
        
        country_clause = ""
        if country and country != '(All)':
            country_clause = " AND tr.target_country = :country"
            params['country'] = country
            
        # Clean specific filters
        of = [o for o in (origins or []) if o != '(All)']
        f1 = [f.lower() for f in (flow1 or []) if f != '(All)']
        f2 = [f.lower() for f in (flow2 or []) if f != '(All)']

        return where_clause, country_clause, params, of, f1, f2

    # CALLBACK 1: Chart 1 Only
    @dash_app.callback(
        Output('chart-1', 'figure'),
        [Input('country-dropdown', 'value'),
         Input('start-date-picker', 'value'),
         Input('end-date-picker', 'value'),
         Input('flow-type-1', 'value'),
         Input('chart1-selection', 'data'),
         Input('chart3-selection', 'data')]
    )
    def update_chart_1(country, start_date, end_date, flow1, sel1, sel3):
        where_clause, country_clause, params, _, f1_filtered, _ = get_query_params(country, start_date, end_date, [], flow1, [])
        
        c1_query = f"""
        SELECT EXTRACT(YEAR FROM tr.date)::int AS "Year", LOWER(tr.flow_type) AS "FlowType", SUM(tr."flow_mcm/d") / 1000.0 AS total_flows_bcm
        FROM dev.european_gas_trade tr {where_clause} {country_clause} AND LOWER(tr.flow_type) IN :flow1 GROUP BY 1, 2 ORDER BY 1, 2;
        """
        # Smooth transition: If transitioning between countries, keep previous chart until data arrives
        if not f1_filtered:
            if ctx.triggered_id in ['country-dropdown', 'start-date-picker', 'end-date-picker']:
                return no_update
            return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 300}}
        
        c1_df = load_data(c1_query, {**params, 'flow1': tuple(f1_filtered)})
        fig1 = go.Figure()
        
        if c1_df.empty: return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 350}}
        c1_df['Flow Name'] = c1_df['FlowType'].apply(lambda x: 'LNG' if x == 'lng' else 'Pipeline')
        years = sorted(c1_df['Year'].unique())
        GREY_OUT = '#e0e0e0'
        
        for flow_name in ['Pipeline', 'LNG']:
            subset = c1_df[c1_df['Flow Name'] == flow_name]
            base_color = PIPELINE_COLOR if flow_name == 'Pipeline' else LNG_COLOR
            colors = []
            for _, row in subset.iterrows():
                ry = int(row['Year'])
                is_dim = False
                
                # Unified Highlight Logic
                if sel1:
                    if sel1['mode'] == 'year':
                        if ry != int(sel1['year']): is_dim = True
                    elif sel1['mode'] == 'bar':
                        if not (ry == int(sel1['year']) and flow_name == sel1['flow']): is_dim = True
                elif sel3:
                    # Highlight based on Chart 3 selection
                    if flow_name.upper() != sel3.upper(): is_dim = True
                
                colors.append(GREY_OUT if is_dim else base_color)

            fig1.add_trace(go.Bar(
                name=flow_name, x=subset['Year'], y=subset['total_flows_bcm'], marker_color=colors,
                text=subset['total_flows_bcm'].round(1), textposition='outside',
                customdata=[[row['Year'], flow_name, "BAR_CLICK"] for _, row in subset.iterrows()],
                hovertemplate="Flow Type: <span style='color:black'><b>"+flow_name+"</b></span><br>Year of Date: <span style='color:black'><b>%{x}</b></span><br>Flow (BCM): <span style='color:black'><b>%{y:.1f}</b></span><extra></extra>"
            ))

        fig1.update_layout(
            barmode='group', plot_bgcolor='white', paper_bgcolor='white', showlegend=False,
            margin=dict(t=50, b=10, l=50, r=20), height=350,
            xaxis=dict(type='category', title="", showticklabels=False),
            yaxis=dict(showgrid=True, gridcolor='#f2f2f2', title="", ticksuffix="   ", tickfont=dict(size=11), visible=True),
            bargap=0.3, bargroupgap=0.05,
            hoverlabel=dict(bgcolor="white", font_size=11, font_color="#777", font_family="Lato, sans-serif", bordercolor="#ddd")
        )
        max_val = c1_df['total_flows_bcm'].max()
        fig1.update_yaxes(range=[0, max_val * 1.25]) 
        fig1.add_trace(go.Scatter(
            x=years, y=[max_val * 1.15] * len(years), mode='text', text=[f"<b>{y}</b>" for y in years],
            textposition='bottom center', textfont=dict(size=14, color='#333'),
            customdata=[[y, "", "YEAR_CLICK"] for y in years], showlegend=False, hoverinfo='none', marker=dict(opacity=0)
        ))
        fig1.add_shape(type="line", x0=-0.5, x1=len(years)-0.5, y0=max_val*1.22, y1=max_val*1.22, line=dict(color="#dee2e6", width=1))
        
        return fig1

    # CALLBACK 2: Chart 2 Only
    @dash_app.callback(
        Output('chart-2', 'figure'),
        [Input('country-dropdown', 'value'),
         Input('start-date-picker', 'value'),
         Input('end-date-picker', 'value'),
         Input('selected-origins-store', 'data'),
         Input('chart2-selection', 'data')]
    )
    def update_chart_2(country, start_date, end_date, origins, sel2):
        where_clause, country_clause, params, origins_filtered, _, _ = get_query_params(country, start_date, end_date, origins, [], [])
        
        # Smooth transition: If transitioning between countries, keep previous chart until data arrives
        if not origins_filtered:
            if ctx.triggered_id in ['country-dropdown', 'start-date-picker', 'end-date-picker']:
                return no_update
            return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 360}}

        c2_query = f"""
        SELECT DATE_TRUNC('month', tr.date) AS "date_month", tr.source_country AS "Gas Origin", SUM(tr."flow_mcm/d") / 1000.0 AS flows_bcm
        FROM dev.european_gas_trade tr {where_clause} {country_clause} AND tr.source_country IN :origins GROUP BY 1, 2 ORDER BY 1;
        """
        c2_df = load_data(c2_query, {**params, 'origins': tuple(origins_filtered)})
        fig2 = go.Figure()
        if c2_df.empty: 
            return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 360}}
        
        c2_df['date_str'] = pd.to_datetime(c2_df['date_month']).dt.strftime('%Y-%m-%d')
        unique_months = sorted(c2_df['date_month'].unique())
        uo = sorted(c2_df['Gas Origin'].unique(), reverse=True) 
        
        # --- Higher Level Decoration ---
        # 1. Full-height backdrop shape for selected month
        if sel2:
            try:
                target_dt = pd.to_datetime(sel2)
                fig2.add_shape(
                    type="rect", xref="x", yref="paper",
                    x0=target_dt - pd.Timedelta(days=14),
                    x1=target_dt + pd.Timedelta(days=14),
                    y0=0, y1=1, fillcolor="rgba(0, 109, 156, 0.06)", line_width=0, layer="below"
                )
            except: pass

        # 2. Main Data Bars
        for i, origin in enumerate(uo):
            sub = c2_df[c2_df['Gas Origin'] == origin]
            m_color = GAS_ORIGIN_COLORS.get(origin, COLOR_PALETTE[i % len(COLOR_PALETTE)])
            clrs = []
            for _, row in sub.iterrows():
                is_dimmed = False
                if sel2 and str(row['date_str']) != str(sel2): is_dimmed = True
                clrs.append(hex_to_rgba(m_color, 0.15) if is_dimmed else m_color)

            fig2.add_trace(go.Bar(
                x=sub['date_month'], y=sub['flows_bcm'], name=origin, 
                marker=dict(color=clrs, line=dict(width=0)), 
                hovertemplate="Origin: <span style='color:black'><b>"+origin+"</b></span><br>Month: <span style='color:black'><b>%{x|%b %y}</b></span><br>Flow (BCM): <span style='color:black'><b>%{y:.3f}</b></span><extra></extra>"
            ))

        # 3. Interactive footer labels (matching Tableau Image)
        footer_colors = []
        footer_text_colors = []
        for m in unique_months:
            if sel2 == pd.to_datetime(m).strftime('%Y-%m-%d'):
                footer_colors.append('rgba(0, 109, 156, 1.0)') # Solid blue flag
                footer_text_colors.append('#ffffff') 
            else: 
                footer_colors.append('rgba(0,0,0,0.03)') 
                footer_text_colors.append('#777')

        fig2.add_trace(go.Bar(
            x=unique_months, y=[1] * len(unique_months),
            yaxis='y2', marker=dict(color=footer_colors, line=dict(width=0)),
            text=[pd.to_datetime(m).strftime('%b %y') for m in unique_months], 
            textposition='inside', insidetextanchor='middle', textangle=-90, 
            textfont=dict(size=10, color=footer_text_colors, family='Lato, sans-serif'),
            hoverinfo='none', showlegend=False,
            customdata=[[m, 'MONTH_LABEL'] for m in unique_months]
        ))

        fig2.update_layout(
            barmode='stack', plot_bgcolor='white', paper_bgcolor='white', showlegend=False,
            margin=dict(t=10, b=0, l=40, r=2), height=360,
            xaxis=dict(showgrid=False, showticklabels=False, anchor='y2'),
            yaxis=dict(
                showgrid=True, gridcolor='#f2f2f2', 
                tickfont=dict(size=11, color='#666'), 
                domain=[0.15, 1],
                tickvals=[0, 20, 40, 60],
                range=[0, 65]
            ),
            yaxis2=dict(domain=[0, 0.15], visible=True, showticklabels=False, fixedrange=True, range=[0, 1]),
            bargap=0.02, 
            uniformtext=dict(minsize=9, mode='show'),
            hoverlabel=dict(bgcolor="white", font_size=11, font_color="#777", font_family="Lato, sans-serif", bordercolor="#ddd")
        )
        return fig2

    # CALLBACK 3: Chart 3 Only
    @dash_app.callback(
        Output('chart-3', 'figure'),
        [Input('country-dropdown', 'value'),
         Input('start-date-picker', 'value'),
         Input('end-date-picker', 'value'),
         Input('flow-type-2', 'value'),
         Input('chart3-selection', 'data'),
         Input('chart1-selection', 'data')]
    )
    def update_chart_3(country, start_date, end_date, flow2, sel3, sel1):
        where_clause, country_clause, params, _, _, flow2_filtered = get_query_params(country, start_date, end_date, [], [], flow2)
        
        # Smooth transition
        if not flow2_filtered:
            if ctx.triggered_id in ['country-dropdown', 'start-date-picker', 'end-date-picker']:
                return no_update
            return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 280}}

        c3_query = f"""
        SELECT tr.date AS "Day of Date", INITCAP(LOWER(tr.flow_type)) AS "FlowName", SUM(tr."flow_mcm/d") / 1000.0 AS flows_bcm
        FROM dev.european_gas_trade tr {where_clause} {country_clause} AND LOWER(tr.flow_type) IN :flow2 GROUP BY 1, 2 ORDER BY 1;
        """
        c3_df = load_data(c3_query, {**params, 'flow2': tuple(flow2_filtered)})
        fig3 = go.Figure()
        if c3_df.empty: return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 280}}
        flow_names = sorted(c3_df['FlowName'].unique())
        
        # Determine current highlight category
        tgt = sel3
        if not tgt and sel1 and sel1.get('mode') == 'bar':
            tgt = sel1.get('flow')

        # Z-order: Put active line on top
        if tgt:
            matches = [f for f in flow_names if f.upper() == tgt.upper()]
            if matches:
                 m = matches[0]
                 flow_names.remove(m)
                 flow_names.append(m)

        for fn in flow_names:
            sub = c3_df[c3_df['FlowName'] == fn]
            bc = LNG_COLOR if fn.upper() == 'LNG' else PIPELINE_COLOR
            is_dim = False
            if tgt and fn.upper() != tgt.upper(): is_dim = True
            
            m_color = hex_to_rgba(bc, 0.1) if is_dim else bc
            line_width = 3.0 if not is_dim else 1.2

            fig3.add_trace(go.Scatter(
                x=sub['Day of Date'], y=sub['flows_bcm'], name=fn, 
                mode='lines', 
                line=dict(color=m_color, width=line_width, shape='spline'),
                hovertemplate="Flow Type: <span style='color:black'><b>"+fn+"</b></span><br>Date: <span style='color:black'><b>%{x|%d %b %y}</b></span><br>Flow (BCM): <span style='color:black'><b>%{y:.4f}</b></span><extra></extra>"
            ))
        
        fig3.update_layout(
            plot_bgcolor='white', paper_bgcolor='white', height=280,
            showlegend=False, hovermode='closest',
            margin=dict(t=10, b=40, l=40, r=10),
            hoverlabel=dict(bgcolor="white", font_size=11, font_color="#777", font_family="Lato, sans-serif", bordercolor="#ddd")
        )
        fig3.update_xaxes(tickformat="%d-%b-%y", dtick="M4", showgrid=False, tickfont=dict(size=9, color='#666'))
        fig3.update_yaxes(showgrid=True, gridcolor='#f5f5f5', rangemode='tozero', tickfont=dict(size=10, color='#666'))
        return fig3

    # CALLBACK 4: Table Only
    @dash_app.callback(
        Output('table-container', 'children'),
        [Input('country-dropdown', 'value'),
         Input('start-date-picker', 'value'),
         Input('end-date-picker', 'value'),
         Input('selected-origins-store', 'data')]
    )
    def update_table(country, start_date, end_date, origins):
        where_clause, country_clause, params, origins_filtered, _, _ = get_query_params(country, start_date, end_date, origins, [], [])
        if not origins_filtered: return html.Div("No data matches selected filters", style={'padding': '20px', 'color': '#999'})

        t_query = f"""
        SELECT TO_CHAR(DATE_TRUNC('month', tr.date), 'FMMonth YYYY') AS "Month of Date", DATE_TRUNC('month', tr.date) as "month_raw",
        tr.source_country AS "Gas Origin", tr.target_country AS "Target Country", SUM(tr."flow_mcm/d") / 1000.0 AS flows_bcm
        FROM dev.european_gas_trade tr {where_clause} {country_clause} AND tr.source_country IN :origins GROUP BY 1, 2, 3, 4 ORDER BY 2 DESC;
        """
        table_df = load_data(t_query, {**params, 'origins': tuple(origins_filtered)})
        if table_df.empty: return html.Div("No data matches selected filters", style={'padding': '20px', 'color': '#999'})

        pivot = table_df.pivot_table(index=['month_raw', 'Month of Date'], columns=['Gas Origin', 'Target Country'], values='flows_bcm', aggfunc='sum').fillna(0).sort_index(level=0, ascending=False)
        cols = [{"name": ["", "Month"], "id": "Month"}]
        cuo = sorted(table_df['Gas Origin'].unique())
        for origin in cuo:
            tcs = sorted(table_df[table_df['Gas Origin'] == origin]['Target Country'].unique())
            for tc in tcs: cols.append({"name": [origin, tc], "id": f"{origin}_{tc}"})
        
        rows = [{"Month": m_name, **{c["id"]: f"{row.get(tuple(c['name']), 0):.3f}" for c in cols[1:]}} for (m_raw, m_name), row in pivot.iterrows()]

        return dash_table.DataTable(
            columns=cols, data=rows, merge_duplicate_headers=True,
            style_table={'overflowX': 'auto', 'border': '1px solid #ddd', 'minWidth': '100%'},
            style_cell={'textAlign': 'right', 'padding': '8px', 'fontSize': '11px', 'minWidth': '80px','fontFamily': 'Lato, sans-serif','color': '#333','border': '1px solid #f0f0f0'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'border': '1px solid #dee2e6','textAlign': 'center','fontSize': '11px','color': '#444','padding': '10px'},
            style_data_conditional=[{'if': {'column_id': 'Month'}, 'textAlign': 'left', 'fontWeight': 'bold', 'backgroundColor': '#f2f2f2', 'minWidth': '120px', 'position': 'sticky', 'left': 0}, {'if': {'row_index': 'odd'}, 'backgroundColor': '#fafafa'}],
            fixed_columns={'headers': True, 'data': 1}, fixed_rows={'headers': True}
        )
