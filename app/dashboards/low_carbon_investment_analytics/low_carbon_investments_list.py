"""
List of Tracked Investments
Comprehensive list of tracked low-carbon investments
"""
from dash import dcc, html, Input, Output, State, dash_table, callback, ALL
import dash
import pandas as pd
from core.data_helpers import execute_query


def load_investments_data(filters=None):
    """Load investments data from database with optional filters"""
    
    # Base query matching the provided SQL
    query = """
    SELECT
        a.asset_name AS "Asset Name",
        b.company_name AS "Company",
        b.peer_group_simple AS "Peer Group",
        c.country_long_name AS "Asset Country",
        c.et_region AS "Region",
        a.investment_type AS "Investment Type",
        EXTRACT(YEAR FROM a.date_announced) AS "Year Announced",
        a.project_category_1 AS "Project Category",
        a.project_category_2 AS "Project Category 2",
        a.project_category_3 AS "Project Category 3",
        a.new_status AS "Status",
        a.investment_usd AS "Investment ($ Million)",
        a.confidence_level_simple AS "Investment Value Source",
        a.reference AS "Reference"
    FROM dev.fact_et_assets a
    LEFT JOIN dev.dim_company b
        ON a.company_id = b.company_id
    LEFT JOIN dev.dim_country c
        ON a.country_id = c.dim_country_id
    WHERE a.new_status <> 'Uncertain'
    """
    
    # Add filters if provided
    params = {}
    if filters:
        if filters.get('asset_name'):
            query += " AND LOWER(a.asset_name) LIKE LOWER(:asset_name)"
            params['asset_name'] = f"%{filters['asset_name']}%"
        
        if filters.get('peer_group') and filters['peer_group'] != 'All':
            query += " AND b.peer_group_simple = :peer_group"
            params['peer_group'] = filters['peer_group']
        
        if filters.get('year_announced') and filters['year_announced'] != 'All':
            query += " AND EXTRACT(YEAR FROM a.date_announced) = :year_announced"
            params['year_announced'] = int(filters['year_announced'])
        
        if filters.get('company') and filters['company'] != 'All':
            query += " AND b.company_name = :company"
            params['company'] = filters['company']
        
        if filters.get('investment_type') and filters['investment_type'] != 'All':
            query += " AND a.investment_type = :investment_type"
            params['investment_type'] = filters['investment_type']
        
        if filters.get('status') and filters['status']:
            if isinstance(filters['status'], list) and len(filters['status']) > 0:
                placeholders = ','.join([f":status_{i}" for i in range(len(filters['status']))])
                query += f" AND a.new_status IN ({placeholders})"
                for i, status in enumerate(filters['status']):
                    params[f'status_{i}'] = status
        
        if filters.get('country') and filters['country'] != 'All':
            query += " AND c.country_long_name = :country"
            params['country'] = filters['country']
        
        if filters.get('project_category') and filters['project_category']:
            if isinstance(filters['project_category'], list):
                if len(filters['project_category']) > 0:
                    placeholders = ','.join([f":category_{i}" for i in range(len(filters['project_category']))])
                    query += f" AND a.project_category_1 IN ({placeholders})"
                    for i, cat in enumerate(filters['project_category']):
                        params[f'category_{i}'] = cat
            else:
                query += " AND a.project_category_1 = :project_category"
                params['project_category'] = filters['project_category']
        
        if filters.get('region') and filters['region']:
            if isinstance(filters['region'], list) and len(filters['region']) > 0:
                placeholders = ','.join([f":region_{i}" for i in range(len(filters['region']))])
                query += f" AND c.et_region IN ({placeholders})"
                for i, region in enumerate(filters['region']):
                    params[f'region_{i}'] = region
        
        if filters.get('project_category_2') and filters['project_category_2']:
            if isinstance(filters['project_category_2'], list) and len(filters['project_category_2']) > 0:
                placeholders = ','.join([f":category2_{i}" for i in range(len(filters['project_category_2']))])
                query += f" AND a.project_category_2 IN ({placeholders})"
                for i, cat2 in enumerate(filters['project_category_2']):
                    params[f'category2_{i}'] = cat2
    
    query += " ORDER BY a.asset_name"
    
    try:
        results = execute_query(query, params if params else None)
        return pd.DataFrame(results) if results else pd.DataFrame()
    except Exception as e:
        print(f"Error loading investments data: {e}")
        return pd.DataFrame()


def load_investment_summary():
    """Load investment count summary by project category"""
    try:
        query = """
        SELECT
            a.project_category_1 AS category,
            COUNT(*) AS investment_count,
            COALESCE(SUM(a.investment_usd), 0) AS total_investment
        FROM dev.fact_et_assets a
        WHERE a.new_status <> 'Uncertain'
            AND a.project_category_1 IS NOT NULL
        GROUP BY a.project_category_1
        ORDER BY COUNT(*) DESC
        """
        
        results = execute_query(query)
        
        # Also get total counts
        total_query = """
        SELECT
            COUNT(*) AS total_count,
            COALESCE(SUM(investment_usd), 0) AS total_investment
        FROM dev.fact_et_assets
        WHERE new_status <> 'Uncertain'
        """
        total_results = execute_query(total_query)
        
        summary = {}
        if results:
            for row in results:
                summary[row['category']] = {
                    'count': row['investment_count'],
                    'investment': row['total_investment']
                }
        
        if total_results and len(total_results) > 0:
            summary['total_count'] = total_results[0]['total_count']
            summary['total_investment'] = total_results[0]['total_investment']
        else:
            summary['total_count'] = 0
            summary['total_investment'] = 0
            
        return summary
    except Exception as e:
        print(f"Error loading investment summary: {e}")
        return {}


def load_filter_options(filters=None):
    """Load unique values for all filter dropdowns based on currently applied filters"""
    try:
        # helper to build where clause for dynamic filter options
        def get_where_clause(exclude_field=None):
            where_parts = ["a.new_status <> 'Uncertain'"]
            params = {}
            if filters:
                if filters.get('asset_name') and exclude_field != 'asset_name':
                    where_parts.append("LOWER(a.asset_name) LIKE LOWER(:asset_name)")
                    params['asset_name'] = f"%{filters['asset_name']}%"
                if filters.get('peer_group') and filters['peer_group'] != 'All' and exclude_field != 'peer_group':
                    where_parts.append("b.peer_group_simple = :peer_group")
                    params['peer_group'] = filters['peer_group']
                if filters.get('year_announced') and filters['year_announced'] != 'All' and exclude_field != 'year_announced':
                    where_parts.append("EXTRACT(YEAR FROM a.date_announced) = :year_announced")
                    params['year_announced'] = int(filters['year_announced'])
                if filters.get('company') and filters['company'] != 'All' and exclude_field != 'company':
                    where_parts.append("b.company_name = :company")
                    params['company'] = filters['company']
                if filters.get('investment_type') and filters['investment_type'] != 'All' and exclude_field != 'investment_type':
                    where_parts.append("a.investment_type = :investment_type")
                    params['investment_type'] = filters['investment_type']
                if filters.get('status') and exclude_field != 'status':
                    if isinstance(filters['status'], list) and len(filters['status']) > 0:
                        placeholders = ','.join([f":status_{i}" for i in range(len(filters['status']))])
                        where_parts.append(f"a.new_status IN ({placeholders})")
                        for i, status in enumerate(filters['status']):
                            params[f'status_{i}'] = status
                if filters.get('country') and filters['country'] != 'All' and exclude_field != 'country':
                    where_parts.append("c.country_long_name = :country")
                    params['country'] = filters['country']
                if filters.get('project_category') and filters['project_category'] != 'All' and exclude_field != 'project_category':
                    where_parts.append("a.project_category_1 = :project_category")
                    params['project_category'] = filters['project_category']
                if filters.get('region') and exclude_field != 'region':
                    if isinstance(filters['region'], list) and len(filters['region']) > 0:
                        placeholders = ','.join([f":region_{i}" for i in range(len(filters['region']))])
                        where_parts.append(f"c.et_region IN ({placeholders})")
                        for i, region in enumerate(filters['region']):
                            params[f'region_{i}'] = region
                if filters.get('project_category_2') and exclude_field != 'project_category_2':
                    if isinstance(filters['project_category_2'], list) and len(filters['project_category_2']) > 0:
                        placeholders = ','.join([f":category2_{i}" for i in range(len(filters['project_category_2']))])
                        where_parts.append(f"a.project_category_2 IN ({placeholders})")
                        for i, cat2 in enumerate(filters['project_category_2']):
                            params[f'category2_{i}'] = cat2
            
            return " AND ".join(where_parts), params

        # Get peer groups
        where, params = get_where_clause('peer_group')
        peer_groups = execute_query(f"""
            SELECT DISTINCT b.peer_group_simple 
            FROM dev.fact_et_assets a
            JOIN dev.dim_company b ON a.company_id = b.company_id
            WHERE {where} AND b.peer_group_simple IS NOT NULL 
            ORDER BY b.peer_group_simple
        """, params)
        
        # Get years
        where, params = get_where_clause('year_announced')
        years = execute_query(f"""
            SELECT DISTINCT EXTRACT(YEAR FROM a.date_announced) as year
            FROM dev.fact_et_assets a
            WHERE {where} AND a.date_announced IS NOT NULL
            ORDER BY year DESC
        """, params)
        
        # Get companies
        where, params = get_where_clause('company')
        companies = execute_query(f"""
            SELECT DISTINCT b.company_name
            FROM dev.fact_et_assets a
            JOIN dev.dim_company b ON a.company_id = b.company_id
            WHERE {where} AND b.company_name IS NOT NULL
            ORDER BY b.company_name
        """, params)
        
        # Get investment types
        where, params = get_where_clause('investment_type')
        investment_types = execute_query(f"""
            SELECT DISTINCT a.investment_type
            FROM dev.fact_et_assets a
            WHERE {where} AND a.investment_type IS NOT NULL
            ORDER BY a.investment_type
        """, params)
        
        # Get statuses
        where, params = get_where_clause('status')
        statuses = execute_query(f"""
            SELECT DISTINCT a.new_status
            FROM dev.fact_et_assets a
            WHERE {where} AND a.new_status IS NOT NULL
            ORDER BY a.new_status
        """, params)
        
        # Get countries
        where, params = get_where_clause('country')
        countries = execute_query(f"""
            SELECT DISTINCT c.country_long_name
            FROM dev.fact_et_assets a
            JOIN dev.dim_country c ON a.country_id = c.dim_country_id
            WHERE {where} AND c.country_long_name IS NOT NULL
            ORDER BY c.country_long_name
        """, params)
        
        # Get project categories
        where, params = get_where_clause('project_category')
        categories = execute_query(f"""
            SELECT DISTINCT a.project_category_1
            FROM dev.fact_et_assets a
            WHERE {where} AND a.project_category_1 IS NOT NULL
            ORDER BY a.project_category_1
        """, params)
        
        # Get regions
        where, params = get_where_clause('region')
        regions = execute_query(f"""
            SELECT DISTINCT c.et_region
            FROM dev.fact_et_assets a
            JOIN dev.dim_country c ON a.country_id = c.dim_country_id
            WHERE {where} AND c.et_region IS NOT NULL
            ORDER BY c.et_region
        """, params)
        
        # Get project category 2
        where, params = get_where_clause('project_category_2')
        categories_2 = execute_query(f"""
            SELECT DISTINCT a.project_category_2
            FROM dev.fact_et_assets a
            WHERE {where} AND a.project_category_2 IS NOT NULL
            ORDER BY a.project_category_2
        """, params)
        
        return {
            'peer_groups': [{'label': 'All', 'value': 'All'}] + [{'label': r['peer_group_simple'], 'value': r['peer_group_simple']} for r in (peer_groups or [])],
            'years': [{'label': 'All', 'value': 'All'}] + [{'label': str(int(r['year'])), 'value': int(r['year'])} for r in (years or [])],
            'companies': [{'label': 'All', 'value': 'All'}] + [{'label': r['company_name'], 'value': r['company_name']} for r in (companies or [])],
            'investment_types': [{'label': 'All', 'value': 'All'}] + [{'label': r['investment_type'], 'value': r['investment_type']} for r in (investment_types or [])],
            'statuses': [{'label': r['new_status'], 'value': r['new_status']} for r in (statuses or [])],
            'countries': [{'label': 'All', 'value': 'All'}] + [{'label': r['country_long_name'], 'value': r['country_long_name']} for r in (countries or [])],
            'categories': [{'label': 'All', 'value': 'All'}] + [{'label': r['project_category_1'], 'value': r['project_category_1']} for r in (categories or [])],
            'regions': [{'label': 'All', 'value': 'All'}] + [{'label': r['et_region'], 'value': r['et_region']} for r in (regions or [])],
            'categories_2': [{'label': 'All', 'value': 'All'}] + [{'label': r['project_category_2'], 'value': r['project_category_2']} for r in (categories_2 or [])]
        }
    except Exception as e:
        print(f"Error loading filter options: {e}")
        return {
            'peer_groups': [{'label': 'All', 'value': 'All'}],
            'years': [{'label': 'All', 'value': 'All'}],
            'companies': [{'label': 'All', 'value': 'All'}],
            'investment_types': [{'label': 'All', 'value': 'All'}],
            'statuses': [],
            'countries': [{'label': 'All', 'value': 'All'}],
            'categories': [{'label': 'All', 'value': 'All'}],
            'regions': [{'label': 'All', 'value': 'All'}],
            'categories_2': [{'label': 'All', 'value': 'All'}]
        }


def create_layout():
    """Create the Tracked Investments List layout"""
    
    # Load filter options
    filter_opts = load_filter_options()
    
    # Load initial data
    df = load_investments_data()
    
    return html.Div([
        # Download component for Export to CSV
        dcc.Download(id='download-investments-csv'),
        
        # Main Container (Flex) - Splits into Main Content (Left) and Sidebar (Right)
        html.Div([
            
            # Left Column: Main Content (Summary Boxes & Table)
            html.Div([
                # Investment Count Summary Section (Dynamic)
                html.Div([
                    html.H4("Investment Count by Company - All", id='lc-inv-summary-title', style={
                        'color': '#f45d2d',
                        'fontSize': '24px',
                        'fontWeight': 'normal',
                        'marginBottom': '20px',
                        'fontFamily': 'Georgia, serif'
                    }),
                    html.Div(id='lc-inv-summary-boxes', children=[])
                ], style={'padding': '10px 0 10px 0'}),
                
                # Data Table Area
                html.Div([
                    # Table Header with Title
                    html.Div([
                        html.Div(style={'flex': '1'}),
                        html.Button(
                            'Export to CSV',
                            id='btn-export-table',
                            n_clicks=0,
                            style={
                                'backgroundColor': 'white', 'color': '#2c3e50', 'border': '1px solid #dee2e6',
                                'padding': '5px 15px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '13px'
                            }
                        )
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'width': '100%', 'marginBottom': '20px'}),
                    
                    dcc.Loading(
                        id="loading-table",
                        type="circle",
                        color="#f45d2d",
                        children=[
                            html.Div(id='lc-inv-link-dummy', style={'display': 'none'}),
                            dash_table.DataTable(
                            id='lc-inv-table',
                            columns=[
                                {'name': 'Asset Name', 'id': 'Asset Name'},
                                {'name': 'Company', 'id': 'Company'},
                                {'name': 'Peer Group', 'id': 'Peer Group'},
                                {'name': 'Asset Country', 'id': 'Asset Country'},
                                {'name': 'Region', 'id': 'Region'},
                                {'name': 'Investment Type', 'id': 'Investment Type'},
                                {'name': 'Year Announced', 'id': 'Year Announced'},
                                {'name': 'Project Category', 'id': 'Project Category'},
                                {'name': 'Project Category 2', 'id': 'Project Category 2'},
                                {'name': 'Status', 'id': 'Status'},
                                {'name': 'Investment ($ Million)', 'id': 'Investment ($ Million)'},
                                {'name': 'Investment Value Source', 'id': 'Investment Value Source'},
                                {'name': 'Reference', 'id': 'Reference'}
                            ],
                            data=[],
                            page_action='none',
                            virtualization=True,
                            merge_duplicate_headers=True,
                            fixed_rows={'headers': True},
                            fixed_columns={'headers': True, 'data': 2},
                            style_table={
                                'minWidth': '100%',
                                'height': '600px',
                                'overflowY': 'auto',
                                'overflowX': 'auto',
                                'border': '1px solid #ddd'
                            },
                            style_header={
                                'backgroundColor': '#ffffff',
                                'fontWeight': 'bold',
                                'textAlign': 'left',
                                'fontSize': '11px',
                                'border': 'none',
                                'color': '#333',
                                'height': '25px',
                                'padding': '2px',
                                'fontFamily': 'Arial, sans-serif'
                            },
                            style_cell={
                                'padding': '0px 10px',
                                'fontSize': '11px',
                                'fontFamily': 'Arial, sans-serif',
                                'border': 'none',
                                'minWidth': '70px',
                                'backgroundColor': '#fff',
                                'color': '#555',
                                'height': 'auto',
                                'whiteSpace': 'normal',
                                'overflow': 'hidden',
                                'textOverflow': 'ellipsis',
                                'cursor': 'pointer'
                            },
                            style_as_list_view=False,
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': '#f2f2f2'
                                },
                                {
                                    'if': {'column_id': 'Asset Name'},
                                    'textAlign': 'left',
                                    'fontWeight': 'bold',
                                    'minWidth': '150px',
                                    'color': '#333',
                                    'paddingLeft': '5px'
                                },
                                {
                                    'if': {'column_id': 'Company'},
                                    'textAlign': 'left',
                                    'minWidth': '120px',
                                    'paddingLeft': '10px',
                                    'borderRight': '1px solid #ccc'
                                },
                                {
                                    'if': {'column_id': ['Peer Group', 'Asset Country', 'Region', 
                                                          'Investment Type', 'Project Category', 'Project Category 2', 
                                                          'Project Category 3', 'Status', 'Investment Value Source', 'Reference']},
                                    'textAlign': 'left',
                                    'paddingLeft': '5px'
                                }
                            ]
                        )
                    ]),
                    
                    # Source attribution
                    html.Div([
                        html.P("Source: Energy Intelligence, Low Carbon Investment Tracker. Data as of Q4 2025.", 
                               style={
                                   'fontSize': '11px',
                                   'color': '#999',
                                   'fontStyle': 'italic',
                                   'marginTop': '10px',
                                   'marginBottom': '0px',
                                   'fontFamily': 'Arial, sans-serif'
                               }),
                        html.P("Confidentiality by leading oil and gas firms. Financed by value initially demonstrates approval. Reported or estimated values are for companies tracked. For more information see methodology.", 
                               style={
                                   'fontSize': '11px',
                                   'color': '#999',
                                   'fontStyle': 'italic',
                                   'marginTop': '5px',
                                   'marginBottom': '0px',
                                   'fontFamily': 'Arial, sans-serif'
                               })
                    ], style={'marginTop': '10px'})
                ], style={'padding': '20px 0 20px 0', 'backgroundColor': '#ffffff', 'fontFamily': 'Arial, sans-serif'})
            ], style={'flex': '1', 'minWidth': '0', 'padding': '0 20px'}),

            # Right Column: Sidebar (Filters)
            html.Div([
                # Filters Title (Hidden or subtle as per image)
                
                # Search Asset Name
                html.Div([
                    html.Label("Search Asset Name", style={
                        'fontSize': '11px',
                        'color': '#666',
                        'marginBottom': '4px',
                        'display': 'block',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    dcc.Input(
                        id='lc-inv-asset-search',
                        type='text',
                        placeholder='',
                        style={
                            'width': '100%',
                            'padding': '5px 8px',
                            'border': '1px solid #ccc',
                            'borderRadius': '3px',
                            'fontSize': '12px',
                            'fontFamily': 'Arial, sans-serif'
                        }
                    )
                ], style={'marginBottom': '15px'}),
                
                # Peer Group
                html.Div([
                    html.Label("Peer Group", style={
                        'fontSize': '11px',
                        'color': '#666',
                        'marginBottom': '4px',
                        'display': 'block',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    dcc.Dropdown(
                        id='lc-inv-peer-group',
                        options=filter_opts['peer_groups'],
                        value='All',
                        clearable=False,
                        style={'fontSize': '12px', 'fontFamily': 'Arial, sans-serif'}
                    )
                ], style={'marginBottom': '15px'}),
                
                # Year Announced
                html.Div([
                    html.Label("Year Announced", style={
                        'fontSize': '11px',
                        'color': '#666',
                        'marginBottom': '4px',
                        'display': 'block',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    dcc.Dropdown(
                        id='lc-inv-year',
                        options=filter_opts['years'],
                        value='All',
                        clearable=False,
                        style={'fontSize': '12px', 'fontFamily': 'Arial, sans-serif'}
                    )
                ], style={'marginBottom': '15px'}),
                
                # Company
                html.Div([
                    html.Label("Company", style={
                        'fontSize': '11px',
                        'color': '#666',
                        'marginBottom': '4px',
                        'display': 'block',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    dcc.Dropdown(
                        id='lc-inv-company',
                        options=filter_opts['companies'],
                        value='All',
                        clearable=False,
                        style={'fontSize': '12px', 'fontFamily': 'Arial, sans-serif'}
                    )
                ], style={'marginBottom': '15px'}),
                
                # Investment Type
                html.Div([
                    html.Label("Investment Type", style={
                        'fontSize': '11px',
                        'color': '#666',
                        'marginBottom': '4px',
                        'display': 'block',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    dcc.Dropdown(
                        id='lc-inv-type',
                        options=filter_opts['investment_types'],
                        value='All',
                        clearable=False,
                        style={'fontSize': '12px', 'fontFamily': 'Arial, sans-serif'}
                    )
                ], style={'marginBottom': '15px'}),
                
                # Status
                html.Div([
                    html.Label("Status", style={
                        'fontSize': '11px',
                        'color': '#666',
                        'marginBottom': '4px',
                        'display': 'block',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    html.Div([
                        dcc.Dropdown(
                            id='lc-inv-status-dropdown',
                            options=[{'label': '(Multiple values)', 'value': 'multiple'}],
                            value='multiple',
                            clearable=False,
                            style={'fontSize': '12px', 'fontFamily': 'Arial, sans-serif', 'marginBottom': '5px'}
                        ),
                    ], id='lc-inv-status-trigger', n_clicks=0, style={'cursor': 'pointer'}),
                    html.Div([
                        dcc.Checklist(
                            id='lc-inv-status',
                            options=filter_opts['statuses'],
                            value=['Completed', 'Proposed', 'Under Development'],
                            labelStyle={
                                'display': 'block',
                                'fontSize': '11px',
                                'color': '#333',
                                'fontFamily': 'Arial, sans-serif',
                                'marginBottom': '3px'
                            }
                        )
                    ], id='lc-inv-status-container', style={'display': 'none', 'paddingLeft': '10px', 'marginTop': '5px'})
                ], style={'marginBottom': '15px'}),
                
                # Asset Country
                html.Div([
                    html.Label("Asset Country", style={
                        'fontSize': '11px',
                        'color': '#666',
                        'marginBottom': '4px',
                        'display': 'block',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    dcc.Dropdown(
                        id='lc-inv-country',
                        options=filter_opts['countries'],
                        value='All',
                        clearable=False,
                        style={'fontSize': '12px', 'fontFamily': 'Arial, sans-serif'}
                    )
                ], style={'marginBottom': '15px'}),
                
                # Project Category
                html.Div([
                    html.Label("Project Category", style={
                        'fontSize': '11px',
                        'color': '#666',
                        'marginBottom': '4px',
                        'display': 'block',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    dcc.Dropdown(
                        id='lc-inv-category',
                        options=filter_opts['categories'],
                        value='All',
                        clearable=False,
                        style={'fontSize': '12px', 'fontFamily': 'Arial, sans-serif'}
                    )
                ], style={'marginBottom': '15px'}),
                
                # Region
                html.Div([
                    html.Label("Region", style={
                        'fontSize': '11px',
                        'color': '#666',
                        'marginBottom': '4px',
                        'display': 'block',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    html.Div([
                        dcc.Dropdown(
                            id='lc-inv-region-dropdown',
                            options=[{'label': '(All)', 'value': 'All'}],
                            value='All',
                            clearable=False,
                            style={'fontSize': '12px', 'fontFamily': 'Arial, sans-serif', 'marginBottom': '5px'}
                        ),
                    ], id='lc-inv-region-trigger', n_clicks=0, style={'cursor': 'pointer'}),
                    html.Div([
                        dcc.Checklist(
                            id='lc-inv-region',
                            options=[{'label': '(All)', 'value': 'All'}] + [opt for opt in filter_opts['regions'] if opt['value'] != 'All'],
                            value=[opt['value'] for opt in filter_opts['regions']],  # All checked by default
                            labelStyle={
                                'display': 'block',
                                'fontSize': '11px',
                                'color': '#333',
                                'fontFamily': 'Arial, sans-serif',
                                'marginBottom': '3px'
                            }
                        )
                    ], id='lc-inv-region-container', style={'display': 'none', 'paddingLeft': '10px', 'marginTop': '5px'})
                ], style={'marginBottom': '15px'}),
                
                # Project Category 2
                html.Div([
                    html.Label("Project Category 2", style={
                        'fontSize': '11px',
                        'color': '#666',
                        'marginBottom': '4px',
                        'display': 'block',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    html.Div([
                        dcc.Dropdown(
                            id='lc-inv-category-2-dropdown',
                            options=[{'label': '(All)', 'value': 'All'}],
                            value='All',
                            clearable=False,
                            style={'fontSize': '12px', 'fontFamily': 'Arial, sans-serif', 'marginBottom': '5px'}
                        ),
                    ], id='lc-inv-cat2-trigger', n_clicks=0, style={'cursor': 'pointer'}),
                    html.Div([
                        dcc.Checklist(
                            id='lc-inv-category-2',
                            options=[{'label': '(All)', 'value': 'All'}] + [opt for opt in filter_opts['categories_2'] if opt['value'] != 'All'],
                            value=[opt['value'] for opt in filter_opts['categories_2']],  # All checked by default
                            labelStyle={
                                'display': 'block',
                                'fontSize': '11px',
                                'color': '#333',
                                'fontFamily': 'Arial, sans-serif',
                                'marginBottom': '3px'
                            }
                        )
                    ], id='lc-inv-cat2-container', style={'display': 'none', 'paddingLeft': '10px', 'marginTop': '5px'})
                ], style={'marginBottom': '15px'}),
                
                # External Link at bottom of sidebar
                html.Div([
                    html.A("Go To Low-Carbon Investment Tracker Data", 
                           href="https://www.energyintel.com/low-carbon-energy-data#low-carbon-investment-data",
                           target="_blank",
                           rel="noopener noreferrer",
                           style={
                               'color': '#4A90E2',
                               'fontSize': '11px',
                               'textDecoration': 'underline',
                               'fontFamily': 'Arial, sans-serif'
                           })
                ], style={'marginTop': '20px'})

            ], style={
                'width': '220px', 
                'minWidth': '220px',
                'borderLeft': '1px solid #dee2e6',
                'padding': '15px',
                'backgroundColor': '#ffffff',
                'height': 'fit-content'
            })
            
        ], style={'display': 'flex', 'flexDirection': 'row'})
        
    ], className='tab-content', style={'backgroundColor': '#ffffff', 'minHeight': '100vh', 'padding': '10px'})


def register_callbacks(dash_app, server):
    """Register callbacks for the investments list"""
    
    # Remove handle_category_all as Project Category is now a dropdown
    
    @callback(
        Output('lc-inv-region', 'value'),
        [Input('lc-inv-region', 'value')],
        [State('lc-inv-region', 'options')]
    )
    def handle_region_all(selected_values, all_options):
        """Handle (All) checkbox for Region"""
        if not selected_values:
            return []
        
        all_values = [opt['value'] for opt in all_options if opt['value'] != 'All']
        
        # If "All" was just checked
        if 'All' in selected_values and len(selected_values) == 1:
            return ['All'] + all_values
        
        # If "All" is checked and user unchecked something
        if 'All' in selected_values and len(selected_values) < len(all_values) + 1:
            return [v for v in selected_values if v != 'All']
        
        # If all individual items are checked, add "All"
        if 'All' not in selected_values and len(selected_values) == len(all_values):
            return ['All'] + selected_values
        
        return selected_values
    
    @callback(
        Output('lc-inv-category-2', 'value'),
        [Input('lc-inv-category-2', 'value')],
        [State('lc-inv-category-2', 'options')]
    )
    def handle_category2_all(selected_values, all_options):
        """Handle (All) checkbox for Project Category 2"""
        if not selected_values:
            return []
        
        all_values = [opt['value'] for opt in all_options if opt['value'] != 'All']
        
        # If "All" was just checked
        if 'All' in selected_values and len(selected_values) == 1:
            return ['All'] + all_values
        
        # If "All" is checked and user unchecked something
        if 'All' in selected_values and len(selected_values) < len(all_values) + 1:
            return [v for v in selected_values if v != 'All']
        
        # If all individual items are checked, add "All"
        if 'All' not in selected_values and len(selected_values) == len(all_values):
            return ['All'] + selected_values
        
        return selected_values
    
    @callback(
        Output('lc-inv-summary-boxes', 'children'),
        Output('lc-inv-summary-title', 'children'),
        [
            Input('lc-inv-table', 'data'),
            Input('lc-inv-company', 'value'),
            Input('lc-inv-category', 'value')
        ]
    )
    def update_summary(table_data, company, selected_category):
        """Update investment count summary boxes dynamically based on filtered table data"""
        title = f"Investment Count by Company - {company}"
        if not table_data:
            return html.Div("No data matches selected filters", style={'padding': '10px'}), title
        
        df = pd.DataFrame(table_data)
        
        # Aggregate by Project Category
        summary_df = df.groupby('Project Category').agg({
            'Asset Name': 'count',
            'Investment ($ Million)': 'sum'
        }).reset_index()
        summary_df.columns = ['category', 'investment_count', 'total_investment']
        
        total_count = len(df)
        total_investment = df['Investment ($ Million)'].sum()
        
        summary = {row['category']: {'count': row['investment_count'], 'investment': row['total_investment']} for _, row in summary_df.iterrows()}
        
        # Define category colors and order
        category_config = {
            'L-C Power Generation': {'color': '#3B5F7F', 'text_color': 'white'},
            'Hydrogen & L-C Fuels/Gases': {'color': '#5B9BD5', 'text_color': 'white'},
            'CCS & Carbon Removal': {'color': '#70B8C4', 'text_color': 'white'},
            'EVs & Mobility': {'color': '#A4D4D4', 'text_color': 'black'},
            'Electricity Solutions': {'color': '#C5E5E5', 'text_color': 'black'},
            'Other': {'color': '#E0F0F0', 'text_color': 'black'}
        }
        
        boxes = []
        for category, config in category_config.items():
            cat_data = summary.get(category, {'count': 0, 'investment': 0})
            count = cat_data['count']
            investment = cat_data['investment']
            
            # Calculate percentage
            percentage = (count / total_count * 100) if total_count > 0 else 0
            
            # Format investment in billions
            investment_billions = investment / 1000 if investment else 0
            total_billions = total_investment / 1000 if total_investment else 0
            
            # Determine flex size
            flex_size = '0.5' if category in ['EVs & Mobility', 'Electricity Solutions', 'Other'] else '1'
            
            box_content = [
                html.Div(category, style={'color': config['text_color'], 'fontWeight': 'bold', 'fontSize': '12px', 'marginBottom': '4px'}),
                html.Div(f"{percentage:.2f}%", style={'color': config['text_color'], 'fontSize': '11px', 'marginBottom': '2px'})
            ]
            
            if flex_size == '1':
                box_content.extend([
                    html.Div(f"{count} Investments out of {total_count} Total", style={'color': config['text_color'], 'fontSize': '9px'}),
                    html.Div(f"${investment_billions:.0f} Billion out of ${total_billions:.0f} Billion Total", style={'color': config['text_color'], 'fontSize': '9px'})
                ])
            
            # Determine highlighting
            is_selected = category == selected_category
            
            if selected_category != 'All' and not is_selected:
                opacity = 0.35
                border_style = '1px solid transparent'
            elif is_selected:
                opacity = 1
                border_style = '3px solid #1b365d'
            else:
                opacity = 1
                border_style = '1px solid transparent'
            
            boxes.append(
                html.Div(box_content, 
                    id={'type': 'lc-summary-box', 'index': category},
                    n_clicks=0,
                    style={
                        'backgroundColor': config['color'], 
                        'padding': '10px', 
                        'flex': flex_size, 
                        'marginRight': '1px',
                        'cursor': 'pointer',
                        'border': border_style,
                        'transition': 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                        'opacity': opacity
                    })
            )
        
        return html.Div(boxes, style={'display': 'flex', 'marginBottom': '15px'}), title

    @callback(
        Output('lc-inv-category', 'value'),
        Input({'type': 'lc-summary-box', 'index': ALL}, 'n_clicks'),
        State('lc-inv-category', 'value'),
        prevent_initial_call=True
    )
    def update_category_from_box(n_clicks, current_category):
        ctx = dash.callback_context
        if not ctx.triggered or all(c is None or c == 0 for c in n_clicks):
            return dash.no_update
        
        # Get the ID of the component that triggered the callback
        triggered_prop = ctx.triggered[0]['prop_id']
        if 'n_clicks' not in triggered_prop:
            return dash.no_update
            
        triggered_id = triggered_prop.split('.')[0]
        import json
        try:
            triggered_id_dict = json.loads(triggered_id)
            new_selection = triggered_id_dict['index']
            # Toggle logic: if clicking the already selected box, reset to All
            if new_selection == current_category:
                return 'All'
            return new_selection
        except:
            return dash.no_update
    
    @callback(
        Output('lc-inv-table', 'data'),
        Output('lc-inv-table', 'columns'),
        [
            Input('lc-inv-asset-search', 'value'),
            Input('lc-inv-peer-group', 'value'),
            Input('lc-inv-year', 'value'),
            Input('lc-inv-company', 'value'),
            Input('lc-inv-type', 'value'),
            Input('lc-inv-status', 'value'),
            Input('lc-inv-country', 'value'),
            Input('lc-inv-category', 'value'),
            Input('lc-inv-region', 'value'),
            Input('lc-inv-category-2', 'value')
        ]
    )
    def update_table(asset_name, peer_group, year, company, inv_type, status, country, category, region, category_2):
        """Update table based on filter selections"""
        
        # Handle empty or "All" in region - don't filter
        if not region or (region and 'All' in region):
            region = None
        
        # Handle "All" in category - don't filter
        if category == 'All':
            category = None
        
        # Handle empty or "All" in category_2 - don't filter
        if not category_2 or (category_2 and 'All' in category_2):
            category_2 = None
        
        # Build filters dict
        filters = {
            'asset_name': asset_name,
            'peer_group': peer_group,
            'year_announced': year,
            'company': company,
            'investment_type': inv_type,
            'status': status,
            'country': country,
            'project_category': category,
            'region': region,
            'project_category_2': category_2
        }
        
        # Load data
        df = load_investments_data(filters)
        
        if df.empty:
            return [], []
        
        # Create columns
        columns = [{'name': col, 'id': col} for col in df.columns]
        
        # Convert to records
        data = df.to_dict('records')
        
        return data, columns
    
    @callback(
        Output('lc-inv-status-container', 'style'),
        Input('lc-inv-status-trigger', 'n_clicks'),
        prevent_initial_call=True
    )
    def toggle_status_checklist(n_clicks):
        if n_clicks and n_clicks % 2 == 1:
            return {'display': 'block', 'paddingLeft': '10px', 'marginTop': '5px'}
        return {'display': 'none', 'paddingLeft': '10px', 'marginTop': '5px'}

    @callback(
        Output('lc-inv-region-container', 'style'),
        Input('lc-inv-region-trigger', 'n_clicks'),
        prevent_initial_call=True
    )
    def toggle_region_checklist(n_clicks):
        if n_clicks and n_clicks % 2 == 1:
            return {'display': 'block', 'paddingLeft': '10px', 'marginTop': '5px'}
        return {'display': 'none', 'paddingLeft': '10px', 'marginTop': '5px'}

    @callback(
        Output('lc-inv-cat2-container', 'style'),
        Input('lc-inv-cat2-trigger', 'n_clicks'),
        prevent_initial_call=True
    )
    def toggle_cat2_checklist(n_clicks):
        if n_clicks and n_clicks % 2 == 1:
            return {'display': 'block', 'paddingLeft': '10px', 'marginTop': '5px'}
        return {'display': 'none', 'paddingLeft': '10px', 'marginTop': '5px'}
    
    @callback(
        [
            Output('lc-inv-peer-group', 'options'),
            Output('lc-inv-year', 'options'),
            Output('lc-inv-company', 'options'),
            Output('lc-inv-type', 'options'),
            Output('lc-inv-status', 'options'),
            Output('lc-inv-country', 'options'),
            Output('lc-inv-category', 'options'),
            Output('lc-inv-region', 'options'),
            Output('lc-inv-category-2', 'options')
        ],
        [
            Input('lc-inv-asset-search', 'value'),
            Input('lc-inv-peer-group', 'value'),
            Input('lc-inv-year', 'value'),
            Input('lc-inv-company', 'value'),
            Input('lc-inv-type', 'value'),
            Input('lc-inv-status', 'value'),
            Input('lc-inv-country', 'value'),
            Input('lc-inv-category', 'value'),
            Input('lc-inv-region', 'value'),
            Input('lc-inv-category-2', 'value')
        ]
    )
    def update_filter_options(asset_name, peer_group, year, company, inv_type, status, country, category, region, category_2):
        """Update all filter options dynamically based on other selections"""
        
        # Handle "All" in region - don't filter
        if not region or (region and 'All' in region):
            region_val = None
        else:
            region_val = region
        
        # Handle "All" in category_2 - don't filter
        if not category_2 or (category_2 and 'All' in category_2):
            cat2_val = None
        else:
            cat2_val = category_2
            
        filters = {
            'asset_name': asset_name,
            'peer_group': peer_group,
            'year_announced': year,
            'company': company,
            'investment_type': inv_type,
            'status': status,
            'country': country,
            'project_category': category,
            'region': region_val,
            'project_category_2': cat2_val
        }
        
        opts = load_filter_options(filters)
        
        # Special handling for checklist options (keep 'All' if it exists)
        region_opts = [{'label': '(All)', 'value': 'All'}] + [opt for opt in opts['regions'] if opt['value'] != 'All']
        cat2_opts = [{'label': '(All)', 'value': 'All'}] + [opt for opt in opts['categories_2'] if opt['value'] != 'All']
        
        return (
            opts['peer_groups'],
            opts['years'],
            opts['companies'],
            opts['investment_types'],
            opts['statuses'],
            opts['countries'],
            opts['categories'],
            region_opts,
            cat2_opts
        )
    
    # Callback for Export to CSV
    @callback(
        Output('download-investments-csv', 'data'),
        [Input('btn-export-table', 'n_clicks')],
        [State('lc-inv-table', 'data')]
    )
    def export_investments_csv(n_clicks, table_data):
        if n_clicks and table_data:
            df = pd.DataFrame(table_data)
            return dcc.send_data_frame(df.to_csv, "low_carbon_investments.csv", index=False)
        return None
    # Clientside callback to open reference link in new tab when cell is clicked
    dash_app.clientside_callback(
        """
        function(active_cell, data) {
            if (active_cell && data) {
                const rowIndex = active_cell.row;
                const rowData = data[rowIndex];
                if (rowData && rowData.Reference && rowData.Reference.startsWith('http')) {
                    window.open(rowData.Reference, '_blank', 'noopener,noreferrer');
                }
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('lc-inv-link-dummy', 'children'),
        Input('lc-inv-table', 'active_cell'),
        State('lc-inv-table', 'data'),
        prevent_initial_call=True
    )
