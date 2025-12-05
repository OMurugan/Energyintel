import os
import re
from pathlib import Path
from dash import dcc, html, Input, Output, State, callback, dash_table
from dash.dcc import Loading
import plotly.graph_objects as go
import pandas as pd
from core.data_helpers import execute_query
import traceback

REGION_COLORS = {
    'Africa': 'rgb(0, 117, 168)',        # #0075A8
    'Asia': 'rgb(89, 89, 89)',           # #595959
    'Europe': 'rgb(49, 59, 73)',         # #313B49
    'FSU': 'rgb(121, 134, 203)',         # #7986CB
    'Latin America': 'rgb(166, 166, 166)',  # #A6A6A6
    'Middle East': 'rgb(191, 82, 39)',   # #BF5227
    'North America': 'rgb(195, 210, 151)'  # #C3D297
}

REGIONS = ['Africa', 'Asia', 'Europe', 'FSU', 'Latin America', 'Middle East', 'North America']

def load_chart_data():
    try:
        query = '''
            WITH base AS (
                SELECT
                    c.region,
                    COALESCE(TRIM(a.likely_goahead), '') AS likely_goahead,
                    est.project_id,
                    est."2024_Q1", est."2024_Q2", est."2024_Q3", est."2024_Q4",
                    est."2025_Q1", est."2025_Q2", est."2025_Q3", est."2025_Q4",
                    est."2026_Q1", est."2026_Q2", est."2026_Q3", est."2026_Q4",
                    est."2027_Q1", est."2027_Q2", est."2027_Q3", est."2027_Q4",
                    est."2028_Q1", est."2028_Q2", est."2028_Q3", est."2028_Q4",
                    est."2029_Q1", est."2029_Q2", est."2029_Q3", est."2029_Q4"
                FROM dev.fact_upstream_project_tracker a
                LEFT JOIN dev.fact_upstream_tracker_prod_estimates est 
                    ON a.project_id = est.project_id
                LEFT JOIN dev.dim_country c 
                    ON a.country_id = c.dim_country_id
                WHERE a.include = TRUE
            ),

            unpvt AS (
                SELECT 
                    region,
                    likely_goahead,
                    project_id,
                    SPLIT_PART(quarter_col, '_', 1)::INT AS year_of_period,
                    SPLIT_PART(quarter_col, '_', 2)       AS quarter_of_period,
                    value AS production_additions
                FROM base
                CROSS JOIN LATERAL (
                    VALUES
                        ('2024_Q1', "2024_Q1"), ('2024_Q2', "2024_Q2"),
                        ('2024_Q3', "2024_Q3"), ('2024_Q4', "2024_Q4"),
                        ('2025_Q1', "2025_Q1"), ('2025_Q2', "2025_Q2"),
                        ('2025_Q3', "2025_Q3"), ('2025_Q4', "2025_Q4"),
                        ('2026_Q1', "2026_Q1"), ('2026_Q2', "2026_Q2"),
                        ('2026_Q3', "2026_Q3"), ('2026_Q4', "2026_Q4"),
                        ('2027_Q1', "2027_Q1"), ('2027_Q2', "2027_Q2"),
                        ('2027_Q3', "2027_Q3"), ('2027_Q4', "2027_Q4"),
                        ('2028_Q1', "2028_Q1"), ('2028_Q2', "2028_Q2"),
                        ('2028_Q3', "2028_Q3"), ('2028_Q4', "2028_Q4"),
                        ('2029_Q1', "2029_Q1"), ('2029_Q2', "2029_Q2"),
                        ('2029_Q3', "2029_Q3"), ('2029_Q4', "2029_Q4")
                ) AS t(quarter_col, value)

                WHERE 
                    value IS NOT NULL 
                    OR likely_goahead = ''
            )

            SELECT
                year_of_period AS "Year of Period",
                quarter_of_period AS "Quarter of Period",
                region AS "Region",
                likely_goahead AS "Likely Go-ahead",
                SUM(COALESCE(production_additions, 0)) AS "Production Additions"
            FROM unpvt
            GROUP BY 
                year_of_period, 
                quarter_of_period, 
                region, 
                likely_goahead
            ORDER BY 
                year_of_period, 
                quarter_of_period, 
                region, 
                likely_goahead;
        '''

        results = execute_query(query)

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)

        col_map = {
            'Year of Period': 'Year',
            'year_of_period': 'Year',
            'Quarter of Period': 'Quarter',
            'quarter_of_period': 'Quarter',
            'Region': 'Region',
            'region': 'Region',
            'Likely Go-ahead': 'likely_goahead',
            'likely_goahead': 'likely_goahead',
            'Production Additions': 'Value',
            'production_additions': 'Value'
        }
        df = df.rename(columns=col_map)
        required_cols = ['Year', 'Quarter', 'Region', 'Value', 'likely_goahead']
        if not all(c in df.columns for c in required_cols):
            return pd.DataFrame()

        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce').fillna(0)
        df = df[df['Year'].notna()]
        df['likely_goahead'] = df['likely_goahead'].astype(str).fillna('').replace({'nan': '', 'None': ''})
        df_2025_2029 = df[df['Year'].between(2025, 2029)]
        if df_2025_2029.empty:
            print("WARNING: No non-null chart data for years 2025–2029; using zero values.")
        else:
            df = df_2025_2029

        df['Quarter'] = df.apply(lambda row: f"{row['Quarter']}\n{int(row['Year'])}", axis=1)
        quarter_map = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
        df['QuarterNum'] = df['Quarter'].apply(lambda x: quarter_map.get(x.split('\n')[0], 0))
        df = df[df['QuarterNum'] != 0].copy()

        all_combinations_list = []
        unique_likely_goahead_from_df = df['likely_goahead'].unique().tolist()
        standard_likely_goahead_options = ['Y', 'N', 'Uncertain', '']
        all_possible_likely_goahead = sorted(list(set(unique_likely_goahead_from_df + standard_likely_goahead_options)))

        for region in REGIONS:
            for year in range(2025, 2030):
                for q_str in quarter_map.keys():
                    for l_goahead in all_possible_likely_goahead:
                        all_combinations_list.append({
                            'Region': region,
                            'Year': year,
                            'Quarter': f'{q_str}\n{year}',
                            'QuarterNum': quarter_map[q_str],
                            'likely_goahead': l_goahead
                        })
        all_combinations = pd.DataFrame(all_combinations_list)

        chart_df = pd.merge(
            all_combinations,
            df,
            on=['Region', 'Year', 'Quarter', 'QuarterNum', 'likely_goahead'],
            how='left'
        ).fillna({'Value': 0})

        chart_df = chart_df.sort_values(by=['Region', 'Year', 'QuarterNum', 'likely_goahead']).reset_index(drop=True)
        return chart_df

    except Exception as e:
        traceback.print_exc()
        return pd.DataFrame()


def load_table_data():
    try:
        query = """
        SELECT
            a.project_name AS "Project Name",
            a.likely_goahead,
            c.country_long_name AS Country,
            c.region AS Region,
            CASE
                WHEN c.opec_grp = 'opec' OR c.opec_grp = 'opec_plus' THEN 'Opec-Plus'
                ELSE 'Non-Opec-Plus'
            END AS Opec_group,
            a.field_type,
            a.field,
            a.play_type,
            a.hydrocarbon AS Hydrocarbon,
            cr.crude_name AS "Associated Crude",
            a.depth AS Depth,
            op.company_name AS Operator,
            p1.company_name AS Partner1,
            p2.company_name AS Partner2,
            p3.company_name AS Partner3,
            p4.company_name AS Partner4,
            p5.company_name AS Partner5,
            yr.year AS "First Oil Year",
            a.sanctioned AS Sanctioned,
            a.external_comments AS Comments,
            a.project_status AS "Project Status",
            a.reserves_gas_mmboe AS "Gas Reserves (mmboe)",
            a.reserves_liquids_mmbbl AS "Liquids Reserves (mmbbl)",
            (
                COALESCE(
                    NULLIF(SPLIT_PART(a.reserves_gas_mmboe, '-', 1), '')::numeric,
                    0
                )
                +
                COALESCE(
                    NULLIF(SPLIT_PART(a.reserves_liquids_mmbbl, '-', 1), '')::numeric,
                    0
                )
            ) AS "Total Reserves (mmboe)",
            a.api_cat AS API,
            a.sulfur_cat AS Sulfur,
            a.operator_pc AS "Operator Share %",
            a.partner1_pc AS "Partner1 Share %",
            a.partner2_pc AS "Partner2 Share %",
            a.partner3_pc AS "Partner3 Share %",
            a.partner4_pc AS "Partner4 Share %",
            a.partner5_pc AS "Partner5 Share %",
            est."2024_Q1",
            est."2024_Q2",
            est."2024_Q3",
            est."2024_Q4",
            est."2025_Q1",
            est."2025_Q2",
            est."2025_Q3",
            est."2025_Q4",
            est."2026_Q1",
            est."2026_Q2",
            est."2026_Q3",
            est."2026_Q4",
            est."2027_Q1",
            est."2027_Q2",
            est."2027_Q3",
            est."2027_Q4",
            est."2028_Q1",
            est."2028_Q2",
            est."2028_Q3",
            est."2028_Q4",
            est."2029_Q1",
            est."2029_Q2",
            est."2029_Q3",
            est."2029_Q4"
        FROM dev.fact_upstream_project_tracker a
        LEFT JOIN dev.fact_upstream_tracker_prod_estimates est 
            ON a.project_id = est.project_id
        LEFT JOIN dev.dim_country c 
            ON a.country_id = c.dim_country_id
        LEFT JOIN dev.dim_company op 
            ON a.operator_id = op.company_id
        LEFT JOIN dev.dim_company p1 
            ON a.partner1_id = p1.company_id
        LEFT JOIN dev.dim_company p2 
            ON a.partner2_id = p2.company_id
        LEFT JOIN dev.dim_company p3 
            ON a.partner3_id = p3.company_id
        LEFT JOIN dev.dim_company p4 
            ON a.partner4_id = p4.company_id
        LEFT JOIN dev.dim_company p5 
            ON a.partner5_id = p5.company_id
        LEFT JOIN (
            SELECT 
                project_id,
                MIN(EXTRACT(YEAR FROM period)) AS year
            FROM dev.fact_upstream_tracker_prod_estimates_incremental
            WHERE value IS NOT NULL 
            GROUP BY project_id
        ) yr ON yr.project_id = a.project_id
        LEFT JOIN dev.dim_crude cr 
            ON cr.dim_crude_id = a.crude_id
        WHERE a.include = TRUE
        ORDER BY a.project_name;
        """
        
        results = execute_query(query)
        if not results:
            return pd.DataFrame()
                
        df = pd.DataFrame(results)
        column_mapping = {
            'Country': 'Country',
            'country': 'Country',
            'Region': 'Region',
            'region': 'Region',
            'Opec_group': 'Opec_group',
            'opec_group': 'Opec_group',
            'field_type': 'field_type',
            'Field Type': 'field_type',
            'field': 'field',
            'Field': 'field',
            'play_type': 'play_type',
            'Play Type': 'play_type',
            'hydrocarbon': 'Hydrocarbon',
            'Hydrocarbon': 'Hydrocarbon',
            'depth': 'Depth',
            'Depth': 'Depth',
            'operator': 'Operator',
            'Operator': 'Operator',
            'partner1': 'Partner1',
            'Partner1': 'Partner1',
            'partner2': 'Partner2',
            'Partner2': 'Partner2',
            'partner3': 'Partner3',
            'Partner3': 'Partner3',
            'partner4': 'Partner4',
            'Partner4': 'Partner4',
            'partner5': 'Partner5',
            'Partner5': 'Partner5',
            'sanctioned': 'Sanctioned',
            'Sanctioned': 'Sanctioned',
            'comments': 'Comments',
            'Comments': 'Comments',
            'api': 'API',
            'API': 'API',
            'sulfur': 'Sulfur',
            'Sulfur': 'Sulfur',
            'likely_goahead': 'likely_goahead'
        }
        
        df = df.rename(columns=column_mapping)
        df = df.fillna('')        
        return df
    except Exception as e:
        traceback.print_exc()
        return pd.DataFrame()


def create_layout():
    region_legend_items = [
        html.Div([
            html.Div(style={
                'width': '16px',
                'height': '16px',
                'backgroundColor': REGION_COLORS[region],
                'border': '1px solid #ccc',
                'display': 'inline-block',
                'marginRight': '8px',
                'verticalAlign': 'middle'
            }),
            html.Span(region, style={
                'fontSize': '12px',
                'verticalAlign': 'middle',
                'color': 'rgb(27, 54, 93)',
                'fontFamily': 'Lato, sans-serif'
            })
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'marginBottom': '6px'
        })
        for region in REGIONS
    ]
    
    return html.Div([
        html.Div([
            html.Div([
                dcc.Loading(
                    id="loading-chart",
                    type="default",
                    children=dcc.Graph(
                        id='projects-time-chart',
                        config={'displayModeBar': False}
                    )
                )
            ], style={'width': '75%', 'display': 'inline-block', 'verticalAlign': 'top'}),
            
            html.Div([
                html.Div([
                    html.H4("Region", style={'marginBottom': '10px', 'fontSize': '14px', 'fontWeight': 'bold', 'fontFamily': 'Lato, sans-serif','color': 'rgb(27, 54, 93)'}),
                    html.Div(region_legend_items)
                ], style={'marginBottom': '30px'}),
                
                html.Div([
                    html.H4("Likely To Go Ahead", style={'marginBottom': '10px', 'fontSize': '14px', 'fontWeight': 'bold', 'fontFamily': 'Lato, sans-serif','color': 'rgb(27, 54, 93)'  }),
                    dcc.Checklist(
                        id='likely-filter',
                        options=[
                            {'label': '(All)', 'value': 'All'},
                            {'label': 'N', 'value': 'N'},
                            {'label': 'Uncertain', 'value': 'Uncertain'},
                            {'label': 'Y', 'value': 'Y'},
                            {'label': ' ', 'value': ''}
                        ],
                        value=['Y'],
                        style={'fontSize': '12px', 'fontFamily': 'Lato, sans-serif'},
                        inputStyle={'marginRight': '5px', 'marginLeft': '5px'},
                        labelStyle={'color': 'rgb(27, 54, 93)', 'fontFamily': 'Lato, sans-serif'}
                    ),
                    dcc.Store(id='likely-filter-previous', data=['Y'])
                ])
            ], style={
                'width': '25%',
                'display': 'inline-block',
                'verticalAlign': 'top',
                'paddingLeft': '20px',
                'paddingTop': '60px'
            })
        ], style={'display': 'flex', 'marginBottom': '20px'}),
        
        html.Div([
            html.P(
                "Select a Region from the chart above to filter the below table",
                style={
                    'fontSize': '14px',
                    'fontWeight': '500',
                    'marginBottom': '15px',
                    'marginTop': '20px',
                    'fontFamily': 'Lato, sans-serif'
                }
            )
        ]),
        
        html.Div([
            html.H4("Project Details", style={'marginBottom': '15px', 'fontSize': '16px', 'fontWeight': 'bold', 'fontFamily': 'Lato, sans-serif', 'color': '#fe5000', 'textAlign': 'left'}),
            dcc.Loading(
                id="loading-table",
                type="default",
                children=dash_table.DataTable(
                    id='projects-time-table',
                    style_table={
                        'overflowX': 'auto',
                        'overflowY': 'auto',
                        'maxHeight': '600px',
                        'border': '1px solid #ddd'
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '8px',
                        'fontSize': '12px',
                        'fontFamily': 'Lato, sans-serif',
                        'color': 'rgb(27, 54, 93)',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'overflow': 'hidden',
                        'textOverflow': 'ellipsis'
                    },
                    style_cell_conditional=[
                        {
                            'if': {'column_id': 'Comments'},
                            'whiteSpace': 'nowrap',
                            'overflow': 'hidden',
                            'textOverflow': 'ellipsis',
                            'height': 'auto',
                            'textAlign': 'left'
                        }
                    ],
                    style_header={
                        'backgroundColor': '#f8f9fa',
                        'fontWeight': 'bold',
                        'fontFamily': 'Lato, sans-serif',
                        'color': 'rgb(27, 54, 93)',
                        'border': '1px solid #ddd',
                        'textAlign': 'center'
                    },
                    style_data={
                        'border': '1px solid #ddd',
                        'whiteSpace': 'normal',
                        'fontFamily': 'Lato, sans-serif',
                        'color': 'rgb(27, 54, 93)'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f9f9f9'
                        }
                    ],
                    sort_action='native',
                    filter_action='native',
                    tooltip_duration=None,
                    css=[{
                        'selector': '.dash-table-tooltip',
                        'rule': 'font-size: 10px !important; font-family: Lato, sans-serif !important; color: rgb(27, 54, 93) !important; max-width: 400px !important; white-space: normal !important; word-wrap: break-word !important; line-height: 1.4 !important; padding: 6px 8px !important;'
                    }, {
                        'selector': '.dash-table-container .row:last-child',
                        'rule': 'display: none !important;'
                    }, {
                        'selector': '.previous-page, .next-page, .first-page, .last-page, .page-number, .page-number--current',
                        'rule': 'display: none !important;'
                    }]
                )
            )
        ], style={'marginTop': '20px'})
    ], className='tab-content', style={'padding': '20px', 'backgroundColor': '#ffffff'})


def register_callbacks(dash_app, server):    
    @callback(
        [Output('likely-filter', 'value'),
         Output('likely-filter-previous', 'data')],
        Input('likely-filter', 'value'),
        State('likely-filter-previous', 'data'),
        prevent_initial_call=False
    )
    def manage_all_checkbox(selected_values, previous_values):
        if selected_values is None:
            return [], []
        
        if not isinstance(selected_values, list):
            selected_values = [selected_values] if selected_values else []
        
        all_options = ['All', 'N', 'Uncertain', 'Y', '']
        individual_options = ['N', 'Uncertain', 'Y', '']
        if previous_values is None:
            previous_values = []
        if not isinstance(previous_values, list):
            previous_values = [previous_values] if previous_values else []
        
        was_all_selected = 'All' in previous_values
        is_all_selected = 'All' in selected_values
        prev_individual = [opt for opt in previous_values if opt in individual_options]
        curr_individual = [opt for opt in selected_values if opt in individual_options]
        
        if not was_all_selected and is_all_selected:
            return all_options, all_options
        
        if was_all_selected and not is_all_selected:
            return [], []
        
        if was_all_selected and is_all_selected and prev_individual != curr_individual:
            if len(curr_individual) < len(prev_individual):
                return curr_individual, curr_individual
            elif len(curr_individual) == len(individual_options):
                return all_options, all_options
        
        if is_all_selected:
            return all_options, all_options
        
        selected_individual = [opt for opt in selected_values if opt in individual_options]
        
        if len(selected_individual) == len(individual_options):
            return all_options, all_options
        
        final_return_values = selected_individual if len(selected_individual) > 0 else (all_options if is_all_selected else [])
        return final_return_values, final_return_values
    
    @callback(
        Output('projects-time-chart', 'figure'),
        [Input('current-submenu', 'data'),
         Input('likely-filter', 'value')]
    )
    def update_chart(submenu, likely_filter):
        """Update projects by time chart"""
        if submenu != 'projects-time':
            return go.Figure()
        
        df = load_chart_data()
        
        if df.empty:
            return go.Figure()
        
        likely_col = 'likely_goahead'
        
        if likely_col in df.columns:
            df[likely_col] = df[likely_col].astype(str).str.strip()
            col_upper = df[likely_col].str.upper()

            if not likely_filter:
                likely_filter = []
            if not isinstance(likely_filter, list):
                likely_filter = [likely_filter] if likely_filter else []

            valid_statuses = ['Y', 'N', 'UNCERTAIN', '']
            has_all = 'All' in likely_filter

            if has_all:
                selected_statuses = valid_statuses
            else:
                selected_statuses = []
                for v in likely_filter:
                    v_up = str(v).upper()
                    if v_up in ['Y', 'N'] or v_up.startswith('UNCERT'):
                        selected_statuses.append(v_up)
                    elif v == '':
                        selected_statuses.append('')

            if not selected_statuses:
                df = pd.DataFrame()
            else:
                mask = pd.Series(False, index=col_upper.index)
                for status in selected_statuses:
                    if status == 'Y':
                        mask |= col_upper.str.startswith('Y')
                    elif status == 'N':
                        mask |= col_upper.str.startswith('N')
                    elif status.startswith('UNCERT'):
                        mask |= col_upper.str.startswith('U')
                    elif status == '':
                        # Blank category: likely_goahead empty after normalization
                        mask |= (col_upper == '')

                before_count = len(df)
                df = df[mask].copy()
                after_count = len(df)

                if not df.empty:
                    df = df.groupby(
                        ['Region', 'Year', 'Quarter', 'QuarterNum'],
                        as_index=False
                    )['Value'].sum()
                   
        if df.empty:
            fig = go.Figure()
            if not likely_filter or (isinstance(likely_filter, list) and len(likely_filter) == 0):
                text_message = "No data selected. Please select at least one option from 'Likely To Go Ahead' filter."
            else:
                text_message = "No data available for selected filters."
            
            fig.add_annotation(
                text=text_message,
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font={'size': 14, 'family': 'Lato', 'color': 'rgb(27, 54, 93)'}
            )
            fig.update_layout(
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white',
                title={
                    'text': "Projected Oil Capacity additions by Quarter ('000 b/d)",
                    'x': 0,
                    'xanchor': 'left',
                    'font': {'size': 18, 'family': 'Lato', 'color': '#fe5000'}
                }
            )
            return fig
        
        quarters = []
        x_tick_labels = []
        for year in range(2025, 2030):
            for q in ['Q1', 'Q2', 'Q3', 'Q4']:
                quarters.append(f'{year}_{q}')
                x_tick_labels.append(q)
        
        fig = go.Figure()
        
        for region in reversed(REGIONS):
            region_data = df[df['Region'] == region]
            if not region_data.empty:
                region_data = region_data.sort_values(['Year', 'QuarterNum'])
                values = region_data['Value'].tolist()
                while len(values) < 20:
                    values.append(0)
                
                fig.add_trace(go.Bar(
                    name=region,
                    x=quarters,
                    y=values,
                    marker=dict(
                        color=REGION_COLORS.get(region, 'rgb(128, 128, 128)'),
                        line=dict(width=0)
                    ),
                    hovertemplate=(
                        '<span style="color:grey">Region:</span> <span style="color:black">%{fullData.name}</span><br>' +
                        '<span style="color:grey">Period:</span> <span style="color:black">%{customdata}</span><br>' +
                        '<span style="color:grey">Oil Capacity Additions(\'000 b/d):</span> <span style="color:black">%{y:,.0f}</span><extra></extra>'
                    ),
                    customdata=[f"{q.split('_')[1]} {q.split('_')[0]}" for q in quarters]
                ))
        
        annotations = []
        year_positions = {}
        for i, quarter in enumerate(quarters):
            year = int(quarter.split('_')[0])
            if year not in year_positions:
                year_positions[year] = []
            year_positions[year].append(i)
        
        shapes = []
        for i in range(21):
            is_year_boundary = (i > 0 and i % 4 == 0)
            if is_year_boundary:
                shapes.append({
                    'type': 'line',
                    'xref': 'x',
                    'yref': 'paper',
                    'x0': i - 0.5,
                    'y0': 0,
                    'x1': i - 0.5,
                    'y1': 1,
                    'line': {
                        'color': '#b0b0b0',
                        'width': 1.5
                    },
                    'layer': 'below'
                })
        
        sorted_years = sorted(year_positions.keys())
        for year in sorted_years:
            positions = year_positions[year]
            x_pos = (positions[0] + positions[-1]) / 2
            annotations.append({
                'x': x_pos,
                'y': 1.02,
                'xref': 'x',
                'yref': 'paper',
                'text': str(year),
                'showarrow': False,
                'font': {'size': 13, 'color': 'rgb(27, 54, 93)', 'family': 'Lato'},
                'xanchor': 'center',
                'yanchor': 'bottom'
            })
        
        fig.update_layout(
            title={
                'text': "Projected Oil Capacity additions by Quarter ('000 b/d)",
                'x': 0,
                'xanchor': 'left',
                'font': {'size': 16, 'color': '#fe5000', 'family': 'Lato'},
                'y': 0.98
            },
            xaxis={
                'title': '',
                'showgrid': False,
                'tickmode': 'array',
                'tickvals': list(range(20)),
                'ticktext': x_tick_labels,
                'tickangle': 0,
                'showline': True,
                'linecolor': '#ccc',
                'tickfont': {'color': 'rgb(27, 54, 93)', 'size': 12, 'family': 'Lato'}
            },
            yaxis={
                'title': "'000 b/d",
                'titlefont': {'color': 'rgb(27, 54, 93)', 'size': 12, 'family': 'Lato'},
                'showgrid': True,
                'gridcolor': '#e0e0e0',
                'range': [0, 1300],
                'tickmode': 'linear',
                'tick0': 0,
                'dtick': 200,
                'showline': True,
                'linecolor': '#ccc',
                'tickfont': {'color': 'rgb(27, 54, 93)', 'size': 12, 'family': 'Lato'}
            },
            barmode='stack',
            height=500,
            plot_bgcolor='white',
            paper_bgcolor='white',
            hovermode='closest',
            hoverlabel=dict(
                bgcolor='white',
                bordercolor='#ccc',
                font_size=12
            ),
            showlegend=False,
            margin=dict(l=60, r=50, t=80, b=60),
            annotations=annotations,
            shapes=shapes
        )
        
        return fig
    
    @callback(
        [Output('projects-time-table', 'data'),
         Output('projects-time-table', 'columns'),
         Output('projects-time-table', 'tooltip_data')],
        [Input('current-submenu', 'data'),
         Input('projects-time-chart', 'clickData'),
         Input('likely-filter', 'value')],
        [State('projects-time-chart', 'figure')],
        prevent_initial_call=False
    )
    def update_table(submenu, click_data, likely_filter, figure):
        """Update projects table"""
        try:
            if submenu != 'projects-time':
                return [], [], []
            df = load_table_data()
            if df.empty:
                return [], [], []
            
            clicked_region = None
            if click_data and isinstance(click_data, dict) and 'points' in click_data and len(click_data['points']) > 0:
                point = click_data['points'][0]
                if isinstance(point, dict):
                    if 'fullData' in point and 'name' in point['fullData']:
                        clicked_region = point['fullData']['name']
                    elif figure and isinstance(figure, dict) and 'data' in figure:
                        trace_index = point.get('curveNumber', 0)
                        if isinstance(trace_index, int) and trace_index < len(figure['data']):
                            trace_data = figure['data'][trace_index]
                            if isinstance(trace_data, dict) and 'name' in trace_data:
                                clicked_region = trace_data['name']
            
            if clicked_region and 'Region' in df.columns:
                df = df[df['Region'] == clicked_region].copy()
            
            likely_col = None
            for col in df.columns:
                col_lower = col.lower()
                if 'likely' in col_lower and ('go' in col_lower or 'ahead' in col_lower):
                    likely_col = col
                    break
            
            if likely_col:
                df[likely_col] = df[likely_col].astype(str).str.strip()
                col_upper = df[likely_col].str.upper()

                if not likely_filter:
                    likely_filter = []
                if not isinstance(likely_filter, list):
                    likely_filter = [likely_filter] if likely_filter else []

                if 'All' not in likely_filter and len(likely_filter) > 0:
                    mask = pd.Series(False, index=col_upper.index)
                    for v in likely_filter:
                        v_up = str(v).upper()
                        if v_up == 'Y':
                            mask |= col_upper.str.startswith('Y')
                        elif v_up == 'N':
                            mask |= col_upper.str.startswith('N')
                        elif v_up.startswith('UNCERT'):
                            mask |= col_upper.str.startswith('U')
                        else:
                            mask |= (col_upper == v_up)

                    before_count = len(df)
                    df = df[mask].copy()
                    after_count = len(df)
                elif 'All' not in likely_filter and len(likely_filter) == 0:
                    df = pd.DataFrame()
        
            display_cols = [
                'Project Name',
                'likely_goahead',
                'Country',
                'Region',
                'Opec_group',
                'field_type',
                'field',
                'play_type',
                'Hydrocarbon',
                'Associated Crude',
                'Depth',
                'Operator',
                'Partner1',
                'Partner2',
                'Partner3',
                'Partner4',
                'Partner5',
                'First Oil Year',
                'Sanctioned',
                'Comments',
                'Project Status',
                'Gas Reserves (mmboe)',
                'Liquids Reserves (mmbbl)',
                'Total Reserves (mmboe)',
                'API',
                'Sulfur',
                'Operator Share %',
                'Partner1 Share %',
                'Partner2 Share %',
                'Partner3 Share %',
                'Partner4 Share %',
                'Partner5 Share %',
                # Quarter columns - 2024 to 2029
                '2024_Q1', '2024_Q2', '2024_Q3', '2024_Q4',
                '2025_Q1', '2025_Q2', '2025_Q3', '2025_Q4',
                '2026_Q1', '2026_Q2', '2026_Q3', '2026_Q4',
                '2027_Q1', '2027_Q2', '2027_Q3', '2027_Q4',
                '2028_Q1', '2028_Q2', '2028_Q3', '2028_Q4',
                '2029_Q1', '2029_Q2', '2029_Q3', '2029_Q4'
            ]
            
            available_cols = [col for col in display_cols if col in df.columns]
            
            if not available_cols:
                return [], [], []
            
            df = df[available_cols].copy()
            
            numeric_cols = ['Gas Reserves (mmboe)', 'Liquids Reserves (mmbbl)', 'Total Reserves (mmboe)']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    df[col] = df[col].apply(lambda x: f'{x:,.3f}' if pd.notna(x) and x != 0 else '')
            
            bool_display_map = {
                'Y': 'Yes',
                'N': 'No',
                'true': 'Yes',
                'false': 'No',
                'True': 'Yes',
                'False': 'No'
            }
            
            bool_columns = ['likely_goahead', 'Sanctioned']
            for col in bool_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip().map(bool_display_map).fillna(df[col])
            
            if 'Comments' in df.columns:
                original_comments = df['Comments'].copy()
                df['Comments'] = df['Comments'].astype(str).apply(
                    lambda x: (x[:10] + '...') if len(x) > 10 else x
                )
            else:
                original_comments = pd.Series([''] * len(df))
            
            column_widths = {
                'Project Name': '180px',
                'likely_goahead': '100px',
                'Country': '120px',
                'Region': '120px',
                'Opec_group': '140px',
                'field_type': '100px',
                'field': '150px',
                'play_type': '120px',
                'Hydrocarbon': '120px',
                'Associated Crude': '140px',
                'Depth': '80px',
                'Operator': '120px',
                'Partner1': '100px',
                'Partner2': '100px',
                'Partner3': '100px',
                'Partner4': '100px',
                'Partner5': '100px',
                'First Oil Year': '100px',
                'Sanctioned': '80px',
                'Comments': '120px',
                'Project Status': '120px',
                'Gas Reserves (mmboe)': '140px',
                'Liquids Reserves (mmbbl)': '150px',
                'Total Reserves (mmboe)': '150px',
                'API': '80px',
                'Sulfur': '80px'
            }
            
            display_name_map = {
                'Opec_group': 'Group',
                'field_type': 'Field Type',
                'field': 'Field/Block',
                'play_type': 'Play Type',
                'likely_goahead': 'Likely To Go Ahead',
            }
            
            columns = []
            for col in available_cols:
                display_name = display_name_map.get(col, col)
                col_def = {'name': display_name, 'id': col}
                if col in column_widths:
                    col_def['minWidth'] = column_widths[col]
                    col_def['maxWidth'] = column_widths[col]
                columns.append(col_def)
            
            df = df.fillna('')
            data = df.to_dict('records')
            tooltip_data = []
            for i, row in enumerate(data):
                tooltip_row = {}
                if 'Comments' in row:
                    original_comment = str(original_comments.iloc[i]) if i < len(original_comments) else ''
                    if original_comment and original_comment != 'nan' and original_comment.strip():
                        tooltip_row['Comments'] = {
                            'value': original_comment,
                            'type': 'text'
                        }
                tooltip_data.append(tooltip_row)
            
            return data, columns, tooltip_data
        except Exception as e:
            traceback.print_exc()
            return [], [], []
