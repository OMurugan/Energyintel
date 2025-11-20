"""
Imports - Country Detail View
Detailed imports data by country
"""
from dash import dcc, html, Input, Output, callback, State, dash_table
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
from datetime import datetime


# File paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'Trade')
LEGEND_CSV = os.path.join(DATA_DIR, 'Chart 1_Legend .csv')
IMPORTS_BY_COUNTRY_CSV = os.path.join(DATA_DIR, 'Chart_Imports by Country and Crude.csv')
TABLE_IMPORTS_CSV = os.path.join(DATA_DIR, 'Table_Imports.csv')
SOURCE_CSV = os.path.join(DATA_DIR, 'Source.csv')
FOOTNOTE_CSV = os.path.join(DATA_DIR, 'Footnote.csv')


def load_legend_data():
    """Load region colors from legend CSV"""
    try:
        df = pd.read_csv(LEGEND_CSV, skiprows=3, header=None, sep='\t', encoding='utf-16')
        df.columns = ['Region', 'Value']
        # Filter out empty rows and get unique regions
        df = df[df['Region'].notna() & (df['Region'] != '')]
        regions = df['Region'].unique().tolist()
        
        # Define colors for each region (matching the figure exactly)
        # Based on the legend: Africa=Medium Blue, Asia-Pacific=Bright Orange, Europe=Vibrant Green,
        # FSU=Strong Red, Latin America=Medium Purple, Middle East=Dark Brown, 
        # North America=Light Pink/Magenta, Others=Medium Grey
        color_map = {
            'Africa': '#1f77b4',  # Medium Blue
            'Asia-Pacific': '#ff7f0e',  # Bright Orange
            'Europe': '#2ea12e',  # Vibrant Green
            'FSU': '#d62a2b',  # Strong Red (Crimson)
            'Latin America': '#9569be',  # Medium Purple
            'Middle East': '#8d584d',  # Dark Brown
            'North America': '#e379c3',  # Light Pink/Magenta (Hot Pink)
            'Others': '#808080'  # Medium Grey
        }
        return regions, color_map
    except Exception as e:
        print(f"Error loading legend: {e}")
        import traceback
        traceback.print_exc()
        return [], {}


def load_imports_by_region_data():
    """Load and aggregate imports data by region and year from Table_Imports.csv"""
    try:
        # Read CSV, skip first 2 rows (header info), use row 3 as column headers
        df = pd.read_csv(TABLE_IMPORTS_CSV, skiprows=2, header=0, sep='\t', encoding='utf-16')
        
        # Get year columns (2025 to 2006)
        year_cols = [str(year) for year in range(2025, 2005, -1)]
        
        # Filter to only rows with region totals (rows where Exporter == 'Total')
        # Exclude 'Grand Total' row - we only want individual regions
        region_totals = df[(df['Exporter'] == 'Total') & (df['Exporting Region'] != 'Grand Total')].copy()
        
        # Melt the dataframe to long format
        data_rows = []
        for _, row in region_totals.iterrows():
            region = row['Exporting Region']
            if pd.isna(region) or region == '' or region == 'Grand Total':
                continue
            for year in year_cols:
                if year in row.index:
                    value = row[year]
                    if pd.notna(value) and value != '':
                        try:
                            # Handle comma-separated numbers (e.g., "2,223" -> 2223)
                            if isinstance(value, str):
                                value = value.replace(',', '').strip()
                            value = float(value)
                            if value > 0:
                                data_rows.append({
                                    'Region': str(region).strip(),
                                    'Year': int(year),
                                    'Volume': value
                                })
                        except (ValueError, TypeError):
                            continue
        
        result_df = pd.DataFrame(data_rows)
        return result_df
    except Exception as e:
        print(f"Error loading imports by region: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_imports_by_country_crude_data():
    """Load imports data by country and crude from Chart_Imports by Country and Crude.csv"""
    try:
        df = pd.read_csv(IMPORTS_BY_COUNTRY_CSV, sep='\t', encoding='utf-16')
        
        # Parse the Year column (format: 01-01-YYYY)
        df['Year'] = pd.to_datetime(df['Year'], format='%d-%m-%Y', errors='coerce').dt.year
        
        # Clean up the data
        df = df[df['DataValue'].notna() & (df['DataValue'] > 0)]
        
        return df
    except Exception as e:
        print(f"Error loading imports by country/crude: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_table_data():
    """Load table data from Table_Imports.csv"""
    try:
        # Read CSV, skip first 2 rows, use row 3 as headers
        df = pd.read_csv(TABLE_IMPORTS_CSV, skiprows=2, header=0, sep='\t', encoding='utf-16')
        
        # Filter out total rows
        df = df[df['Exporter'] != 'Total'].copy()
        
        # Remove rows where all year columns are empty
        year_cols = [str(year) for year in range(2025, 2005, -1)]
        df = df[df[year_cols].notna().any(axis=1)]
        
        return df
    except Exception as e:
        print(f"Error loading table data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_source_data():
    """Load source information"""
    try:
        with open(SOURCE_CSV, 'r', encoding='utf-16') as f:
            lines = f.readlines()
            if len(lines) > 1:
                return lines[1].strip()
        return "Energy Intelligence"
    except Exception as e:
        print(f"Error loading source: {e}")
        return "Energy Intelligence"


def load_footnote_data():
    """Load footnote information"""
    try:
        df = pd.read_csv(FOOTNOTE_CSV, encoding='utf-16')
        if 'Note' in df.columns:
            notes = df['Note'].dropna().unique().tolist()
            return notes
        return []
    except Exception as e:
        print(f"Error loading footnote: {e}")
        return []


def create_layout():
    """Create the Imports - Country Detail layout"""
    regions, _ = load_legend_data()
    source = load_source_data()
    footnotes = load_footnote_data()
    
    # Get available countries from the data
    country_crude_df = load_imports_by_country_crude_data()
    available_countries = sorted(country_crude_df['Importer'].unique().tolist()) if not country_crude_df.empty else ['Japan']
    
    return html.Div([
        dcc.Store(id='selected-year-store', data=2023),  # Store selected year from chart click
        dcc.Store(id='selected-country-store', data='Japan'),  # Store selected country
        
        # Country Selector
        html.Div([
            html.Label(
                "Select Importing Country",
                style={
                    'fontWeight': 'bold',
                    'fontSize': '16px',
                    'lineHeight': '18px',
                    'color': '#1b365d',
                    'marginBottom': '5px',
                    'display': 'block',
                    'fontFamily': '"Lato", "Benton Sans", "Arial", "Helvetica", sans-serif',
                    'textAlign': 'left'
                }
            ),
            dcc.Dropdown(
                id='importing-country-select',
                options=[{'label': country, 'value': country} for country in available_countries],
                value='Japan',
                style={
                    'width': '1200px',
                    'fontSize': '13px',
                    'fontFamily': '"Lato", "Benton Sans", "Arial", "Helvetica", sans-serif',
                    'color': '#1b365d',
                    'align': 'center',
                },
                className='importing-country-dropdown'
            )
        ], style={'marginBottom': '20px'}),
        
        # First Chart: Imports by Region over Time
        html.Div([
            dcc.Graph(id='imports-by-region-chart')
        ], style={'marginBottom': '30px'}),
        
        # Instruction text
        html.Div([
            html.P(
                "Click on any bar to highlight it. Use the country selector above to change the data view.",
                style={'fontSize': '13px', 'fontStyle': 'italic', 'marginBottom': '20px', 'color': '#666'}
            )
        ]),
        
        # Second Chart: Imports by Country for Selected Year
        html.Div([
            dcc.Graph(id='imports-by-country-chart')
        ], style={'marginBottom': '30px'}),
        
        # Table: Detailed Imports Data
        html.Div([
            html.H4(id='imports-table-title', children="Japan Crude Oil Imports by Region and Country", className='imports-table-title'),
            dash_table.DataTable(
                id='imports-detail-table',
                data=[],
                columns=[
                    {'name': 'Exporting Region', 'id': 'Exporting Region'},
                    {'name': 'Exporter', 'id': 'Exporter'},
                    {'name': 'Company', 'id': 'Company'},
                    {'name': 'Crude', 'id': 'Crude'}
                ],
                style_table={
                    'overflowX': 'auto',
                    'overflowY': 'auto',
                    'maxHeight': '500px',
                    'fontFamily': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                    'border': '1px solid #d3d3d3',
                    'borderRadius': '4px'
                },
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px 12px',
                    'fontSize': '12px',
                    'fontFamily': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                    'border': '1px solid #e0e0e0',
                    'backgroundColor': 'white',
                    'color': '#333333',
                    'minWidth': '80px',
                    'width': 'auto',
                    'maxWidth': '200px',
                    'whiteSpace': 'normal',
                    'height': 'auto'
                },
                style_header={
                    'backgroundColor': '#f8f8f8',
                    'fontWeight': '600',
                    'border': '1px solid #d3d3d3',
                    'textAlign': 'center',
                    'fontSize': '12px',
                    'fontFamily': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                    'color': '#333333',
                    'textTransform': 'none',
                    'padding': '10px 12px'
                },
                style_data={
                    'border': '1px solid #e0e0e0',
                    'backgroundColor': 'white',
                    'color': '#333333'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#fafafa'
                    },
                    {
                        'if': {'filter_query': '{Exporting Region} = Total'},
                        'fontWeight': '600',
                        'backgroundColor': '#f0f0f0'
                    },
                    {
                        'if': {'column_id': 'Exporting Region'},
                        'minWidth': '150px',
                        'width': '150px',
                        'maxWidth': '150px'
                    },
                    {
                        'if': {'column_id': 'Exporter'},
                        'minWidth': '150px',
                        'width': '150px',
                        'maxWidth': '150px'
                    },
                    {
                        'if': {'column_id': 'Company'},
                        'minWidth': '120px',
                        'width': '120px',
                        'maxWidth': '120px'
                    },
                    {
                        'if': {'column_id': 'Crude'},
                        'minWidth': '150px',
                        'width': '150px',
                        'maxWidth': '150px'
                    }
                ],
                page_action='none',
                filter_action='none',
                sort_action='none',
                fixed_rows={'headers': True}
            )
        ], style={'marginBottom': '30px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '4px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'}),
        
        # Source and Footer
        html.Div([
            html.Div([
                html.P(f"Source: {source}", style={'fontSize': '11px', 'marginBottom': '5px'})
            ]),
            html.Div([
                html.P(note, style={'fontSize': '11px', 'marginBottom': '2px'}) 
                for note in footnotes
            ])
        ], style={'marginTop': '20px', 'fontSize': '11px', 'color': '#666'})
    ], className='tab-content', style={'padding': '20px'})


def create_imports_by_region_chart(selected_country='Japan'):
    """Create stacked bar chart showing imports by region over time"""
    df = load_imports_by_region_data()
    _, color_map = load_legend_data()
    
    if df.empty:
        return go.Figure()
    
    # Filter by country if needed (for now, data is already filtered to Japan)
    # Group by Region and Year, sum volumes
    df_grouped = df.groupby(['Region', 'Year'])['Volume'].sum().reset_index()
    
    # Get all years from 2006 to 2025 (matching Figure 1)
    years = sorted([y for y in df_grouped['Year'].unique() if 2006 <= y <= 2025])
    
    # Define stacking order to match Figure 1: Middle East at bottom, then others
    # Order: Middle East (bottom), Africa, Asia-Pacific, Europe, FSU, Latin America, North America, Others (top)
    region_order = ['Middle East', 'Africa', 'Asia-Pacific', 'Europe', 'FSU', 'Latin America', 'North America', 'Others']
    
    # Get available regions from data
    available_regions = df_grouped['Region'].unique().tolist()
    
    # Sort regions according to the stacking order (only include regions that exist in data)
    regions = [r for r in region_order if r in available_regions]
    # Add any remaining regions not in the predefined order
    for r in sorted(available_regions):
        if r not in regions:
            regions.append(r)
    
    fig = go.Figure()
    
    # Add a trace for each region in the specified stacking order
    # In stacked bars, first trace is at bottom, last trace is at top
    for region in regions:
        region_data = df_grouped[df_grouped['Region'] == region]
        volumes = []
        for year in years:
            year_data = region_data[region_data['Year'] == year]
            if len(year_data) > 0:
                volumes.append(year_data['Volume'].iloc[0])
            else:
                volumes.append(0)
        
        fig.add_trace(go.Bar(
            x=years,
            y=volumes,
            name=region,
            marker_color=color_map.get(region, '#CCCCCC'),
            hovertemplate=f'Region: {region}<br>Year: %{{x}}<br>Import Volume: %{{y:,.0f}} (\'000 b/d)<extra></extra>',
            selected=dict(marker=dict(opacity=1.0)),  # Selected bars remain fully opaque
            unselected=dict(marker=dict(opacity=0.3))
            
        ))
    
    # Calculate total volumes for each year to display on top of bars
    year_totals = df_grouped.groupby('Year')['Volume'].sum()
    total_volumes = [year_totals.get(year, 0) for year in years]
    
    # Add total values on top of bars
    fig.add_trace(go.Scatter(
        x=years,
        y=total_volumes,
        mode='text',
        text=[f'{val:,.0f}' if val > 0 else '' for val in total_volumes],
        textposition='top center',
        showlegend=False,
        hoverinfo='skip',
        textfont=dict(size=11, color='#000000')
    ))
    
    # Update layout to match Figure 1 exactly
    fig.update_layout(
        title={
            'text': f"{selected_country}'s Crude Imports by Exporting Region",
            'x': 0.5,
            'xanchor': 'center',
            'font': {
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 16,
                'color': '#ff7f0e'  # Orange color matching Figure 1
            }
        },
        xaxis=dict(
            title="Year",
            tickmode='linear',
            tick0=2006,
            dtick=1,  # Show every year
            range=[2005.5, 2025.5],  # Slight padding for better visibility
            tickfont={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 11,
                'color': '#333333'
            },
            titlefont={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 13,
                'color': '#333333'
            },
            showgrid=True,
            gridcolor='#e0e0e0',
            gridwidth=1,
            linecolor='#d3d3d3',
            linewidth=1
        ),
        yaxis=dict(
            title="Import Volume ('000 b/d)",
            range=[0, 4500],  # Set range to 0-4500 to show up to 4000 clearly
            tickmode='linear',
            tick0=0,
            dtick=1000,  # Show ticks at 0, 1000, 2000, 3000, 4000
            tickfont={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 11,
                'color': '#333333'
            },
            titlefont={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 13,
                'color': '#333333'
            },
            showgrid=True,
            gridcolor='#e0e0e0',
            gridwidth=1,
            linecolor='#d3d3d3',
            linewidth=1
        ),
        barmode='stack',
        height=400,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=60, r=200, t=60, b=50),
        clickmode='select',  # Only selection, no event callbacks
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            font={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 11,
                'color': '#333333'
            },
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#d3d3d3',
            borderwidth=1
        ),
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='white',
            bordercolor='#999999',
            font=dict(
                size=12,
                family='"Benton Sans", "Arial", "Helvetica", sans-serif',
                color='#000000'
            ),
            align='left'
        )
    )
    
    return fig


def create_imports_by_country_chart(selected_year=2023, selected_country='Japan'):
    """Create stacked bar chart showing imports by country for selected year, broken down by crude"""
    df = load_imports_by_country_crude_data()
    
    if df.empty:
        return go.Figure()
    
    # Filter by year and country
    df_filtered = df[(df['Year'] == selected_year) & (df['Importer'] == selected_country)].copy()
    
    if df_filtered.empty:
        return go.Figure()
    
    # Remove duplicates based on Exporter, Crude, and DataValue
    # Keep only the first occurrence of each unique combination
    df_filtered = df_filtered.drop_duplicates(subset=['Exporter', 'Crude', 'DataValue'], keep='first')
    
    # Group by Exporter and Crude, sum volumes
    # Note: Color column contains crude names, not actual colors
    df_grouped = df_filtered.groupby(['Exporter', 'Crude'])['DataValue'].sum().reset_index()
    
    # Get all exporters and order by total volume
    exporter_totals = df_grouped.groupby('Exporter')['DataValue'].sum().sort_values(ascending=False)
    exporters = exporter_totals.index.tolist()
    
    # Define exact color mapping for each crude type
    crude_color_map = {
        'Al-Shaheen': '#2ca02c',
        'Arab Extra Light': '#ff9896',
        'Arab Heavy': '#9467bd',
        'Arab Light': '#c5b0d5',
        'Arab Medium': '#c49c94',
        'Arab Super Light': '#f7b6d2',
        'Bach Ho': '#d62728',
        'Banoco Arab Medium': '#c7c7c7',
        'Champion': '#7f7f7f',
        'Clifhead': '#c7c7c7',
        'Cossack': '#8c564b',
        'Das Blend': '#2ca02c',
        'Deodorized Field Condensate': '#98df8a',
        'Dubai': '#ff9896',
        'Ichthys Condensate': '#7f7f7f',
        'Isthmus': '#c7c7c7',
        'Ketapang': '#c7c7c7',
        'Khafji': '#d62728',
        'Kikeh': '#dbdb8d',
        'Kuwait': '#8c564b',
        'Kuwait Super Light': '#f7b6d2',
        'Lalang': '#1f77b4',
        'Mares Blend': '#aec7e8',
        'Mars Blend': '#ff7f0e',
        'Mubarras Blend': '#1f77b4',
        'Murban': '#aec7e8',
        'Napo': '#98df8a',
        'Nile Blend Sudan': '#d62728',
        'Oman': '#8c564b',
        'Oriente': '#ff9896',
        'Pyrenees': '#c49c94',
        'Qatar Land': '#c7c7c7',
        'Qatar Low Sulphur Condensate': '#bcbd22',
        'Qatar Marine': '#dbdb8d',
        'Ruby': '#f7b6d2',
        'Sakhalin Blend': '#ff9896',
        'Sepat': '#bcbd22',
        'Seria Light': '#17becf',
        'Stag': '#9edae5',
        'Thang Long': '#ffbb78',
        'Umm Lulu': '#bcbd22',
        'Upper Zakum': '#9edae5',
        'Wandoo': '#2ca02c',
        'West Texas Intermediate': '#aec7e8',
        'West Texas Light': '#ff7f0e'
    }
    
    # Get unique crudes from data
    crudes = sorted(df_grouped['Crude'].unique())
    
    fig = go.Figure()
    
    # Store volumes for each crude to calculate cumulative positions for text labels
    crude_volumes_dict = {}
    
    # Add a trace for each crude
    for crude in crudes:
        crude_data = df_grouped[df_grouped['Crude'] == crude]
        volumes = []
        for exporter in exporters:
            exporter_data = crude_data[crude_data['Exporter'] == exporter]
            if len(exporter_data) > 0:
                volumes.append(exporter_data['DataValue'].iloc[0])
            else:
                volumes.append(0)
        
        # Only add trace if there's at least one non-zero value
        if sum(volumes) > 0:
            # Format year as "01-01-YYYY" for hover tooltip
            year_str = f"01-01-{selected_year}"
            fig.add_trace(go.Bar(
                x=exporters,
                y=volumes,
                name=crude,
                marker_color=crude_color_map.get(crude, '#CCCCCC'),
                hovertemplate=f'Crude: {crude}<br>Year: {year_str}<br>Traded Volume: %{{y:,.1f}}(\'000 b/d)<extra></extra>',
                text=[f'{v:,.1f}' if v >= 10 else '' for v in volumes],  # Show value if >= 10
                textposition='inside',
                textangle=-90,  # Rotate text vertically
                textfont=dict(size=10, color='#000000'),
                selected=dict(marker=dict(opacity=1.0)),  # Selected bars remain fully opaque
                unselected=dict(marker=dict(opacity=0.3))  # Unselected bars are dimmed
            ))
            crude_volumes_dict[crude] = volumes
    
    # Update layout
    fig.update_layout(
        title={
            'text': f"{selected_country} Crude Imports by Country - {selected_year}",
            'x': 0.5,
            'xanchor': 'center',
            'font': {
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 16,
                'color': '#333333'
            },
            'pad': {'t': 10, 'b': 20}
        },
        xaxis=dict(
            title={
                'text': "Country",
                'font': {
                    'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                    'size': 13,
                    'color': '#333333'
                }
            },
            tickfont={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 10,
                'color': '#666666'
            },
            tickangle=90,  # Vertical labels (straight up)
            showgrid=False,  # Remove vertical grid lines to avoid square boxes
            showline=True,  # Show the axis line
            linecolor='#d3d3d3',
            linewidth=1,
            mirror=True  # Show axis line on all sides
        ),
        yaxis=dict(
            title={
                'text': "Volume ('000 b/d)",
                'font': {
                    'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                    'size': 13,
                    'color': '#333333'
                }
            },
            tickfont={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 11,
                'color': '#666666'
            },
            range=[0, 1100],  # Set range to 0-1100 to show up to 1000 clearly (matching Figure 1)
            tickmode='linear',
            tick0=0,
            dtick=200,  # Show ticks at 0, 200, 400, 600, 800, 1000 (matching Figure 1)
            gridcolor='#e0e0e0',
            gridwidth=1,
            showgrid=False,  # Remove horizontal grid lines
            showline=True,  # Show the axis line
            linecolor='#d3d3d3',
            linewidth=1,
            mirror=True  # Show axis line on all sides
        ),
        barmode='stack',
        height=520,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=60, r=200, t=60, b=100),
        clickmode='select',  # Only selection, no event callbacks
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            font={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 10,
                'color': '#333333'
            },
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#d3d3d3',
            borderwidth=1
        ),
        hovermode='closest',  # Show only the hovered segment
        hoverlabel=dict(
            bgcolor='white',
            bordercolor='#999999',
            font=dict(
                size=12,
                family='"Benton Sans", "Arial", "Helvetica", sans-serif',
                color='#000000'
            ),
            align='left'
        )
    )
    
    return fig


def create_imports_table(selected_country='Japan'):
    """Create data table from Table_Imports.csv with hierarchical grouping"""
    df = load_table_data()
    
    if df.empty:
        return [], []
    
    # Sort by Exporting Region, Exporter, Company, Crude for proper grouping
    df = df.sort_values(['Exporting Region', 'Exporter', 'Company', 'Crude'], 
                        ascending=[True, True, True, True]).reset_index(drop=True)
    
    # Convert to list of dictionaries for DataTable
    # Ensure all values are native Python types (not pandas/numpy types)
    table_data = []
    for _, row in df.iterrows():
        record = {}
        for col in df.columns:
            value = row[col]
            # Convert pandas/numpy types to native Python types
            if pd.isna(value) or value is None:
                record[col] = ''
            elif hasattr(value, 'item'):  # numpy scalar types have .item() method
                try:
                    record[col] = value.item()
                except:
                    record[col] = str(value)
            elif isinstance(value, (int, float)):
                # Check for NaN or inf
                if isinstance(value, float) and (value != value or abs(value) == float('inf')):
                    record[col] = ''
                else:
                    record[col] = int(value) if isinstance(value, (int, bool)) else float(value)
            elif isinstance(value, bool):
                record[col] = bool(value)
            else:
                # Convert everything else to string
                try:
                    record[col] = str(value) if value is not None else ''
                except:
                    record[col] = ''
        table_data.append(record)
    
    # Process data for hierarchical grouping and formatting
    prev_region = None
    prev_exporter = None
    prev_company = None
    
    for i, record in enumerate(table_data):
        # Ensure record is a dictionary
        if not isinstance(record, dict):
            continue
            
        # Get original values before any modifications
        current_region = str(record.get('Exporting Region', '')).strip() if record.get('Exporting Region') else ''
        current_exporter = str(record.get('Exporter', '')).strip() if record.get('Exporter') else ''
        current_company = str(record.get('Company', '')).strip() if record.get('Company') else ''
        
        # Replace NaN/None values with empty strings or valid numbers for better display (for year columns)
        for key, value in list(record.items()):
            if key not in ['Exporting Region', 'Exporter', 'Company', 'Crude']:
                if value == '' or value is None:
                    record[key] = ''
                elif isinstance(value, (int, float)):
                    # Format numeric values - keep 0 as 0, ensure it's a valid number
                    if value != value:  # Check for NaN (NaN != NaN)
                        record[key] = ''
                    elif abs(value) == float('inf'):
                        record[key] = ''
                    else:
                        # Ensure it's a valid number (native Python type)
                        record[key] = float(value) if isinstance(value, float) else int(value)
                else:
                    # For non-numeric, non-empty values, convert to string
                    record[key] = str(value) if value is not None else ''
        
        # Ensure text columns are strings, not None
        for col in ['Exporting Region', 'Exporter', 'Company', 'Crude']:
            if col in record:
                if record[col] is None or record[col] == '':
                    record[col] = ''
                else:
                    record[col] = str(record[col])
        
        # Hierarchical grouping: only show region/exporter/company once per group
        if current_region and current_region == prev_region:
            # Same region as previous row - make it empty
            record['Exporting Region'] = ''
        else:
            # New region - keep it and reset exporter/company tracking
            prev_region = current_region
            prev_exporter = None
            prev_company = None
        
        if current_exporter and current_exporter == prev_exporter and current_region == prev_region:
            # Same exporter within same region - make it empty
            record['Exporter'] = ''
        else:
            # New exporter - keep it and reset company tracking
            if current_exporter:
                prev_exporter = current_exporter
            prev_company = None
        
        if current_company and current_company == prev_company and current_exporter == prev_exporter:
            # Same company within same exporter - make it empty
            record['Company'] = ''
        else:
            if current_company:
                prev_company = current_company
    
    # Create columns
    columns = [
        {'name': 'Exporting Region', 'id': 'Exporting Region'},
        {'name': 'Exporter', 'id': 'Exporter'},
        {'name': 'Company', 'id': 'Company'},
        {'name': 'Crude', 'id': 'Crude'}
    ]
    
    # Add year columns
    year_cols = [str(year) for year in range(2025, 2005, -1)]
    for year in year_cols:
        if year in df.columns:
            columns.append({
                'name': year, 
                'id': year, 
                'type': 'numeric', 
                'format': {'specifier': ',.0f'},
                'presentation': 'input'  # Allow empty values to show as empty
            })
    
    return table_data, columns


def register_callbacks(dash_app, server):
    """Register all callbacks for Imports - Country Detail"""
    
    @callback(
        Output('imports-by-region-chart', 'figure'),
        [Input('importing-country-select', 'value'),
         Input('current-submenu', 'data')],
        prevent_initial_call=False
    )
    def update_imports_by_region(selected_country, submenu):
        """Update imports by region chart"""
        if submenu != 'imports-detail':
            return go.Figure()
        fig = create_imports_by_region_chart(selected_country)
        # Ensure the figure is valid and has data
        if fig and len(fig.data) > 0:
            return fig
        return go.Figure()
    
    @callback(
        [Output('imports-by-country-chart', 'figure'),
         Output('selected-year-store', 'data')],
        [Input('importing-country-select', 'value'),
         Input('current-submenu', 'data'),
         State('selected-year-store', 'data')]
    )
    def update_imports_by_country(selected_country, submenu, current_year):
        """Update imports by country chart based on country selection"""
        if submenu != 'imports-detail':
            return go.Figure(), current_year
        
        # Use current year (default 2023) - chart 1 clicks no longer affect chart 2
        selected_year = current_year if current_year else 2023
        
        fig = create_imports_by_country_chart(selected_year, selected_country)
        return fig, selected_year
    
    @callback(
        [Output('imports-detail-table', 'data'),
         Output('imports-detail-table', 'columns'),
         Output('imports-table-title', 'children')],
        [Input('importing-country-select', 'value'),
         Input('current-submenu', 'data')]
    )
    def update_imports_table(selected_country, submenu):
        """Update imports detail table"""
        if submenu != 'imports-detail':
            # Return empty but valid structures
            empty_columns = [
                {'name': 'Exporting Region', 'id': 'Exporting Region'},
                {'name': 'Exporter', 'id': 'Exporter'},
                {'name': 'Company', 'id': 'Company'},
                {'name': 'Crude', 'id': 'Crude'}
            ]
            return [], empty_columns, ""
        try:
            data, columns = create_imports_table(selected_country)
            # Ensure data and columns are lists
            if not isinstance(data, list):
                data = []
            if not isinstance(columns, list):
                # Return default columns structure if columns is invalid
                columns = [
                    {'name': 'Exporting Region', 'id': 'Exporting Region'},
                    {'name': 'Exporter', 'id': 'Exporter'},
                    {'name': 'Company', 'id': 'Company'},
                    {'name': 'Crude', 'id': 'Crude'}
                ]
            
            # Deep clean: Ensure all data items are dictionaries with only native Python types
            cleaned_data = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                cleaned_item = {}
                for key, value in item.items():
                    # Ensure key is a string
                    key_str = str(key) if key is not None else ''
                    # Ensure value is a native Python type
                    if value is None:
                        cleaned_item[key_str] = ''
                    elif isinstance(value, (int, float, str, bool)):
                        # Check for NaN or inf in floats
                        if isinstance(value, float) and (value != value or abs(value) == float('inf')):
                            cleaned_item[key_str] = ''
                        else:
                            cleaned_item[key_str] = value
                    elif hasattr(value, 'item'):  # numpy scalar
                        try:
                            cleaned_item[key_str] = value.item()
                        except:
                            cleaned_item[key_str] = str(value)
                    else:
                        # Convert everything else to string
                        try:
                            cleaned_item[key_str] = str(value) if value is not None else ''
                        except:
                            cleaned_item[key_str] = ''
                cleaned_data.append(cleaned_item)
            
            # Ensure all column items are dictionaries with required keys
            cleaned_columns = []
            for col in columns:
                if not isinstance(col, dict):
                    continue
                if 'name' in col and 'id' in col:
                    # Ensure name and id are strings
                    cleaned_col = {
                        'name': str(col['name']) if col['name'] is not None else '',
                        'id': str(col['id']) if col['id'] is not None else ''
                    }
                    # Copy other properties if they exist
                    for key, value in col.items():
                        if key not in ['name', 'id']:
                            cleaned_col[key] = value
                    cleaned_columns.append(cleaned_col)
            
            if not cleaned_columns:
                # Fallback to default columns
                cleaned_columns = [
                    {'name': 'Exporting Region', 'id': 'Exporting Region'},
                    {'name': 'Exporter', 'id': 'Exporter'},
                    {'name': 'Company', 'id': 'Company'},
                    {'name': 'Crude', 'id': 'Crude'}
                ]
            
            title = f"{selected_country} Crude Oil Imports by Region and Country"
            return cleaned_data, cleaned_columns, title
        except Exception as e:
            print(f"Error updating imports table: {e}")
            import traceback
            traceback.print_exc()
            # Return empty but valid structures on error
            empty_columns = [
                {'name': 'Exporting Region', 'id': 'Exporting Region'},
                {'name': 'Exporter', 'id': 'Exporter'},
                {'name': 'Company', 'id': 'Company'},
                {'name': 'Crude', 'id': 'Crude'}
            ]
            return [], empty_columns, ""
