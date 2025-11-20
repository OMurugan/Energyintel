"""
Standalone script to create United States Production table
Matching the format shown in the Energy Intelligence dashboard
"""
from dash import dcc, html, dash_table
import pandas as pd
import os

# Path to the data file
DATA_DIR = os.path.join(os.path.dirname(__file__), 'app', 'dashboards', 'data', 'Country_Profile')
MONTHLY_PRODUCTION_CSV = os.path.join(DATA_DIR, 'Monthly_Production_data.csv')

def load_production_data():
    """Load production data from CSV"""
    try:
        df = pd.read_csv(MONTHLY_PRODUCTION_CSV)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

def create_united_states_production_table():
    """Create United States Production table matching the Energy Intelligence format"""
    # Load data
    monthly_prod_df = load_production_data()
    
    if monthly_prod_df.empty:
        return dash_table.DataTable(
            data=[],
            columns=[],
            style_cell={'textAlign': 'left', 'fontFamily': 'Arial, sans-serif', 'fontSize': '13px'}
        )
    
    # Filter for United States Production
    if 'Monthly production dynamic title' in monthly_prod_df.columns:
        us_data = monthly_prod_df[
            monthly_prod_df['Monthly production dynamic title'].str.contains('United States Production', case=False, na=False)
        ].copy()
    else:
        return dash_table.DataTable(data=[], columns=[])
    
    if us_data.empty:
        return dash_table.DataTable(data=[], columns=[])
    
    # Prepare data
    us_data['Year'] = us_data['Year of Date'].astype(int)
    us_data['Month'] = us_data['Month of Date'].astype(str)
    
    # Get unique years (most recent first)
    years = sorted(us_data['Year'].unique(), reverse=True)
    
    # Month order (chronological - January through December)
    # Based on image: July-December for 2025, August-December for 2024
    months_order = ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December']
    
    # Get unique crudes (sorted alphabetically, but Total should be last)
    crudes = sorted([c for c in us_data['Crude'].unique() if c != 'Total'])
    if 'Total' in us_data['Crude'].unique():
        crudes.append('Total')
    
    # Build columns with nested structure: Date -> Year -> Month
    columns = [{'name': ['', '', 'Crude'], 'id': 'Crude', 'type': 'text'}]
    
    # Add date columns grouped by year
    for year in years:
        year_data = us_data[us_data['Year'] == year]
        year_months = sorted(year_data['Month'].unique(), 
                           key=lambda x: months_order.index(x) if x in months_order else 999)
        
        for month in year_months:
            col_id = f"{year}_{month}"
            columns.append({
                'name': ['Date', str(year), month],
                'id': col_id,
                'type': 'numeric',
                'format': {'specifier': ',.0f'}  # Integer format with thousands separator
            })
    
    # Build table data
    table_data = []
    for crude in crudes:
        row = {'Crude': crude}
        
        for year in years:
            year_data = us_data[us_data['Year'] == year]
            year_months = sorted(year_data['Month'].unique(),
                               key=lambda x: months_order.index(x) if x in months_order else 999)
            
            for month in year_months:
                col_id = f"{year}_{month}"
                # Get value for this crude, year, month combination
                value_row = us_data[
                    (us_data['Crude'] == crude) & 
                    (us_data['Year'] == year) & 
                    (us_data['Month'] == month)
                ]
                
                if not value_row.empty:
                    value = value_row['Avg. Value'].iloc[0]
                    # Format as integer (no decimals)
                    row[col_id] = int(round(value)) if pd.notna(value) else ''
                else:
                    row[col_id] = ''
        
        table_data.append(row)
    
    # Create the DataTable
    return dash_table.DataTable(
        data=table_data,
        columns=columns,
        style_cell={
            'textAlign': 'center',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '13px',
            'padding': '12px',
            'border': '1px solid #dee2e6'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': '600',
            'color': '#2c3e50',
            'border': '1px solid #dee2e6',
            'textAlign': 'center'
        },
        style_data={
            'border': '1px solid #dee2e6',
            'backgroundColor': 'white'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            }
        ],
        style_cell_conditional=[
            {
                'if': {'column_id': 'Crude'},
                'textAlign': 'left',
                'fontWeight': '500'
            },
            {
                'if': {'filter_query': '{Crude} = Total'},
                'fontWeight': 'bold'
            }
        ],
        page_action='none',
        filter_action='none',
        sort_action='none',
        merge_duplicate_headers=True,
        style_table={
            'overflowX': 'auto',
            'border': '1px solid #dee2e6',
            'borderRadius': '4px',
            'backgroundColor': 'white'
        }
    )


def create_table_layout():
    """Create a complete layout with the table"""
    return html.Div([
        html.H5(
            "United States Production",
            style={
                'color': '#fe5000',  # Orange color matching the image
                'fontWeight': '600',
                'fontSize': '18px',
                'marginBottom': '20px',
                'marginTop': '20px'
            }
        ),
        html.Div([
            create_united_states_production_table()
        ], style={
            'background': 'white',
            'padding': '20px',
            'borderRadius': '8px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
        })
    ], style={'padding': '24px', 'background': '#f8f9fa'})


if __name__ == '__main__':
    # Example usage
    from dash import Dash
    
    app = Dash(__name__)
    app.layout = create_table_layout()
    
    if __name__ == '__main__':
        app.run_server(debug=True, port=8051)

