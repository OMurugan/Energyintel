"""
Country Overview View
Replicates Energy Intelligence WCoD Country Overview functionality
"""
from dash import dcc, html, Input, Output, State, callback, dash_table, dash
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta
from app import db
from app.models import Country, Production, Exports, Reserves
from sqlalchemy import func


def create_layout():
    """Create the Country Overview layout"""
    return html.Div([
        # Store for selected country
        dcc.Store(id='selected-country-store', data=None),
        # Store for profile URL to open
        dcc.Store(id='profile-url-store', data=None),
        # Store for click counter (ensures callback fires on every click)
        dcc.Store(id='click-counter-store', data=0),
        # Hidden div to trigger URL opening via clientside callback
        html.Div(id='open-url-trigger', children=0, style={'display': 'none'}),
        
        html.Div([
            html.H4(
                "Click on the Country's name to view the Profile",
                style={'textAlign': 'center', 'marginBottom': '20px', 'color': '#2c3e50', 'fontWeight': '500'}
            )
        ]),
        
        # Ranking Chart Card
        html.Div([
            html.Div([
                html.Div([
                    html.H5(
                        "Ranking the world's crude oil exporters",
                        style={'margin': '0', 'display': 'inline-block', 'color': '#2c3e50', 'fontWeight': '600'}
                    ),
                    html.Button(
                        '−',
                        id='chart-collapse-button',
                        n_clicks=0,
                        style={
                            'float': 'right',
                            'fontSize': '20px',
                            'fontWeight': 'bold',
                            'color': '#2c3e50',
                            'textDecoration': 'none',
                            'padding': '0 10px',
                            'border': 'none',
                            'background': 'transparent',
                            'cursor': 'pointer'
                        }
                    )
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'width': '100%', 'padding': '15px', 'background': '#f8f9fa', 'borderBottom': '1px solid #dee2e6'})
            ]),
            html.Div([
                dcc.Graph(
                    id='exports-ranking-chart',
                    clickData=None,
                    style={'height': '600px'}
                )
            ], id='chart-collapse-content', style={'padding': '20px', 'background': 'white'})
        ], style={'background': 'white', 'border': '1px solid #dee2e6', 'borderRadius': '4px', 'marginBottom': '30px', 'overflow': 'hidden'}),
        
        # Data Table Section
        html.Div([
            html.H5(
                "Leading Oil Exporting Countries",
                style={'textAlign': 'center', 'marginTop': '30px', 'marginBottom': '20px', 
                       'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '18px'}
            ),
            dash_table.DataTable(
                id='oil-data-table',
                columns=[
                    {"name": ["", "Country"], "id": "Country", "type": "text", "presentation": "markdown"},
                    {"name": ["Exports", "2024"], "id": "Exports_2024", "type": "numeric", "format": {"specifier": ",.0f"}},
                    {"name": ["Exports", "2023"], "id": "Exports_2023", "type": "numeric", "format": {"specifier": ",.0f"}},
                    {"name": ["Production", "2024"], "id": "Production_2024", "type": "numeric", "format": {"specifier": ",.0f"}},
                    {"name": ["Production", "2023"], "id": "Production_2023", "type": "numeric", "format": {"specifier": ",.0f"}},
                    {"name": ["R/P Ratio", "2024"], "id": "R_P_Ratio_2024", "type": "numeric", "format": {"specifier": ",.1f"}},
                    {"name": ["R/P Ratio", "2023"], "id": "R_P_Ratio_2023", "type": "numeric", "format": {"specifier": ",.1f"}},
                    {"name": ["Reserves", "2024"], "id": "Reserves_2024", "type": "numeric", "format": {"specifier": ",.1f"}},
                    {"name": ["Reserves", "2023"], "id": "Reserves_2023", "type": "numeric", "format": {"specifier": ",.1f"}}
                ],
                style_cell={
                    'textAlign': 'center',
                    'padding': '8px',
                    'fontSize': '12px',
                    'fontFamily': 'Arial, sans-serif',
                    'border': '1px solid #dee2e6'
                },
                style_header={
                    'backgroundColor': '#f8f9fa',
                    'fontWeight': 'bold',
                    'border': '1px solid #dee2e6',
                    'textAlign': 'center'
                },
                style_data={
                    'border': '1px solid #dee2e6',
                    'backgroundColor': 'white'
                },
                style_cell_conditional=[
                    {
                        'if': {'column_id': 'Country'},
                        'textAlign': 'left',
                        'fontWeight': 'bold',
                        'minWidth': '150px'
                    }
                ],
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ],
                merge_duplicate_headers=True,
                page_size=25,
                sort_action='native',
                filter_action='native',
                style_table={
                    'overflowX': 'auto',
                    'border': '1px solid #dee2e6'
                },
                cell_selectable=True
            )
        ]),
        
        # Footer notes
        html.Div([
            html.P(
                "Countries: Select jurisdictions are included under countries for data presentation purposes.",
                style={'fontSize': '10px', 'fontStyle': 'italic', 'marginTop': '20px', 'color': '#6c757d'}
            ),
            html.P(
                "Source: Energy Intelligence | COPYRIGHT © 2001-2025 ENERGY INTELLIGENCE GROUP, INC.",
                style={'fontSize': '10px', 'fontStyle': 'italic', 'marginTop': '10px', 'color': '#6c757d'}
            )
        ])
    ], className='tab-content')


def create_ranking_chart(selected_country=None, server=None):
    """Create horizontal bar chart ranking crude oil exporters"""
    if not server:
        return go.Figure()
    
    with server.app_context():
        # Get latest date (assume 2024, fallback to max date)
        latest_date = db.session.query(func.max(Exports.date)).scalar()
        if not latest_date:
            return go.Figure()
        
        # Get 2024 and 2023 data
        date_2024 = latest_date
        date_2023 = date_2024 - timedelta(days=365) if date_2024 else None
        
        # Get exports and production data
        exports_2024 = db.session.query(
            Country.name,
            func.sum(Exports.exports_bbl).label('exports')
        ).join(Exports).filter(
            Exports.date == date_2024
        ).group_by(Country.id, Country.name).all()
        
        production_2024 = db.session.query(
            Country.name,
            func.sum(Production.production_bbl).label('production')
        ).join(Production).filter(
            Production.date == date_2024
        ).group_by(Country.id, Country.name).all()
        
        # Create DataFrame
        exports_dict = {r.name: r.exports / 1000 for r in exports_2024}  # Convert to '000 b/d
        production_dict = {r.name: r.production / 1000 for r in production_2024}
        
        # Combine and get top 9 by exports
        all_countries = set(exports_dict.keys()) | set(production_dict.keys())
        chart_data = []
        for country in all_countries:
            chart_data.append({
                'Country': country,
                'Exports_2024': exports_dict.get(country, 0),
                'Production_2024': production_dict.get(country, 0)
            })
        
        df = pd.DataFrame(chart_data)
        # Get top 9 by exports (descending), then sort ascending for chart display
        df = df.sort_values('Exports_2024', ascending=False).head(9).sort_values('Exports_2024', ascending=True)
        
        if df.empty:
            return go.Figure()
        
        country_list = df['Country'].astype(str).str.strip().tolist()
        
        # Determine colors
        export_colors = ['#0075A8' if country == selected_country else 'rgb(0, 117, 168)' for country in country_list]
        production_colors = ['#595959' if country == selected_country else 'rgb(89, 89, 89)' for country in country_list]
        
        fig = go.Figure()
        
        # Add Production bar (second, appears on right)
        fig.add_trace(go.Bar(
            y=country_list,
            x=df['Production_2024'].tolist(),
            orientation='h',
            marker=dict(
                color=production_colors,
                line=dict(color=production_colors, width=1.5 if selected_country else 0.5)
            ),
            text=df['Production_2024'].apply(lambda x: f'{x:,.0f}' if pd.notna(x) else '').tolist(),
            textposition='outside',
            name='Production',
            hovertemplate='<b>%{y}</b><br>Production: %{x:,.0f} (\'000 b/d)<br>Year: 2024<extra></extra>',
            showlegend=True,
            legendgroup='production',
            offsetgroup='production',
            width=0.4
        ))
        
        # Add Exports bar (first, appears on left)
        fig.add_trace(go.Bar(
            y=country_list,
            x=df['Exports_2024'].tolist(),
            orientation='h',
            marker=dict(
                color=export_colors,
                line=dict(color=export_colors, width=1.5 if selected_country else 0.5)
            ),
            text=df['Exports_2024'].apply(lambda x: f'{x:,.0f}' if pd.notna(x) else '').tolist(),
            textposition='outside',
            name='Exports',
            hovertemplate='<b>%{y}</b><br>Exports: %{x:,.0f} (\'000 b/d)<br>Year: 2024<extra></extra>',
            showlegend=True,
            legendgroup='exports',
            offsetgroup='exports',
            width=0.4
        ))
        
        max_val = max(df['Exports_2024'].max(), df['Production_2024'].max()) if len(df) > 0 else 1000
        
        fig.update_layout(
            title={
                'text': "Ranking the world's crude oil exporters",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'family': 'Arial, sans-serif', 'color': '#2c3e50'}
            },
            xaxis_title="('000 b/d)",
            yaxis_title="",
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                font=dict(size=12, family='Arial, sans-serif'),
                bgcolor='rgba(255,255,255,0.8)',
                traceorder='normal',
                itemsizing='constant'
            ),
            height=600,
            margin=dict(l=150, r=120, t=90, b=40),
            xaxis=dict(
                range=[0, max_val * 1.2] if max_val > 0 else [0, 1000],
                showgrid=True,
                gridcolor='#E0E0E0',
                gridwidth=1,
                tickformat=',',
                zeroline=False,
                showline=True,
                linecolor='#000000',
                linewidth=1
            ),
            yaxis=dict(
                categoryorder='array',
                categoryarray=country_list,
                tickfont=dict(size=11, family='Arial, sans-serif'),
                showline=True,
                linecolor='#000000',
                linewidth=1,
                side='left',
                type='category'
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            hovermode='closest',
            barmode='group',
            bargap=0.3,
            bargroupgap=0.4
        )
        
        # Set legend order
        fig.update_traces(selector=dict(name='Exports'), legendrank=1)
        fig.update_traces(selector=dict(name='Production'), legendrank=2)
        
        return fig


def register_callbacks(dash_app, server):
    """Register all callbacks for Country Overview"""
    
    @callback(
        Output('exports-ranking-chart', 'figure'),
        [Input('current-submenu', 'data'),
         Input('selected-country-store', 'data')],
        prevent_initial_call=False
    )
    def update_ranking_chart(submenu, selected_country):
        """Update ranking chart with highlighting"""
        if submenu != 'country-overview':
            return go.Figure()
        return create_ranking_chart(selected_country=selected_country)
    
    @callback(
        [Output('oil-data-table', 'data'),
         Output('oil-data-table', 'columns')],
        Input('current-submenu', 'data'),
        prevent_initial_call=False
    )
    def update_oil_data_table(submenu):
        """Update oil data table with country statistics"""
        if submenu != 'country-overview':
            return [], []
        
        with server.app_context():
            latest_date = db.session.query(func.max(Exports.date)).scalar()
            if not latest_date:
                return [], []
            
            date_2024 = latest_date
            date_2023 = date_2024 - timedelta(days=365) if date_2024 else None
            
            # Get all countries with data
            countries = Country.query.all()
            table_data = []
            
            for country in countries:
                # Get 2024 data
                exports_2024 = db.session.query(func.sum(Exports.exports_bbl)).filter(
                    Exports.country_id == country.id,
                    Exports.date == date_2024
                ).scalar() or 0
                
                exports_2023 = db.session.query(func.sum(Exports.exports_bbl)).filter(
                    Exports.country_id == country.id,
                    Exports.date == date_2023
                ).scalar() or 0 if date_2023 else 0
                
                production_2024 = db.session.query(func.sum(Production.production_bbl)).filter(
                    Production.country_id == country.id,
                    Production.date == date_2024
                ).scalar() or 0
                
                production_2023 = db.session.query(func.sum(Production.production_bbl)).filter(
                    Production.country_id == country.id,
                    Production.date == date_2023
                ).scalar() or 0 if date_2023 else 0
                
                reserves_2024 = db.session.query(func.sum(Reserves.reserves_bbl)).filter(
                    Reserves.country_id == country.id,
                    Reserves.date == date_2024
                ).scalar() or 0
                
                reserves_2023 = db.session.query(func.sum(Reserves.reserves_bbl)).filter(
                    Reserves.country_id == country.id,
                    Reserves.date == date_2023
                ).scalar() or 0 if date_2023 else 0
                
                # Calculate R/P Ratio (Reserves to Production ratio in years)
                rp_ratio_2024 = (reserves_2024 / production_2024 / 365) if production_2024 > 0 else 0
                rp_ratio_2023 = (reserves_2023 / production_2023 / 365) if production_2023 > 0 else 0
                
                # Only include countries with data
                if exports_2024 > 0 or production_2024 > 0:
                    profile_url = f"/wcod-country-overview?country={country.id}"
                    table_data.append({
                        'Country': f"[{country.name}]({profile_url})",
                        'Country_Original': country.name,
                        'Profile_URL': profile_url,
                        'Exports_2024': exports_2024 / 1000,  # Convert to '000 b/d
                        'Exports_2023': exports_2023 / 1000,
                        'Production_2024': production_2024 / 1000,
                        'Production_2023': production_2023 / 1000,
                        'R_P_Ratio_2024': rp_ratio_2024,
                        'R_P_Ratio_2023': rp_ratio_2023,
                        'Reserves_2024': reserves_2024 / 1e9,  # Convert to billion bbl
                        'Reserves_2023': reserves_2023 / 1e9
                    })
            
            # Sort by 2024 exports descending
            table_data.sort(key=lambda x: x['Exports_2024'], reverse=True)
        
        columns = [
            {"name": ["", "Country"], "id": "Country", "type": "text", "presentation": "markdown"},
            {"name": ["Exports", "2024"], "id": "Exports_2024", "type": "numeric", "format": {"specifier": ",.0f"}},
            {"name": ["Exports", "2023"], "id": "Exports_2023", "type": "numeric", "format": {"specifier": ",.0f"}},
            {"name": ["Production", "2024"], "id": "Production_2024", "type": "numeric", "format": {"specifier": ",.0f"}},
            {"name": ["Production", "2023"], "id": "Production_2023", "type": "numeric", "format": {"specifier": ",.0f"}},
            {"name": ["R/P Ratio", "2024"], "id": "R_P_Ratio_2024", "type": "numeric", "format": {"specifier": ",.1f"}},
            {"name": ["R/P Ratio", "2023"], "id": "R_P_Ratio_2023", "type": "numeric", "format": {"specifier": ",.1f"}},
            {"name": ["Reserves", "2024"], "id": "Reserves_2024", "type": "numeric", "format": {"specifier": ",.1f"}},
            {"name": ["Reserves", "2023"], "id": "Reserves_2023", "type": "numeric", "format": {"specifier": ",.1f"}}
        ]
        
        return table_data, columns
    
    @callback(
        [Output('selected-country-store', 'data', allow_duplicate=True),
         Output('profile-url-store', 'data', allow_duplicate=True),
         Output('click-counter-store', 'data', allow_duplicate=True)],
        Input('exports-ranking-chart', 'clickData'),
        State('click-counter-store', 'data'),
        prevent_initial_call=True
    )
    def update_selected_country_from_chart(clickData, click_counter):
        """Update selected country and profile URL from chart click"""
        if clickData and 'points' in clickData and len(clickData['points']) > 0:
            country_name = clickData['points'][0]['y']
            # Get profile URL from database
            profile_url = None
            with server.app_context():
                country = Country.query.filter_by(name=country_name).first()
                if country:
                    profile_url = f"/wcod-country-overview?country={country.id}"
            new_counter = (click_counter or 0) + 1
            return country_name, profile_url, new_counter
        return dash.no_update, dash.no_update, click_counter
    
    @callback(
        [Output('selected-country-store', 'data', allow_duplicate=True),
         Output('profile-url-store', 'data', allow_duplicate=True),
         Output('click-counter-store', 'data', allow_duplicate=True)],
        Input('oil-data-table', 'active_cell'),
        [State('oil-data-table', 'data'),
         State('click-counter-store', 'data')],
        prevent_initial_call=True
    )
    def update_selected_country_from_table(active_cell, table_data, click_counter):
        """Update selected country and profile URL from table click"""
        if active_cell and table_data and active_cell.get('row') is not None:
            row_idx = active_cell['row']
            if row_idx < len(table_data):
                row = table_data[row_idx]
                country = row.get('Country_Original', row.get('Country', ''))
                # Extract from markdown if needed
                if isinstance(country, str) and country.startswith('[') and '](' in country:
                    country = country.split('](')[0][1:]
                profile_url = row.get('Profile_URL')
                new_counter = (click_counter or 0) + 1
                return country, profile_url, new_counter
        return dash.no_update, dash.no_update, click_counter
    
    @callback(
        Output('exports-ranking-chart', 'figure', allow_duplicate=True),
        Input('selected-country-store', 'data'),
        State('current-submenu', 'data'),
        prevent_initial_call=True
    )
    def update_chart_highlight(selected_country, submenu):
        """Update chart highlighting based on selected country"""
        if submenu != 'country-overview':
            return dash.no_update
        return create_ranking_chart(selected_country=selected_country, server=server)
    
    @callback(
        Output('oil-data-table', 'style_data_conditional', allow_duplicate=True),
        Input('selected-country-store', 'data'),
        State('oil-data-table', 'data'),
        prevent_initial_call=True
    )
    def update_table_highlight(selected_country, table_data):
        """Update table row highlighting based on selected country"""
        style_conditions = [
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ]
        
        if selected_country and table_data:
            for idx, row in enumerate(table_data):
                country_original = row.get('Country_Original', '')
                if country_original == selected_country:
                    style_conditions.append({
                        'if': {'row_index': idx},
                        'backgroundColor': '#FFF8DC',  # Light yellow highlight
                        'fontWeight': 'bold'
                    })
                    break
        
        return style_conditions
    
    @callback(
        [Output('chart-collapse-content', 'style'),
         Output('chart-collapse-button', 'children')],
        Input('chart-collapse-button', 'n_clicks'),
        State('chart-collapse-content', 'style'),
        prevent_initial_call=True
    )
    def toggle_chart_collapse(n_clicks, current_style):
        """Toggle chart collapse/expand"""
        if n_clicks:
            is_hidden = current_style.get('display') == 'none'
            new_style = {**current_style, 'display': 'none' if not is_hidden else 'block'}
            button_text = '+' if is_hidden else '−'
            return new_style, button_text
        return current_style, '−'
    
    # Client-side callback to open profile URL in new tab
    dash_app.clientside_callback(
        """
        function(url, click_counter) {
            if (url && url !== '' && url !== null && url !== undefined && url !== 'None' && url !== 'null' && click_counter > 0) {
                // Always open in new tab (target=_blank)
                setTimeout(function() {
                    window.open(url, '_blank', 'noopener,noreferrer');
                }, 100);
                return click_counter; // Return counter to track changes
            }
            return click_counter || 0;
        }
        """,
        Output('open-url-trigger', 'children'),
        [Input('profile-url-store', 'data'),
         Input('click-counter-store', 'data')]
    )

