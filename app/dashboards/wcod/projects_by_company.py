"""
Projects by Company View
Upstream projects grouped by company - matches Tableau dashboard design
"""
from dash import dcc, html, Input, Output, State, callback, ALL, callback_context, dash_table
import dash
import json
import plotly.graph_objects as go
import pandas as pd
import os
from core.data_helpers import execute_query
from .shared_map_utils import (
    create_choropleth_map,
    get_mapbox_config,
    load_world_geojson,
    handle_map_click_reset,
    create_empty_map,
    MAP_BACKGROUND_COLOR,
    WORLD_CENTER,
    WORLD_ZOOM
)
from core.country_mappings import get_iso_code

def load_chart_data(company_name=None, likely_goahead_filter=None):
    """Load chart data from database using Query 1 (quarterly data for bar chart)."""
    # Build query conditionally based on filters
    company_filter = ""
    likely_filter = ""
    params = {}
    
    # Get company_id from company_name if provided
    company_id = None
    if company_name:
        try:
            company_id_query = "SELECT company_id FROM dim_company WHERE company_name = :company_name LIMIT 1"
            company_result = execute_query(company_id_query, {'company_name': company_name})
            if company_result and len(company_result) > 0:
                company_id = company_result[0]['company_id']
        except Exception as e:
            print(f"Error getting company_id: {e}")
    
    if company_id:
        company_filter = "AND :company_id IN (a.operator_id, a.partner1_id, a.partner2_id, a.partner3_id, a.partner4_id, a.partner5_id)"
        params['company_id'] = company_id
    
    # Build likely_goahead filter
    if likely_goahead_filter is not None and isinstance(likely_goahead_filter, list):
        if len(likely_goahead_filter) == 0:
            # Empty list means all checkboxes unchecked - return no data
            likely_filter = "AND 1=0"  # This will match nothing
        elif 'ALL' in [str(v).upper() for v in likely_goahead_filter]:
            # If ALL is selected, don't filter
            likely_filter = ""
        else:
            # Normalize filter values
            selected_statuses = []
            for v in likely_goahead_filter:
                v_up = str(v).upper()
                if v_up == 'Y':
                    selected_statuses.append('Y')
                elif v_up == 'N':
                    selected_statuses.append('N')
                elif v_up.startswith('U'):
                    selected_statuses.append('UNCERTAIN')
                elif v_up == 'EMPTY' or v == '':
                    selected_statuses.append('')
            
            if selected_statuses:
                # Build OR conditions for likely_goahead
                conditions = []
                for idx, status in enumerate(selected_statuses):
                    param_name = f'likely_{idx}'
                    if status == 'Y':
                        conditions.append(f"COALESCE(TRIM(a.likely_goahead), '') LIKE 'Y%'")
                    elif status == 'N':
                        conditions.append(f"COALESCE(TRIM(a.likely_goahead), '') LIKE 'N%'")
                    elif status == 'UNCERTAIN' or status == 'U':
                        conditions.append(f"COALESCE(TRIM(a.likely_goahead), '') LIKE 'U%'")
                    elif status == '':
                        conditions.append(f"COALESCE(TRIM(a.likely_goahead), '') = ''")
                
                if conditions:
                    likely_filter = "AND (" + " OR ".join(conditions) + ")"
                else:
                    # No valid statuses - return no data
                    likely_filter = "AND 1=0"
            else:
                # No valid statuses - return no data
                likely_filter = "AND 1=0"
    
    # Build company_pc calculation based on company_id
    company_pc_case = ""
    if company_id:
        company_pc_case = f"""
            CASE
                WHEN a.operator_id = {company_id} THEN a.operator_pc
                WHEN a.partner1_id = {company_id} THEN a.partner1_pc
                WHEN a.partner2_id = {company_id} THEN a.partner2_pc
                WHEN a.partner3_id = {company_id} THEN a.partner3_pc
                WHEN a.partner4_id = {company_id} THEN a.partner4_pc
                WHEN a.partner5_id = {company_id} THEN a.partner5_pc
                ELSE 0
            END AS company_pc"""
    else:
        company_pc_case = "a.operator_pc AS company_pc"
    
    query = f"""
    WITH base AS (
        SELECT
            a.project_id,
            a.project_name,
            c.country_long_name AS country,
            COALESCE(TRIM(a.likely_goahead), '') AS likely_goahead,
            {company_pc_case},
            est."2024_Q1", est."2024_Q2", est."2024_Q3", est."2024_Q4",
            est."2025_Q1", est."2025_Q2", est."2025_Q3", est."2025_Q4",
            est."2026_Q1", est."2026_Q2", est."2026_Q3", est."2026_Q4",
            est."2027_Q1", est."2027_Q2", est."2027_Q3", est."2027_Q4",
            est."2028_Q1", est."2028_Q2", est."2028_Q3", est."2028_Q4",
            est."2029_Q1", est."2029_Q2", est."2029_Q3", est."2029_Q4"
        FROM fact_upstream_project_tracker a
        LEFT JOIN fact_upstream_tracker_prod_estimates est
            ON a.project_id = est.project_id
        LEFT JOIN dim_country c
            ON a.country_id = c.dim_country_id
        WHERE a.include = TRUE
            {company_filter}
            {likely_filter}
    ),
    unpvt AS (
        SELECT
            country,
            likely_goahead,
            company_pc,
            SPLIT_PART(qtr, '_', 1)::INT AS year_of_period,
            SPLIT_PART(qtr, '_', 2) AS quarter_of_period,
            value AS production_value
        FROM base
        CROSS JOIN LATERAL (
            VALUES
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
        ) AS t(qtr, value)
    )
    SELECT
        year_of_period AS "Year of Period",
        quarter_of_period AS "Quarter of Period",
        country AS "Country",
        SUM((production_value * company_pc) / 100.0) AS value_company,
        CASE
            WHEN country = 'Algeria' THEN '#a0cbe8'
            WHEN country = 'Angola' THEN '#4e79a7'
            WHEN country = 'Argentina' THEN '#f28e2b'
            WHEN country = 'Australia' THEN '#ffbe7d'
            WHEN country = 'Azerbaijan' THEN '#8cd17d'
            WHEN country = 'Brazil' THEN '#d7b5a6'
            WHEN country = 'Brunei' THEN '#f1ce63'
            WHEN country = 'Cameroon' THEN '#e15759'
            WHEN country = 'Canada' THEN '#86bcb6'
            WHEN country = 'China' THEN '#79706e'
            WHEN country = 'Cote d''Ivoire' THEN '#d37295'
            WHEN country = 'Denmark' THEN '#d37295'
            WHEN country = 'Egypt' THEN '#b07aa1'
            WHEN country = 'Gabon' THEN '#d4a6c8'
            WHEN country = 'Ghana' THEN '#9d7660'
            WHEN country = 'Guyana' THEN '#76b7b2'
            WHEN country = 'India' THEN '#76b7b2'
            WHEN country = 'Indonesia' THEN '#4e79a7'
            WHEN country = 'Iran' THEN '#a0cbe8'
            WHEN country = 'Iraq' THEN '#9c755f'
            WHEN country = 'Kazakhstan' THEN '#59a14f'
            WHEN country = 'Kuwait' THEN '#b6992d'
            WHEN country = 'Libya' THEN '#76b7b2'
            WHEN country = 'Malaysia' THEN '#86bcb6'
            WHEN country = 'Mexico' THEN '#76b7b2'
            WHEN country = 'Namibia' THEN '#79706e'
            WHEN country = 'Neutral Zone' THEN '#79706e'
            WHEN country = 'Niger' THEN '#bab0ac'
            WHEN country = 'Nigeria' THEN '#59a14f'
            WHEN country = 'Norway' THEN '#b07aa1'
            WHEN country = 'Oman' THEN '#9c755f'
            WHEN country = 'Qatar' THEN '#4e79a7'
            WHEN country = 'Russia' THEN '#4e79a7'
            WHEN country = 'Saudi Arabia' THEN '#8cd17d'
            WHEN country = 'Senegal' THEN '#f28e2b'
            WHEN country = 'Suriname' THEN '#bab0ac'
            WHEN country = 'Thailand' THEN '#f1ce63'
            WHEN country = 'Trinidad and Tobago' THEN '#f1ce63'
            WHEN country = 'Turkey' THEN '#8cd17d'
            WHEN country = 'Turkmenistan' THEN '#8cd17d'
            WHEN country = 'Uganda' THEN '#e15759'
            WHEN country = 'United Arab Emirates' THEN '#edc948'
            WHEN country = 'United Kingdom' THEN '#b07aa1'
            WHEN country = 'United States' THEN '#ff9da7'
            WHEN country = 'Vietnam' THEN '#499894'
            ELSE NULL
        END AS "Country Color"
    FROM unpvt
    GROUP BY
        year_of_period,
        quarter_of_period,
        country
    ORDER BY
        country,
        quarter_of_period;
    """
    
    try:
        results = execute_query(query, params if params else None)
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        df.columns = df.columns.str.strip()
        df['value_company'] = pd.to_numeric(df['value_company'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        print(f"Error loading chart data: {e}")
        return pd.DataFrame()


def load_map_data(company_name=None, likely_goahead_filter=None):
    """Load map data from database using Query 2 (yearly aggregated data for map)."""
    # Build query conditionally based on filters
    company_filter = ""
    likely_filter = ""
    params = {}
    
    # Get company_id from company_name if provided
    company_id = None
    if company_name:
        try:
            company_id_query = "SELECT company_id FROM dim_company WHERE company_name = :company_name LIMIT 1"
            company_result = execute_query(company_id_query, {'company_name': company_name})
            if company_result and len(company_result) > 0:
                company_id = company_result[0]['company_id']
        except Exception as e:
            print(f"Error getting company_id: {e}")
    
    if company_id:
        company_filter = "AND :company_id IN (a.operator_id, a.partner1_id, a.partner2_id, a.partner3_id, a.partner4_id, a.partner5_id)"
        params['company_id'] = company_id
    
    # Build likely_goahead filter
    if likely_goahead_filter is not None and isinstance(likely_goahead_filter, list):
        if len(likely_goahead_filter) == 0:
            # Empty list means all checkboxes unchecked - return no data
            likely_filter = "AND 1=0"  # This will match nothing
        elif 'ALL' in [str(v).upper() for v in likely_goahead_filter]:
            # If ALL is selected, don't filter
            likely_filter = ""
        else:
            # Normalize filter values
            selected_statuses = []
            for v in likely_goahead_filter:
                v_up = str(v).upper()
                if v_up == 'Y':
                    selected_statuses.append('Y')
                elif v_up == 'N':
                    selected_statuses.append('N')
                elif v_up.startswith('U'):
                    selected_statuses.append('UNCERTAIN')
                elif v_up == 'EMPTY' or v == '':
                    selected_statuses.append('')
            
            if selected_statuses:
                # Build OR conditions for likely_goahead
                conditions = []
                for idx, status in enumerate(selected_statuses):
                    if status == 'Y':
                        conditions.append(f"COALESCE(TRIM(a.likely_goahead), '') LIKE 'Y%'")
                    elif status == 'N':
                        conditions.append(f"COALESCE(TRIM(a.likely_goahead), '') LIKE 'N%'")
                    elif status == 'UNCERTAIN' or status == 'U':
                        conditions.append(f"COALESCE(TRIM(a.likely_goahead), '') LIKE 'U%'")
                    elif status == '':
                        conditions.append(f"COALESCE(TRIM(a.likely_goahead), '') = ''")
                
                if conditions:
                    likely_filter = "AND (" + " OR ".join(conditions) + ")"
                else:
                    # No valid statuses - return no data
                    likely_filter = "AND 1=0"
            else:
                # No valid statuses - return no data
                likely_filter = "AND 1=0"
    
    # Build company_pc calculation based on company_id
    company_pc_case = ""
    if company_id:
        company_pc_case = f"""
            CASE
                WHEN a.operator_id = {company_id} THEN a.operator_pc
                WHEN a.partner1_id = {company_id} THEN a.partner1_pc
                WHEN a.partner2_id = {company_id} THEN a.partner2_pc
                WHEN a.partner3_id = {company_id} THEN a.partner3_pc
                WHEN a.partner4_id = {company_id} THEN a.partner4_pc
                WHEN a.partner5_id = {company_id} THEN a.partner5_pc
                ELSE 0
            END AS company_pc"""
    else:
        company_pc_case = "a.operator_pc AS company_pc"
    
    query = f"""
    WITH base AS (
        SELECT
            a.project_id,
            c.country_long_name AS country,
            c.region,
            c.latitude,
            c.longitude,
            COALESCE(TRIM(a.likely_goahead), '') AS likely_goahead,
            {company_pc_case},
            est."2024_Q1", est."2024_Q2", est."2024_Q3", est."2024_Q4",
            est."2025_Q1", est."2025_Q2", est."2025_Q3", est."2025_Q4",
            est."2026_Q1", est."2026_Q2", est."2026_Q3", est."2026_Q4",
            est."2027_Q1", est."2027_Q2", est."2027_Q3", est."2027_Q4",
            est."2028_Q1", est."2028_Q2", est."2028_Q3", est."2028_Q4",
            est."2029_Q1", est."2029_Q2", est."2029_Q3", est."2029_Q4"
        FROM fact_upstream_project_tracker a
        LEFT JOIN fact_upstream_tracker_prod_estimates est
            ON a.project_id = est.project_id
        LEFT JOIN dim_country c
            ON a.country_id = c.dim_country_id 
        WHERE a.include = TRUE
            {company_filter}
            {likely_filter}
    ),
    unpvt AS (
        SELECT
            country,
            region,
            latitude,
            longitude,
            likely_goahead,
            company_pc,
            SPLIT_PART(qtr, '_', 1)::INT AS year_of_period,
            value AS production_value
        FROM base
        CROSS JOIN LATERAL (
            VALUES
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
        ) AS t(qtr, value)
    )
    SELECT
        year_of_period AS "Year of Period",
        country AS "Country",
        region AS "Region",
        AVG(latitude) AS "Latitude",
        AVG(longitude) AS "Longitude",
        SUM((production_value * company_pc) / 100.0) AS value_company
    FROM unpvt
    GROUP BY
        year_of_period,
        country,
        region
    ORDER BY
        value_company DESC NULLS LAST;
    """
    
    try:
        results = execute_query(query, params if params else None)
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        df.columns = df.columns.str.strip()
        df['value_company'] = pd.to_numeric(df['value_company'], errors='coerce').fillna(0)
        
        # Add ISO codes for map
        df['iso_alpha'] = df['Country'].apply(get_iso_code)
        
        return df
    except Exception as e:
        print(f"Error loading map data: {e}")
        return pd.DataFrame()


def get_unique_companies():
    """Get unique companies from database for dropdown filter (includes operators and partners)."""
    query = """
    SELECT DISTINCT company_name
    FROM (
        SELECT op.company_name AS company_name
        FROM fact_upstream_project_tracker a
        LEFT JOIN dim_company op ON a.operator_id = op.company_id
        WHERE a.include = TRUE
            AND op.company_name IS NOT NULL
            AND TRIM(op.company_name) != ''
        UNION
        SELECT p1.company_name AS company_name
        FROM fact_upstream_project_tracker a
        LEFT JOIN dim_company p1 ON a.partner1_id = p1.company_id
        WHERE a.include = TRUE
            AND p1.company_name IS NOT NULL
            AND TRIM(p1.company_name) != ''
        UNION
        SELECT p2.company_name AS company_name
        FROM fact_upstream_project_tracker a
        LEFT JOIN dim_company p2 ON a.partner2_id = p2.company_id
        WHERE a.include = TRUE
            AND p2.company_name IS NOT NULL
            AND TRIM(p2.company_name) != ''
        UNION
        SELECT p3.company_name AS company_name
        FROM fact_upstream_project_tracker a
        LEFT JOIN dim_company p3 ON a.partner3_id = p3.company_id
        WHERE a.include = TRUE
            AND p3.company_name IS NOT NULL
            AND TRIM(p3.company_name) != ''
        UNION
        SELECT p4.company_name AS company_name
        FROM fact_upstream_project_tracker a
        LEFT JOIN dim_company p4 ON a.partner4_id = p4.company_id
        WHERE a.include = TRUE
            AND p4.company_name IS NOT NULL
            AND TRIM(p4.company_name) != ''
        UNION
        SELECT p5.company_name AS company_name
        FROM fact_upstream_project_tracker a
        LEFT JOIN dim_company p5 ON a.partner5_id = p5.company_id
        WHERE a.include = TRUE
            AND p5.company_name IS NOT NULL
            AND TRIM(p5.company_name) != ''
    ) all_companies
    ORDER BY company_name;
    """
    
    try:
        results = execute_query(query)
        if not results:
            return []
        companies = [row['company_name'] for row in results if row.get('company_name')]
        return sorted(companies)
    except Exception as e:
        print(f"Error loading companies: {e}")
        return []

# Quarter columns returned by the SQL query (used for chart, map, and table)
QUARTER_COLUMNS = [
    "2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4",
    "2025_Q1", "2025_Q2", "2025_Q3", "2025_Q4",
    "2026_Q1", "2026_Q2", "2026_Q3", "2026_Q4",
    "2027_Q1", "2027_Q2", "2027_Q3", "2027_Q4",
    "2028_Q1", "2028_Q2", "2028_Q3", "2028_Q4",
    "2029_Q1", "2029_Q2", "2029_Q3", "2029_Q4"
]

YEARS_FOR_CHART = list(range(2025, 2030))


def load_projects_data(company_name=None):
    """Load Projects by Company data directly from the database."""
    # Build query conditionally based on whether company_name is provided
    company_filter = ""
    params = {}
    
    # Get company_id from company_name if provided
    company_id = None
    if company_name:
        try:
            company_id_query = "SELECT company_id FROM dim_company WHERE company_name = :company_name LIMIT 1"
            company_result = execute_query(company_id_query, {'company_name': company_name})
            if company_result and len(company_result) > 0:
                company_id = company_result[0]['company_id']
        except Exception as e:
            print(f"Error getting company_id: {e}")
    
    if company_id:
        company_filter = "AND :company_id IN (a.operator_id, a.partner1_id, a.partner2_id, a.partner3_id, a.partner4_id, a.partner5_id)"
        params = {'company_id': company_id}
    
    # Build company_pc calculation based on company_id
    company_pc_case = ""
    if company_id:
        company_pc_case = f"CASE WHEN a.operator_id = {company_id} THEN a.operator_pc WHEN a.partner1_id = {company_id} THEN a.partner1_pc WHEN a.partner2_id = {company_id} THEN a.partner2_pc WHEN a.partner3_id = {company_id} THEN a.partner3_pc WHEN a.partner4_id = {company_id} THEN a.partner4_pc WHEN a.partner5_id = {company_id} THEN a.partner5_pc ELSE 0 END"
    else:
        company_pc_case = "a.operator_pc"
    
    # Build quarterly columns - multiply by company_pc/100.0 when company is selected
    if company_id:
        quarterly_cols = f"""
            (est."2024_Q1" * ({company_pc_case}) / 100.0) AS "2024_Q1",
            (est."2024_Q2" * ({company_pc_case}) / 100.0) AS "2024_Q2",
            (est."2024_Q3" * ({company_pc_case}) / 100.0) AS "2024_Q3",
            (est."2024_Q4" * ({company_pc_case}) / 100.0) AS "2024_Q4",
            (est."2025_Q1" * ({company_pc_case}) / 100.0) AS "2025_Q1",
            (est."2025_Q2" * ({company_pc_case}) / 100.0) AS "2025_Q2",
            (est."2025_Q3" * ({company_pc_case}) / 100.0) AS "2025_Q3",
            (est."2025_Q4" * ({company_pc_case}) / 100.0) AS "2025_Q4",
            (est."2026_Q1" * ({company_pc_case}) / 100.0) AS "2026_Q1",
            (est."2026_Q2" * ({company_pc_case}) / 100.0) AS "2026_Q2",
            (est."2026_Q3" * ({company_pc_case}) / 100.0) AS "2026_Q3",
            (est."2026_Q4" * ({company_pc_case}) / 100.0) AS "2026_Q4",
            (est."2027_Q1" * ({company_pc_case}) / 100.0) AS "2027_Q1",
            (est."2027_Q2" * ({company_pc_case}) / 100.0) AS "2027_Q2",
            (est."2027_Q3" * ({company_pc_case}) / 100.0) AS "2027_Q3",
            (est."2027_Q4" * ({company_pc_case}) / 100.0) AS "2027_Q4",
            (est."2028_Q1" * ({company_pc_case}) / 100.0) AS "2028_Q1",
            (est."2028_Q2" * ({company_pc_case}) / 100.0) AS "2028_Q2",
            (est."2028_Q3" * ({company_pc_case}) / 100.0) AS "2028_Q3",
            (est."2028_Q4" * ({company_pc_case}) / 100.0) AS "2028_Q4",
            (est."2029_Q1" * ({company_pc_case}) / 100.0) AS "2029_Q1",
            (est."2029_Q2" * ({company_pc_case}) / 100.0) AS "2029_Q2",
            (est."2029_Q3" * ({company_pc_case}) / 100.0) AS "2029_Q3",
            (est."2029_Q4" * ({company_pc_case}) / 100.0) AS "2029_Q4" """
    else:
        quarterly_cols = """
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
            est."2029_Q4" """
    
    query = f"""
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
            {quarterly_cols}
        FROM fact_upstream_project_tracker a
        LEFT JOIN fact_upstream_tracker_prod_estimates est 
            ON a.project_id = est.project_id
        LEFT JOIN dim_country c 
            ON a.country_id = c.dim_country_id
        LEFT JOIN dim_company op 
            ON a.operator_id = op.company_id
        LEFT JOIN dim_company p1 
            ON a.partner1_id = p1.company_id
        LEFT JOIN dim_company p2 
            ON a.partner2_id = p2.company_id
        LEFT JOIN dim_company p3 
            ON a.partner3_id = p3.company_id
        LEFT JOIN dim_company p4 
            ON a.partner4_id = p4.company_id
        LEFT JOIN dim_company p5 
            ON a.partner5_id = p5.company_id
        LEFT JOIN (
            SELECT 
                project_id,
                MIN(EXTRACT(YEAR FROM period)) AS year
            FROM fact_upstream_tracker_prod_estimates_incremental
            WHERE value IS NOT NULL 
            GROUP BY project_id
        ) yr ON yr.project_id = a.project_id
        LEFT JOIN dim_crude cr 
            ON cr.dim_crude_id = a.crude_id
        WHERE a.include = TRUE
            {company_filter}
        ORDER BY a.project_name;
    """

    try:
        results = execute_query(query, params if params else None)
        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)
        column_mapping = {
            'Project Name': 'Project Name',
            'project_name': 'Project Name',
            'likely_goahead': 'Likely Go-ahead',
            'Likely Go-ahead': 'Likely Go-ahead',
            'Country': 'Country',
            'country': 'Country',
            'country_long_name': 'Country',
            'Region': 'Region',
            'region': 'Region',
            'Opec_group': 'Group',
            'opec_group': 'Group',
            'field_type': 'Field Type',
            'Field Type': 'Field Type',
            'field': 'Field/Block',
            'Field': 'Field/Block',
            'play_type': 'Play Type',
            'Play Type': 'Play Type',
            'Hydrocarbon': 'Hydrocarbon',
            'hydrocarbon': 'Hydrocarbon',
            'Associated Crude': 'Associated Crude',
            'Depth': 'Depth',
            'depth': 'Depth',
            'Operator': 'Operator',
            'operator': 'Operator',
            'Partner1': 'Partner1',
            'partner1': 'Partner1',
            'Partner2': 'Partner2',
            'partner2': 'Partner2',
            'Partner3': 'Partner3',
            'partner3': 'Partner3',
            'Partner4': 'Partner4',
            'partner4': 'Partner4',
            'Partner5': 'Partner5',
            'partner5': 'Partner5',
            'First Oil Year': 'First Oil Year',
            'year': 'First Oil Year',
            'Sanctioned': 'Sanctioned',
            'sanctioned': 'Sanctioned',
            'Comments': 'Comments',
            'comments': 'Comments',
            'Project Status': 'Project Status',
            'project_status': 'Project Status',
            'Gas Reserves (mmboe)': 'Gas Reserves (mmboe)',
            'reserves_gas_mmboe': 'Gas Reserves (mmboe)',
            'Liquids Reserves (mmbbl)': 'Liquids Reserves (mmbbl)',
            'reserves_liquids_mmbbl': 'Liquids Reserves (mmbbl)',
            'Total Reserves (mmboe)': 'Total Reserves (mmboe)',
            'api_cat': 'API',
            'API': 'API',
            'sulfur_cat': 'Sulfur',
            'sulfur': 'Sulfur',
            'Sulfur': 'Sulfur',
            'operator_pc': 'Operator Share %',
            'partner1_pc': 'Partner1 Share %',
            'partner2_pc': 'Partner2 Share %',
            'partner3_pc': 'Partner3 Share %',
            'partner4_pc': 'Partner4 Share %',
            'partner5_pc': 'Partner5 Share %'
        }
        df = df.rename(columns=column_mapping)

        for col in QUARTER_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        non_quarter_cols = [c for c in df.columns if c not in QUARTER_COLUMNS]
        df[non_quarter_cols] = df[non_quarter_cols].fillna('')
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()


def build_quarterly_capacity(df):
    """Transform wide quarter columns into long format for the stacked bar chart."""
    if df.empty:
        return pd.DataFrame()

    records = []
    for _, row in df.iterrows():
        country = row.get('Country')
        if pd.isna(country) or not str(country).strip():
            continue
        for col in QUARTER_COLUMNS:
            if col not in df.columns:
                continue
            value = pd.to_numeric(row.get(col), errors='coerce')
            if pd.isna(value):
                value = 0
            year_part, quarter_part = col.split('_')
            try:
                year_int = int(year_part)
            except (TypeError, ValueError):
                continue
            if year_int not in YEARS_FOR_CHART:
                continue
            records.append({
                'Country': country,
                'Year of Period': year_int,
                'Quarter of Period': quarter_part.replace('Q', 'Q'),
                'value_company': value
            })

    return pd.DataFrame(records)


def build_map_data(quarter_df):
    """Aggregate quarterly data to yearly totals for the map."""
    if quarter_df.empty:
        return pd.DataFrame()
    try:
        return (
            quarter_df.groupby(['Country', 'Year of Period'])['value_company']
            .sum()
            .reset_index()
        )
    except Exception as e:
        print(f"Error building map data: {e}")
        return pd.DataFrame()


# Load data once at module level (will be reloaded when company changes)
PROJECTS_RAW_DF = load_projects_data()  # SQL – table only

# Get unique values for filters
def get_unique_years(company_name=None, likely_goahead_filter=None):
    """Get unique years from chart data for selected company and filters"""
    df = load_chart_data(company_name, likely_goahead_filter)
    if df.empty:
        return []
    return sorted(df['Year of Period'].unique().tolist())

def get_unique_countries(company_name=None):
    """Get unique countries from chart data for selected company (for filtering)"""
    df = load_chart_data(company_name)
    if df.empty:
        return []
    countries = sorted([c for c in df['Country'].unique().tolist() if pd.notna(c) and str(c).strip()])
    return countries

def get_all_unique_countries():
    """Get ALL unique countries from database (for country list display, regardless of filters)"""
    query = """
    SELECT DISTINCT c.country_long_name AS country
    FROM fact_upstream_project_tracker a
    LEFT JOIN dim_country c
        ON a.country_id = c.dim_country_id
    WHERE a.include = TRUE
        AND c.country_long_name IS NOT NULL
        AND TRIM(c.country_long_name) != ''
    ORDER BY c.country_long_name;
    """
    
    try:
        results = execute_query(query)
        if not results:
            return []
        countries = [row['country'] for row in results if row.get('country')]
        return sorted(countries)
    except Exception as e:
        print(f"Error loading all countries: {e}")
        return []

def get_all_unique_countries_with_colors():
    """Get ALL unique countries from database with colors from query (returns dict of country -> color)
    Same pattern as projects_by_country.py - colors come from SQL query using COUNTRY_COLORS mapping"""
    query = """
    SELECT DISTINCT 
        c.country_long_name AS country,
        CASE
            WHEN c.country_long_name = 'Algeria' THEN '#a0cbe8'
            WHEN c.country_long_name = 'Angola' THEN '#4e79a7'
            WHEN c.country_long_name = 'Argentina' THEN '#f28e2b'
            WHEN c.country_long_name = 'Australia' THEN '#ffbe7d'
            WHEN c.country_long_name = 'Azerbaijan' THEN '#8cd17d'
            WHEN c.country_long_name = 'Brazil' THEN '#d7b5a6'
            WHEN c.country_long_name = 'Brunei' THEN '#f1ce63'
            WHEN c.country_long_name = 'Cameroon' THEN '#e15759'
            WHEN c.country_long_name = 'Canada' THEN '#86bcb6'
            WHEN c.country_long_name = 'China' THEN '#79706e'
            WHEN c.country_long_name = 'Cote d''Ivoire' THEN '#d37295'
            WHEN c.country_long_name = 'Denmark' THEN '#d37295'
            WHEN c.country_long_name = 'Egypt' THEN '#b07aa1'
            WHEN c.country_long_name = 'Gabon' THEN '#d4a6c8'
            WHEN c.country_long_name = 'Ghana' THEN '#9d7660'
            WHEN c.country_long_name = 'Guyana' THEN '#76b7b2'
            WHEN c.country_long_name = 'India' THEN '#76b7b2'
            WHEN c.country_long_name = 'Indonesia' THEN '#4e79a7'
            WHEN c.country_long_name = 'Iran' THEN '#a0cbe8'
            WHEN c.country_long_name = 'Iraq' THEN '#9c755f'
            WHEN c.country_long_name = 'Kazakhstan' THEN '#59a14f'
            WHEN c.country_long_name = 'Kuwait' THEN '#b6992d'
            WHEN c.country_long_name = 'Libya' THEN '#76b7b2'
            WHEN c.country_long_name = 'Malaysia' THEN '#86bcb6'
            WHEN c.country_long_name = 'Mexico' THEN '#76b7b2'
            WHEN c.country_long_name = 'Namibia' THEN '#79706e'
            WHEN c.country_long_name = 'Neutral Zone' THEN '#79706e'
            WHEN c.country_long_name = 'Niger' THEN '#bab0ac'
            WHEN c.country_long_name = 'Nigeria' THEN '#59a14f'
            WHEN c.country_long_name = 'Norway' THEN '#b07aa1'
            WHEN c.country_long_name = 'Oman' THEN '#9c755f'
            WHEN c.country_long_name = 'Qatar' THEN '#4e79a7'
            WHEN c.country_long_name = 'Russia' THEN '#4e79a7'
            WHEN c.country_long_name = 'Saudi Arabia' THEN '#8cd17d'
            WHEN c.country_long_name = 'Senegal' THEN '#f28e2b'
            WHEN c.country_long_name = 'Suriname' THEN '#bab0ac'
            WHEN c.country_long_name = 'Thailand' THEN '#f1ce63'
            WHEN c.country_long_name = 'Trinidad and Tobago' THEN '#f1ce63'
            WHEN c.country_long_name = 'Turkey' THEN '#8cd17d'
            WHEN c.country_long_name = 'Turkmenistan' THEN '#8cd17d'
            WHEN c.country_long_name = 'Uganda' THEN '#e15759'
            WHEN c.country_long_name = 'United Arab Emirates' THEN '#edc948'
            WHEN c.country_long_name = 'United Kingdom' THEN '#b07aa1'
            WHEN c.country_long_name = 'United States' THEN '#ff9da7'
            WHEN c.country_long_name = 'Vietnam' THEN '#499894'
            ELSE NULL
        END AS country_color
    FROM fact_upstream_project_tracker a
    LEFT JOIN dim_country c
        ON a.country_id = c.dim_country_id
    WHERE a.include = TRUE
        AND c.country_long_name IS NOT NULL
        AND TRIM(c.country_long_name) != ''
    ORDER BY c.country_long_name;
    """
    
    try:
        results = execute_query(query)
        if not results:
            return {}
        # Return dict of country -> color (same pattern as projects_by_country.py)
        country_color_map = {}
        for row in results:
            country = row.get('country')
            color = row.get('country_color')
            if country:
                # Use color from query if available, otherwise fallback to get_country_color
                country_color_map[country] = color if color else get_country_color(country)
        return country_color_map
    except Exception as e:
        print(f"Error loading countries with colors: {e}")
        return {}

def get_unique_quarters():
    """Get unique quarters"""
    return ['Q1', 'Q2', 'Q3', 'Q4']

# Color palette for countries (matching Tableau dashboard exactly)
COUNTRY_COLORS = {
   'Algeria': '#a0cbe8',  # light blue
    'Angola': '#4e79a7',  # orange (matching Tableau dashboard)
    'Argentina': '#f28e2b',  # orange
    'Australia': '#ffbe7d',  # light orange/peach
    'Azerbaijan': '#8cd17d',  # light green
    'Brazil': '#d7b5a6', #light brown/tan
    'Brunei': '#f1ce63',  # yellow
    'Cameroon': '#e15759',  # red
    'Canada': '#86bcb6',  # teal/light blue-green
    'China': '#79706e',  # dark grey
    'Cote d\'Ivoire': '#d37295',  # pink
    'Denmark': '#d37295',  # dark pink
    'Egypt': '#b07aa1',  # muted purple (plum)
    'Gabon': '#d4a6c8',  # very light pink/peach
    'Ghana': '#9d7660',  # dark reddish-brown (saddle brown)
    'Guyana': '#76b7b2',  # distinct teal/turquoise (matching Tableau)
    'India': '#76b7b2',  # light sky blue
    'Indonesia': '#4e79a7',  # dark, rich blue
    'Iran': '#a0cbe8',  # very pale, almost white-blue (alice blue)
    'Iraq': '#9c755f',  # medium brown (peru)
    'Kazakhstan': '#59a14f',  # dark turquoise/teal (matching Tableau - shown as green in bars)
    'Kuwait': '#b6992d',  # mustard yellow/gold
    'Libya': '#76b7b2',  # light, slightly desaturated teal/green (medium turquoise)
    'Malaysia': '#86bcb6',  # dark forest green
    'Mexico': '#76b7b2' ,  # light, slightly desaturated teal/green (medium turquoise)
    'Namibia': '#79706e',  # light, slightly desaturated teal/green (medium turquoise)
    'Neutral Zone': '#79706e',  # light, slightly desaturated teal/green (medium turquoise)
    'Niger': '#bab0ac',  # light, slightly desaturated teal/green (medium turquoise)
    'Nigeria': '#59a14f',  # light, slightly desaturated teal/green (medium turquoise)
    'Norway': '#b07aa1',  # light, slightly desaturated teal/green (medium turquoise)
    'Oman': '#9c755f',  # light, slightly desaturated teal/green (medium turquoise)
    'Qatar': '#4e79a7',  # medium purple
    'Russia': '#4e79a7',  # light, slightly desaturated teal/green (medium turquoise)
    'Saudi Arabia': '#8cd17d',  # light, slightly desaturated teal/green (medium turquoise)
    'Senegal': '#f28e2b',  # light, slightly desaturated teal/green (medium turquoise)
    'Suriname': '#bab0ac',  # light, slightly desaturated teal/green (medium turquoise)
    'Thailand': '#f1ce63',  # light, slightly desaturated teal/green (medium turquoise)
    'Trinidad and Tobago': '#f1ce63',  # light, slightly desaturated teal/green (medium turquoise)
    'Turkey': '#8cd17d',  # light, slightly desaturated teal/green (medium turquoise)
    'Turkmenistan': '#8cd17d',  # light, slightly desaturated teal/green (medium turquoise)
    'Uganda': '#e15759',  # light, slightly desaturated teal/green (medium turquoise)
    'United Arab Emirates': '#edc948',  # light, slightly desaturated teal/green (medium turquoise)
    'United Kingdom': '#b07aa1',  # light, slightly desaturated teal/green (medium turquoise)
    'United States': '#ff9da7',  # dodger blue
    'Vietnam': '#499894',  # light sea green
}

def get_country_color(country):
    """Get color for a country, assign default if not in palette"""
    if country in COUNTRY_COLORS:
        return COUNTRY_COLORS[country]
    # Generate a color based on hash for countries not in palette
    import hashlib
    hash_obj = hashlib.md5(str(country).encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    # Generate a color from hash
    r = (hash_int & 0xFF0000) >> 16
    g = (hash_int & 0xFF00) >> 8
    b = hash_int & 0xFF
    return f'rgb({r}, {g}, {b})'

def apply_opacity_to_color(color, opacity):
    """Return RGBA color string with the requested opacity; fall back to the original color on error."""
    try:
        if isinstance(color, str) and color.startswith('#') and len(color) == 7:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            return f'rgba({r},{g},{b},{opacity})'
        if isinstance(color, str) and color.startswith('rgb(') and color.endswith(')'):
            parts = color[4:-1].split(',')
            if len(parts) == 3:
                r, g, b = [int(p.strip()) for p in parts]
                return f'rgba({r},{g},{b},{opacity})'
    except Exception:
        pass
    return color

def create_stacked_bar_chart(df, selected_company="Exxon Mobil", selected_countries=None, highlight_year=None, highlight_quarter=None):
    """Create stacked bar chart showing quarterly capacity by country"""
    if selected_countries is None:
        selected_countries = []
    
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            height=500,
            plot_bgcolor='white',
            paper_bgcolor='white',
            title={
                'text': f"Oil Projects Capacity Start Up by {selected_company} ('000 b/d)*",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'family': 'Arial, sans-serif', 'color': '#FF8C42'}
            }
        )
        return fig
    
    # Use the provided df which is already filtered by company
    original_df = df.copy()
    
    # Create period labels on the full dataset first
    if 'Period' not in original_df.columns:
        original_df['Period'] = original_df['Year of Period'].astype(str) + ' ' + original_df['Quarter of Period']
    
    # Create a sort key for proper chronological ordering
    quarter_order = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
    if 'SortKey' not in original_df.columns:
        original_df['SortKey'] = original_df['Year of Period'] * 10 + original_df['Quarter of Period'].map(quarter_order)
        original_df = original_df.sort_values(['SortKey'])
    
    # Always show ALL countries in the chart (not just selected ones)
    # Selected countries will be highlighted, non-selected will be greyed out but still visible
    all_countries_in_data = [c for c in original_df['Country'].unique().tolist() if pd.notna(c) and str(c).strip()]
    
    # Always use the full original data - don't filter countries out
    # Instead, we'll apply opacity to non-selected countries in the chart rendering
    df = original_df.copy()
    
    # Generate all possible periods from min year to max year (to ensure all quarters are shown)
    # Use the full data range (2025-2029) to show all quarters consistently
    all_periods = []
    for year in range(2025, 2030):
        for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
            all_periods.append(f"{year} {quarter}")
    periods = all_periods
    
    # Define stacking order to match Tableau visualization
    # In stacked bar charts, the order matters - countries are stacked from bottom to top
    # Based on the image, the typical order is: Kazakhstan (bottom), then others with data, then zeros on top
    # For proper stacking, we want countries with data first, then countries with zeros
    stacking_order = [
        'Kazakhstan', 'Guyana', 'Brazil', 'Azerbaijan', 'Indonesia', 'Angola', 
        'Qatar', 'Nigeria', 'Canada', 'China', 'Malaysia', 'Iran', 'Iraq',
        'Mexico', 'Libya', 'Niger', 'Kuwait', 'Algeria', 'Argentina', 'Australia',
        'Brunei', 'Cameroon', 'Cote d\'Ivoire', 'Denmark', 'Egypt', 'Gabon', 
        'Ghana', 'India', 'United States', 'United Kingdom', 'United Arab Emirates',
        'Uganda', 'Turkmenistan', 'Turkey', 'Trinidad and Tobago', 'Thailand',
        'Suriname', 'Senegal', 'Saudi Arabia', 'Russia', 'Oman', 'Norway',
        'Neutral Zone', 'Namibia', 'Vietnam', 'Ecuador'
    ]
    
    # Separate countries with data from countries with only zeros
    countries_with_data = []
    countries_with_zeros_only = []
    
    for country in all_countries_in_data:
        country_data = df[df['Country'] == country]
        if not country_data.empty and country_data['value_company'].sum() > 0:
            countries_with_data.append(country)
        else:
            countries_with_zeros_only.append(country)
    
    # Order countries with data according to stacking order
    ordered_with_data = [c for c in stacking_order if c in countries_with_data]
    remaining_with_data = [c for c in sorted(countries_with_data) if c not in stacking_order]
    
    # Order countries with zeros according to stacking order
    ordered_with_zeros = [c for c in stacking_order if c in countries_with_zeros_only]
    remaining_with_zeros = [c for c in sorted(countries_with_zeros_only) if c not in stacking_order]
    
    # Stack: countries with data first (bottom), then countries with zeros (top, but invisible)
    countries = ordered_with_data + remaining_with_data + ordered_with_zeros + remaining_with_zeros
    
    # Format periods for hover (Q1 2025 instead of 2025 Q1) - create once before loop
    hover_periods = [f"{p.split(' ')[1]} {p.split(' ')[0]}" for p in periods]
    
    # Create stacked bar chart
    fig = go.Figure()
    
    # Add a trace for each country
    for country in countries:
        # Always use the full df (which has Period column already created)
        # All countries are shown, but non-selected ones will be greyed out
        country_data = df[df['Country'] == country]
        # Get color from query result if available, otherwise fallback to get_country_color (same pattern as projects_by_country.py)
        if not country_data.empty and 'Country Color' in country_data.columns:
            base_color = country_data['Country Color'].iloc[0] if pd.notna(country_data['Country Color'].iloc[0]) else get_country_color(country)
        else:
            base_color = get_country_color(country)
        
        # Check if this country is selected (highlighted)
        # If no countries are selected (empty list), show all countries normally (not greyed out)
        # If countries are selected, only those are highlighted, others are greyed out
        if len(selected_countries) == 0:
            # No countries selected: show all countries normally
            is_selected = True
        else:
            # Some countries selected: only those are highlighted
            is_selected = country in selected_countries
        
        highlight_year_int = None
        highlight_quarter_label = None
        try:
            highlight_year_int = int(highlight_year) if highlight_year is not None else None
        except (ValueError, TypeError):
            highlight_year_int = None
        try:
            highlight_quarter_label = str(highlight_quarter) if highlight_quarter is not None else None
        except Exception:
            highlight_quarter_label = None
        
        values = []
        marker_colors = []
        for period in periods:
            period_data = country_data[country_data['Period'] == period]
            period_year = None
            try:
                period_year = int(str(period).split(' ')[0])
            except (ValueError, TypeError, AttributeError):
                period_year = None
            if not period_data.empty:
                values.append(period_data['value_company'].sum())
            else:
                # If no data for this period, set to 0
                values.append(0)
            
            # Apply year/quarter highlighting
            # Quarter highlighting applies to ALL countries (not just selected ones)
            # Year highlighting only applies to selected countries
            if highlight_quarter_label is not None:
                # Quarter highlighting: apply to all countries
                is_quarter_match = str(period).endswith(f" {highlight_quarter_label}")
                if is_quarter_match:
                    marker_colors.append(base_color)
                else:
                    marker_colors.append(apply_opacity_to_color(base_color, 0.18))
            elif is_selected and highlight_year_int is not None:
                # Year highlighting: only for selected countries
                is_year_match = (period_year == highlight_year_int)
                if is_year_match:
                    marker_colors.append(base_color)
                else:
                    marker_colors.append(apply_opacity_to_color(base_color, 0.18))
            else:
                # No highlighting: use base color
                marker_colors.append(base_color)
        
        # Determine overall opacity for the trace
        # Non-selected countries should be visible but greyed out (disabled)
        # Selected countries should be fully visible
        if not is_selected: 
            # Non-selected countries: greyed out but still visible (not hidden)
            trace_opacity = 0.3
        else:
            # Selected countries: full opacity (or minimal for zero values to maintain hover)
            trace_opacity = 1.0 if any(v > 0 for v in values) else 0.01
        
        # Always create a trace for all countries, even if all values are 0
        # This ensures the chart structure is maintained and tooltips work for countries with zeros
        # In stacked bar charts, traces with zeros are still part of the stack and show in tooltips
        # Countries with zeros will be hoverable even though they don't show visually
        fig.add_trace(go.Bar(
            name=country,
            x=periods,
            y=values,
            marker_color=marker_colors if (highlight_quarter_label is not None or (is_selected and highlight_year_int is not None)) else base_color,
            customdata=hover_periods,
            meta=country,
            hovertemplate='Country: %{meta}<br>Period: %{customdata}<br>Production Additions (\'000 b/d): %{y:,.1f}<extra></extra>',
            showlegend=False,  # Hide legend - using sidebar legend instead
            marker_line_width=0,  # No border on bars
            # Apply opacity: selected countries full opacity, non-selected greyed out (disabled but visible)
            opacity=trace_opacity
        ))
    
    # Y-axis should be exactly 0-70 to match images exactly; extend slightly to host invisible click-capture markers.
    y_max = 70
    
    # Update layout to match exact image design
    fig.update_layout(
        barmode='stack',
        bargap=0.12,  # slight gap to mirror reference spacing
        height=520,
        plot_bgcolor='white',
        paper_bgcolor='white',
        title={
            'text': f"<b>Oil Projects Capacity Start Up by {selected_company} ('000 b/d)*</b>",
            'x': 0.0,
            'xanchor': 'left',
            'font': {'size': 18, 'family': 'Arial, sans-serif', 'color': '#FF8C42'},
            'y': 0.98
        },
        xaxis=dict(
            title='',
            tickangle=0,
            showgrid=True,
            gridcolor='#e0e0e0',
            tickfont=dict(size=11, color='#2c3e50'),
            tickmode='array',
            tickvals=periods,
            ticktext=[p.split(' ')[1] for p in periods],  # Show only quarters (Q1, Q2, etc.)
            categoryorder='array',
            categoryarray=periods
        ),
        yaxis=dict(
            title="'000 b/d",
            showgrid=True,
            gridcolor='#e0e0e0',
            tickfont=dict(size=11, color='#2c3e50'),
            range=[-5, y_max + 5],
            dtick=10,
            titlefont=dict(size=12, color='#2c3e50')
        ),
        showlegend=False,  # Hide legend in chart - using sidebar legend instead
        margin=dict(l=60, r=60, t=60, b=100),  # Reduced right margin since legend is in sidebar
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='white',
            bordercolor='#999999',
            font=dict(
                size=13,
                family='Arial, sans-serif',
                color='#000000'
            )
        )
    )
    
    # Add year annotations above quarter groups for full 2025–2029 span
    for year in range(2025, 2030):
        year_positions = [idx for idx, p in enumerate(periods) if p.startswith(f"{year} ")]
        if not year_positions:
            continue
        x_pos = sum(year_positions) / len(year_positions)  # center label across four quarters
        fig.add_annotation(
            x=x_pos,
            y=1.05,
            xref='x',
            yref='paper',
            text=str(year),
            showarrow=False,
            font=dict(size=12, color='#2c3e50'),
            xanchor='center'
        )
    
    # Add footnote to match reference design
    fig.add_annotation(
        text="*Only the company's stake in the project is included.",
        xref="paper",
        yref="paper",
        x=0.0,
        y=-0.08,
        showarrow=False,
        font=dict(size=11, color='#2c3e50'),
        xanchor='left',
        yanchor='top'
    )
    
    # Invisible traces to capture quarter and year clicks (so users can click labels/areas, not just bars).
    # Quarter capture: points aligned with every period positioned below x-axis labels for easy clicking.
    fig.add_trace(go.Scatter(
        x=periods,
        y=[-3] * len(periods),
        mode='markers',
        marker=dict(size=40, color='rgba(0,0,0,0)'),  # Larger invisible area for easier clicking
        hoverinfo='skip',
        showlegend=False,
        customdata=[p.split(' ')[1] for p in periods],  # Store quarter (Q1, Q2, Q3, Q4)
        name='quarter-click-capture'
    ))
    year_click_x = []
    for year in range(2025, 2030):
        # Use the second quarter slot as the click anchor (roughly centered).
        year_click_x.append(f"{year} Q2")
    fig.add_trace(go.Scatter(
        x=year_click_x,
        y=[y_max + 2] * len(year_click_x),
        mode='markers',
        marker=dict(size=24, color='rgba(0,0,0,0)'),
        hoverinfo='skip',
        showlegend=False,
        customdata=[str(y) for y in range(2025, 2030)],
        name='year-click-capture'
    ))
    
    return fig

def get_all_country_centroids():
    """Get centroids for ALL countries from dim_country for the map labels."""
    query = """
    SELECT 
        country_long_name AS "Country",
        latitude AS "Latitude",
        longitude AS "Longitude"
    FROM dim_country
    WHERE country_long_name IS NOT NULL
        AND latitude IS NOT NULL 
        AND longitude IS NOT NULL
    """
    try:
        results = execute_query(query)
        if not results:
            return pd.DataFrame()
        return pd.DataFrame(results)
    except Exception as e:
        print(f"Error loading country centroids: {e}")
        return pd.DataFrame()

def create_world_map(selected_year=2025, selected_company=None, likely_goahead_filter=None, selected_countries=None):
    """Create world map showing geographical distribution for selected year using standardized shared component."""
    if selected_countries is None:
        selected_countries = []
        
    # Load map data from database for selected company with filters
    map_df = load_map_data(selected_company, likely_goahead_filter)
    
    if map_df.empty:
        return create_empty_map(f"No data available for {selected_year}")
    
    # Filter by year
    year_df = map_df[map_df['Year of Period'] == selected_year].copy()
    
    if year_df.empty:
         return create_empty_map(f"No data available for {selected_year}")

    # Create a blue/teal color scale that matches the reference map
    colorscale = [
        [0.0, '#C7E8E4'],   # very light teal
        [0.16, '#A4DCD5'],  # light teal
        [0.32, '#7DC9C3'],  # medium-light teal
        [0.48, '#4FB2AF'],  # medium teal
        [0.64, '#2A94A1'],  # medium-dark teal
        [0.8, '#1F7A8A'],   # dark teal
        [1.0, '#1C6C7C']    # deepest teal
    ]
    
    # Aggregate by country 
    country_totals = year_df.groupby(['Country', 'iso_alpha'])['value_company'].sum().reset_index()
    country_totals.columns = ['Country', 'iso_alpha', 'Value']
    
    # Prepare data for standardized map
    locations = country_totals['iso_alpha'].tolist()
    z_values = country_totals['Value'].tolist()
    hover_text = [
        f"<b>{row['Country']}</b><br>Production Addition: {row['Value']:,.1f} '000 b/d" 
        for _, row in country_totals.iterrows()
    ]
    
    # Get centroids for labels (reuse existing logic but simplified)
    all_centroids = get_all_country_centroids()
    label_countries = [
        'Algeria', 'Angola', 'Argentina', 'Australia', 'Azerbaijan', 'Brazil', 'Brunei', 
        'Cameroon', 'Canada', 'China', "Cote d'Ivoire", 'Denmark', 'Egypt', 'Gabon', 
        'Ghana', 'Guyana', 'India', 'Indonesia', 'Iran', 'Iraq', 'Kazakhstan', 'Kuwait', 
        'Libya', 'Malaysia', 'Mexico', 'Namibia', 'Neutral Zone', 'Niger', 'Nigeria', 
        'Norway', 'Oman', 'Qatar', 'Russia', 'Saudi Arabia', 'Senegal', 'Suriname', 
        'Thailand', 'Trinidad and Tobago', 'Turkey', 'Turkmenistan', 'Uganda', 
        'United Arab Emirates', 'United Kingdom', 'United States', 'Vietnam'
    ]
    
    if not all_centroids.empty:
        all_centroids = all_centroids[all_centroids['Country'].isin(label_countries)]
    
    # Identify selected ISOs
    selected_iso = None
    other_isos = None
    if selected_countries and len(selected_countries) == 1:
        # Standard map highlights one country
        selected_country = selected_countries[0]
        selected_row = country_totals[country_totals['Country'] == selected_country]
        if not selected_row.empty:
            selected_iso = selected_row.iloc[0]['iso_alpha']
            other_isos = [iso for iso in locations if iso != selected_iso]
    
    # Use standardized map creation
    fig = create_choropleth_map(
        locations=locations,
        z_values=z_values,
        colorscale=colorscale,
        hover_text=hover_text,
        selected_country=selected_countries[0] if selected_countries and len(selected_countries) == 1 else None,
        selected_iso=selected_iso,
        other_isos=other_isos,
        countries_df=all_centroids,
        height=520,
        zmin=0.7,
        zmax=135.0
    )
    
    # Custom title update to match exact requirement
    fig.update_layout(
        title={
            'text': f"<b>Oil Projects Capacity Start Up by {selected_company} ('000 b/d)*- {selected_year}</b>",
            'x': 0.0,
            'xanchor': 'left',
            'y': 0.99,
            'yanchor': 'top',
            'font': {'size': 18, 'family': 'Arial, sans-serif', 'color': '#FF8C42'}
        },
        margin=dict(l=0, r=0, t=50, b=10) # Adjust top margin for title
    )
    
    # Add copyright annotation at bottom left
    fig.add_annotation(
        text="© 2025 Mapbox © OpenStreetMap",
        xref="paper",
        yref="paper",
        x=0.01,
        y=0.01,
        showarrow=False,
        font=dict(size=10, color='#888888', family='Arial, sans-serif'),
        xanchor='left',
        yanchor='bottom'
    )
    
    return fig

def create_layout():
    """Create layout for Projects by Company with filters, year controls, legend, chart, map and table."""
    df_table = PROJECTS_RAW_DF.copy()
    if df_table.empty:
        data_full = []
        tooltip_data = []
    else:
        data_full = df_table.fillna("").to_dict('records')
        tooltip_data = []
        for row in data_full:
            tip_row = {}
            comments_val = str(row.get('Comments', '') or '').strip()
            if comments_val and comments_val.lower() != 'nan':
                tip_row['Comments'] = {'value': comments_val, 'type': 'text'}
            tooltip_data.append(tip_row)
    
    # Years for filters / slider (will be updated dynamically based on company)
    # Use default values for initial layout (will be updated by callbacks)
    years = get_unique_years(None, None)
    if years:
        min_year = min(years)
        max_year = max(years)
        default_year = years[0]
    else:
        # Sensible fallback based on Tableau dashboard (2025–2029)
        min_year, max_year, default_year = 2025, 2029, 2025
    
    # Countries for legend - show ALL countries from database (not filtered)
    all_countries_from_data = get_all_unique_countries()
    legend_countries = (
        sorted(all_countries_from_data)
        if all_countries_from_data
        else sorted(list(COUNTRY_COLORS.keys()))
    )
    
    # Get country colors from query (everything in query only) - same pattern as projects_by_country.py
    country_colors_from_query = get_all_unique_countries_with_colors()

    # Build clickable legend items – these are targeted by the pattern-matching callbacks
    legend_items = []
    for country in legend_countries:
        # Use color from query if available, otherwise fallback to get_country_color (same pattern as projects_by_country.py)
        color = country_colors_from_query.get(country) if country_colors_from_query.get(country) else get_country_color(country)
        legend_items.append(
            html.Div(
                id={'type': 'country-item', 'index': country},
                children=[
                    html.Div(
                        style={
                            'width': '12px',
                            'height': '12px',
                            'backgroundColor': color,
                            'marginRight': '6px',
                            'borderRadius': '2px',
                            'flexShrink': '0'
                        }
                    ),
                    html.Span(
                        country,
                        style={
                            'fontSize': '12px',
                            'color': '#2c3e50',
                            'whiteSpace': 'nowrap'
                        }
                    )
                ],
                style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'marginBottom': '4px',
                    'padding': '2px 4px',
                    'cursor': 'pointer',
                    'borderRadius': '3px'
                }
            )
        )

    layout = html.Div([
        # Stores and interval used by callbacks
        dcc.Store(id='selected-countries-store', data=[]),
        dcc.Store(id='year-period-play-store', data=False),
        dcc.Store(id='bar-highlight-year-store', data=None),
        dcc.Store(id='quarter-highlight-store', data=None),
        dcc.Store(id='likely-filter-previous-store', data=[]),
        # Stores to keep full table data for filtering
        dcc.Store(id='projects-company-table-data-full', data=data_full if df_table is not None else []),
        
        # Download Components
        dcc.Download(id='projects-company-download-chart-csv'),
        dcc.Download(id='projects-company-download-map-csv'),
        dcc.Download(id='projects-company-download-table-csv'),
        dcc.Store(id='projects-company-table-tooltip-full', data=tooltip_data if df_table is not None else []),
        # Dummy target for clientside sort UI (adds A/Z hover like projects_latest)
        dcc.Store(id='projects-company-dummy-sort', data='', storage_type='memory'),
        dcc.Interval(
            id='year-period-interval',
            interval=2000,  # 2 seconds between steps when playing
            n_intervals=0,
            disabled=True
        ),
        
        # Top bar – only Company filter, matching Tableau
        html.Div([
            html.Label(
                "Company",
                style={
                    'fontSize': '12px',
                    'fontWeight': 'bold',
                    'color': '#1b365d',
                    'marginRight': '8px',
                    'whiteSpace': 'nowrap'
                }
            ),
            dcc.Dropdown(
                id='company-filter',
                options=[],
                value=None,
                clearable=False,
                placeholder="Select Company...",
                style={
                    'width': '100%'
                }
            )
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'gap': '8px',
            'width': '100%',
            'marginBottom': '0px'
        }),
        
        # Main content – chart/map on the left, legend & filters on the right
        html.Div([
            # LEFT COLUMN: bar chart and map
            html.Div([
                html.Div([
                     html.Button(
                        'Download Chart CSV',
                        id='projects-company-btn-download-chart',
                        n_clicks=0,
                        style={
                            'backgroundColor': 'white',
                            'color': '#2c3e50',
                            'border': '1px solid #dee2e6',
                            'padding': '4px 10px',
                            'borderRadius': '4px',
                            'cursor': 'pointer',
                            'fontSize': '11px',
                            'marginBottom': '5px',
                            'float': 'right'
                        }
                    )
                ], style={'width': '100%', 'display': 'block', 'height': '25px', 'marginBottom': '15px', 'marginTop': '15px'}),
                dcc.Graph(
                    id='projects-company-bar-chart',
                    style={'height': '520px', 'marginBottom': '30px'}
                ),
                html.Div([
                    html.Div([
                         html.Button(
                            'Download Map CSV',
                            id='projects-company-btn-download-map',
                            n_clicks=0,
                            style={
                                'backgroundColor': 'white',
                                'color': '#2c3e50',
                                'border': '1px solid #dee2e6',
                                'padding': '4px 10px',
                                'borderRadius': '4px',
                                'cursor': 'pointer',
                                'fontSize': '11px',
                                'marginBottom': '5px',
                                'float': 'right',
                                'zIndex': '10',
                                'position': 'relative'
                            }
                        )
                    ], style={'width': '100%', 'display': 'block', 'height': '25px', 'marginBottom': '15px', 'marginTop': '15px'}),
                    dcc.Graph(
                        id='projects-company-map',
                        style={
                            'height': '520px',
                            'width': '100%'
                        }
                    ),
                    html.Div([
                        html.Div(id='year-of-period-container', children=[
                            html.Label(
                                "Year of Period",
                            style={
                                'fontSize': '12px',
                                'fontWeight': 'bold',
                                'color': '#1b365d',
                                'display': 'block',
                                'marginBottom': '4px'
                            }
                        ),
                        html.Div([
                            html.Button(
                                '◀',
                                id='year-period-prev',
                                n_clicks=0,
                                style={
                                    'border': '1px solid #ffffff',
                                    # 'backgroundColor': '#f5a623',
                                    'color': '#000000',
                                    'padding': '2px 6px',
                                    'fontSize': '12px',
                                    'cursor': 'pointer'
                                }
                            ),
                            dcc.Dropdown(
                                id='year-of-period-filter',
                                options=[{'label': str(y), 'value': y} for y in years] if years else [],
                                value=default_year,
                                clearable=False,
                                style={'width': '120px'}
                            ),
                            html.Button(
                                '▶',
                                id='year-period-next',
                                n_clicks=0,
                                style={
                                    'border': '1px solid #ffffff',
                                    # 'backgroundColor': '#f5a623',
                                    'color': '#000000',
                                    'padding': '2px 6px',
                                    'fontSize': '12px',
                                    'cursor': 'pointer'
                                }
                            )
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '4px', 'marginBottom': '6px'}),
                        dcc.Slider(
                            id='year-period-slider',
                            min=min_year,
                            max=max_year,
                            step=1,
                            value=default_year,
                            marks={y: {'label': '|', 'style': {'color': '#666666', 'fontSize': '14px'}} for y in years} if years else {},
                            included=False
                        ),
                        html.Div([
                            html.Button(
                                '◀',
                                id='year-period-timeline-prev',
                                n_clicks=0,
                                style={
                                    'border': '1px solid #ffffff',
                                    # 'backgroundColor': '#f5a623',
                                    'color': '#000000',
                                    'padding': '2px 6px',
                                    'fontSize': '12px',
                                    'cursor': 'pointer'
                                }
                            ),
                            html.Button(
                                '■',
                                id='year-period-stop',
                                n_clicks=0,
                                style={
                                    'border': '1px solid #ffffff',
                                    'backgroundColor': '#000000',
                                    'color': '#ffffff',
                                    'padding': '2px 8px',
                                    'fontSize': '12px',
                                    'cursor': 'pointer'
                                }
                            ),
                            html.Button(
                                '▶',
                                id='year-period-play',
                                n_clicks=0,
                                style={
                                    'border': '1px solid #ffffff',
                                    # 'backgroundColor': '#f5a623',
                                    'color': '#000000',
                                    'padding': '2px 8px',
                                    'fontSize': '12px',
                                    'cursor': 'pointer'
                                }
                            )
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '6px', 'margin': '8px 0 6px'}),
                        dcc.Checklist(
                            id='show-history-checkbox',
                            options=[{'label': 'Show history', 'value': 'history'}],
                            value=[],
                            labelStyle={'fontSize': '12px'}
                        ),
                        ]),
                        html.Div([
                            html.Div(
                                "Production Additions ('000 b/d)",
                            style={
                                'fontSize': '11px',
                                'color': '#1b365d',
                                'marginBottom': '4px',
                                'fontFamily': 'Arial, sans-serif'
                            }
                        ),
                        html.Div(id='production-additions-content', children=[
                            html.Div(style={
                                'height': '14px',
                                'width': '210px',
                                'background': 'linear-gradient(to right, #C7E8E4, #A4DCD5, #7DC9C3, #4FB2AF, #2A94A1, #1F7A8A, #1C6C7C)',
                                'border': '1px solid #c5c5c5',
                                'borderRadius': '2px'
                            }),
                            html.Div([
                                html.Span('0.7', style={'fontSize': '10px', 'color': '#1b365d'}),
                                html.Span('135.0', style={'fontSize': '10px', 'color': '#1b365d', 'marginLeft': 'auto'})
                            ], style={
                                'display': 'flex',
                                'justifyContent': 'space-between',
                                'width': '210px',
                                'marginTop': '2px'
                            })
                        ])
                        ], id='production-additions-legend', style={'marginTop': '5px'}),
                        html.Div(
                            id='year-period-display',
                            style={'display': 'none'}
                        )
                    ], style={
                        'position': 'absolute',
                        'top': '10px',
                        'right': '-243px',
                        'backgroundColor': '#ffffff',
                        'padding': '8px 10px',
                        'border': '1px solid #dcdcdc',
                        'borderRadius': '4px',
                        'boxShadow': '0 1px 4px rgba(0, 0, 0, 0.12)',
                        'minWidth': '220px',
                        'zIndex': 5
                    })
                ], style={
                    'position': 'relative',
                    # 'height': '520px',  <-- Removed fixed height to allow auto-expansion
                    'marginBottom': '20px'
                })
            ], style={'flex': '4', 'minWidth': '0'}),
            
            # RIGHT COLUMN: legend, Likely To Go, year controls, history toggle
            html.Div([
                html.Div(
                    "Country",
                    style={
                        'fontWeight': 'bold',
                        'fontSize': '13px',
                        'color': '#1b365d',
                        'marginBottom': '4px'
                    }
                ),
                html.Div(
                    legend_items,
                    style={
                        'display': 'flex',
                        'flexDirection': 'column',
                        'flexWrap': 'nowrap',
                        'maxHeight': '260px',
                        'overflowY': 'auto',
                        'padding': '6px 8px',
                        'border': '1px solid #e0e0e0',
                        'borderRadius': '4px',
                        'backgroundColor': '#fafafa',
                        'marginBottom': '10px'
                    }
                ),
                
                html.Div([
                    html.Label(
                        "Likely To Go Ahead",
                        style={
                            'fontSize': '12px',
                            'fontWeight': 'bold',
                            'color': '#1b365d',
                            'display': 'block',
                            'marginBottom': '4px'
                        }
                    ),
                    dcc.Checklist(
                        id='likely-to-go-filter',
                        options=[
                            {'label': '(All)', 'value': 'ALL'},
                            {'label': '', 'value': 'EMPTY'},
                            {'label': 'N', 'value': 'N'},
                            {'label': 'Uncertain', 'value': 'UNCERTAIN'},
                            {'label': 'Y', 'value': 'Y'},
                        ],
                        value=['Y'],
                        labelStyle={
                            'display': 'block',
                            'fontSize': '12px',
                            'marginBottom': '2px'
                        }
                    )
                ], style={'marginBottom': '14px'}),
            ], style={
                'flex': '1',
                'minWidth': '260px',
                'maxWidth': '340px',
                'marginLeft': '20px'
            })
        ], style={
            'display': 'flex',
            'alignItems': 'flex-start'
        }),
        
        # Projects table – match design from projects_by_time
        html.Div([
            html.Div([
                html.H4(
                    "Projected Oil Capacity Details by Company",
                    style={
                        'marginBottom': '0',
                        'fontSize': '24px',
                        'fontWeight': 'bold',
                        'fontFamily': 'Georgia, serif',
                        'color': '#fe5000',
                        'textAlign': 'left'
                    }
                ),
                html.Button(
                    'Download Table CSV',
                    id='projects-company-btn-download-table',
                    n_clicks=0,
                    style={
                        'backgroundColor': 'white',
                        'color': '#2c3e50',
                        'border': '1px solid #dee2e6',
                        'padding': '4px 10px',
                        'borderRadius': '4px',
                        'cursor': 'pointer',
                        'fontSize': '11px',
                        'marginLeft': 'auto'
                    }
                )
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'marginBottom': '15px'}),
            dcc.Loading(
                id="loading-projects-company-table",
                type="default",
                children=dash_table.DataTable(
                    id='projects-company-table',
                    columns=[],
                    data=[],
                    tooltip_data=[],
                    tooltip_duration=None,
                    page_action='none',
                    sort_action='native',
                    filter_action='native',  # Native filtering shows filter inputs below headers
                    style_table={
                        'overflowX': 'auto',
                        'overflowY': 'auto',
                        'maxHeight': '600px',
                        'width': '100%',
                        'border': '1px solid #ddd'
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '8px',
                        'whiteSpace': 'nowrap',
                        'height': 'auto',
                        'overflow': 'hidden',
                        'textOverflow': 'ellipsis',
                        'maxWidth': '180px',
                        'fontSize': '12px',
                        'border': '1px solid #ddd',
                        'backgroundColor': '#fff',
                        'fontFamily': 'Georgia, serif',
                        'color': '#333333'
                    },
                    style_header={
                        'backgroundColor': '#ffffff',
                        'fontWeight': 'bold',
                        'fontFamily': 'Georgia, serif',
                        'color': '#333333',
                        'border': '1px solid #ddd',
                        'textAlign': 'left',
                        'whiteSpace': 'nowrap',
                        'height': 'auto',
                        'position': 'relative'
                    },
                    style_data={
                        'border': '1px solid #ddd',
                        'whiteSpace': 'nowrap',
                        'fontFamily': 'Georgia, serif',
                        'color': '#333333'
                    },
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'},
                        {
                            'if': {'column_id': 'Comments'},
                            'whiteSpace': 'nowrap',
                            'overflow': 'hidden',
                            'textOverflow': 'ellipsis',
                            'height': 'auto',
                            'textAlign': 'left'
                        }
                    ],
                    css=[{
                        'selector': '.dash-table-tooltip',
                        'rule': 'font-size: 10px !important; font-family: Georgia, serif !important; color: #333333 !important; max-width: 400px !important; white-space: normal !important; word-wrap: break-word !important; line-height: 1.4 !important; padding: 6px 8px !important;'
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
    ], style={'padding': '10px 18px'})
    return layout

def register_callbacks(dash_app, server):
    """Register all callbacks for Projects by Company"""
    
    # Get all countries from database for creating dynamic outputs
    # Show ALL countries regardless of filters (for country list display)
    all_countries_from_data = get_all_unique_countries()
    legend_countries = sorted(all_countries_from_data) if all_countries_from_data else sorted(list(COUNTRY_COLORS.keys()))
    
    # Create outputs for all country items
    country_outputs = [
        Output({'type': 'country-item', 'index': country}, 'style')
        for country in legend_countries
    ]
    
    @dash_app.callback(
        Output('selected-countries-store', 'data', allow_duplicate=True),
        Input({'type': 'country-item', 'index': ALL}, 'n_clicks'),
        State('selected-countries-store', 'data'),
        prevent_initial_call=True
    )
    def toggle_country(_clicks, selected_countries):
        """Toggle country selection on click"""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update
        
        # Get the triggered country
        triggered = ctx.triggered[0]["prop_id"]
        try:
            country_id = json.loads(triggered.split('.')[0])
            clicked_country = country_id.get("index")
        except (ValueError, TypeError, AttributeError, KeyError):
            return dash.no_update
        
        if not clicked_country or clicked_country not in legend_countries:
            return dash.no_update
        
        # Initialize selected_countries if None
        if selected_countries is None:
            selected_countries = []
        
        # Toggle the clicked country
        if clicked_country in selected_countries:
            # Deselect
            new_selected = [c for c in selected_countries if c != clicked_country]
        else:
            # Select
            new_selected = selected_countries + [clicked_country] if selected_countries else [clicked_country]
        
        return new_selected
    
    @dash_app.callback(
        Output('selected-countries-store', 'data', allow_duplicate=True),
        Input('projects-company-map', 'clickData'),
        State('selected-countries-store', 'data'),
        prevent_initial_call=True
    )
    def toggle_country_from_map(click_data, selected_countries):
        """Toggle country selection on map click using shared utility"""
        # Pass (All) if currently empty/none to match shared util expectations, 
        # though passing [] usually works if util treats empty as 'none selected' 
        # but generic util might differ. Let's pass current state as is.
        # Actually, shared util logic:
        # if "(All)" in current_filter -> resolved = all
        # else -> resolved = current filtered
        # 
        # If we pass [], resolved is []. 
        # Then it falls through to 'return [country]'. This is correct for selecting map item.
        # 
        # If we pass ['Angola'], resolved is ['Angola'].
        # Then len == 1 -> returns ["(All)"] + all.
        
        result = handle_map_click_reset(click_data, selected_countries, legend_countries)
        
        # Adapt result: if it contains "(All)", return empty list (standard for this app)
        if result and "(All)" in result:
            return []
            
        return result

    
    @dash_app.callback(
        country_outputs,
        Input('selected-countries-store', 'data'),
        prevent_initial_call=False
    )
    def update_country_styles(selected_countries):
        """Update country item styles based on store"""
        selected_countries = selected_countries or []
        styles = []
        for country in legend_countries:
            # If no countries are selected, show all countries normally (not greyed out)
            # If countries are selected, only those are highlighted, others are greyed out
            if len(selected_countries) == 0:
                is_selected = True  # Show all normally when none selected
            else:
                is_selected = country in selected_countries
            
            country_color = get_country_color(country)
            # Selected countries get a subtle background highlight. Non-selected countries are greyed out but still visible.
            if is_selected:
                # Selected country: highlighted with background color, no border
                styles.append({
                    'display': 'flex',
                    'alignItems': 'center',
                    'marginBottom': '4px',
                    'padding': '2px 4px',
                    'cursor': 'pointer',
                    'borderRadius': '3px',
                    'border': '1px solid transparent',
                    'backgroundColor': 'rgba(240, 240, 240, 0.5)',
                    'transition': 'all 0.2s ease',
                    'opacity': '1.0'
                })
            else:
                # Non-selected country: greyed out but still visible
                styles.append({
                    'display': 'flex',
                    'alignItems': 'center',
                    'marginBottom': '4px',
                    'padding': '2px 4px',
                    'cursor': 'pointer',
                    'borderRadius': '3px',
                    'border': '1px solid transparent',
                    'backgroundColor': 'transparent',
                    'transition': 'all 0.2s ease',
                    'opacity': '0.3'  # Grey out non-selected countries
                })
        return styles
    
    # Callback to handle quarter clicks from chart (clicking on quarter labels Q1, Q2, Q3, Q4)
    @dash_app.callback(
        Output('quarter-highlight-store', 'data', allow_duplicate=True),
        Input('projects-company-bar-chart', 'clickData'),
        State('quarter-highlight-store', 'data'),
        prevent_initial_call=True
    )
    def handle_quarter_label_click(click_data, current_quarter):
        """Handle quarter label clicks on the chart - clicking same quarter toggles it off"""
        if not click_data or 'points' not in click_data or not click_data['points']:
            return dash.no_update
        
        try:
            point = click_data['points'][0]
            y_pos = point.get('y', 0)
            
            # Get trace name from the point's curveNumber and figure data
            # Check if this is a quarter label click (y position < 0 indicates quarter label area)
            # The invisible scatter trace for quarter clicks is at y=-3
            if y_pos < 0:
                quarter_val = point.get('customdata')
                if quarter_val in ['Q1', 'Q2', 'Q3', 'Q4']:
                    # Toggle: if same quarter is already selected, clear it; otherwise select it
                    if current_quarter == quarter_val:
                        return None  # Clear selection
                    else:
                        return quarter_val  # Select this quarter
            else:
                # Check if clicked on a bar but want to extract quarter from x value
                # This allows clicking on bars to also select quarters
                x_val = point.get('x')
                if isinstance(x_val, str) and ' ' in x_val:
                    parts = x_val.split(' ')
                    if len(parts) > 1:
                        quarter_val = parts[1]
                        if quarter_val in ['Q1', 'Q2', 'Q3', 'Q4']:
                            # Toggle: if same quarter is already selected, clear it; otherwise select it
                            if current_quarter == quarter_val:
                                return None  # Clear selection
                            else:
                                return quarter_val  # Select this quarter
        except Exception:
            pass
        
        return dash.no_update
    
    # Initial callback to set year display
    @dash_app.callback(
        Output('year-period-display', 'children', allow_duplicate=True),
        Input('year-of-period-filter', 'value'),
        prevent_initial_call='initial_duplicate'
    )
    def initialize_year_display(year_value):
        """Initialize year display on page load"""
        if year_value:
            return str(year_value)
        years = get_unique_years(None, None)
        return str(years[0]) if years else '2025'
    
    # Normalize Likely To Go checklist: (All) selects all; unchecking (All) clears all checkboxes.
    @dash_app.callback(
        [Output('likely-to-go-filter', 'value'),
         Output('likely-filter-previous-store', 'data')],
        Input('likely-to-go-filter', 'value'),
        State('likely-filter-previous-store', 'data'),
        prevent_initial_call=True
    )
    def normalize_likely_to_go(selected, previous_selected):
        """Checklist behavior: (All) checks everything; unchecking (All) clears all checkboxes."""
        options_all = ['ALL', 'EMPTY', 'N', 'UNCERTAIN', 'Y']
        
        # Normalize inputs
        selected = selected or []
        previous_selected = previous_selected or []
        
        # Check if ALL was in previous selection but not in current selection
        # This means user unchecked ALL - clear all checkboxes
        had_all_before = 'ALL' in previous_selected
        has_all_now = 'ALL' in selected
        
        if had_all_before and not has_all_now:
            # User unchecked ALL - clear all checkboxes
            return [], []
        
        # Handle empty selection
        if not selected:
            return [], selected
        
        # If ALL is present, force all options on
        if 'ALL' in selected:
            return options_all, options_all
        
        # Otherwise keep the order and remove duplicates
        seen = []
        for v in selected:
            if v not in seen:
                seen.append(v)
        return seen, seen
    
    @dash_app.callback(
        [Output('projects-company-table', 'data'),
         Output('projects-company-table', 'tooltip_data'),
         Output('projects-company-table', 'columns'),
         Output('projects-company-table-data-full', 'data', allow_duplicate=True),
         Output('projects-company-table-tooltip-full', 'data', allow_duplicate=True)],
        [Input('company-filter', 'value'),
         Input('likely-to-go-filter', 'value'),
         Input('selected-countries-store', 'data')],
        [State('projects-company-table-data-full', 'data'),
         State('projects-company-table-tooltip-full', 'data')],
        prevent_initial_call='initial_duplicate'
    )
    def filter_projects_company_table(company, likely_filter, selected_countries, data_full, tooltip_full):
        """Filter and format the Projects by Company table to mirror projects_by_time layout.
        Reloads table data when company changes to ensure synchronization with chart and map."""
        ctx = callback_context
        triggered_id = None
        if ctx.triggered:
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Reload table data when company changes (to ensure synchronization)
        if triggered_id == 'company-filter' or (company and (not data_full or len(data_full) == 0)):
            if company:
                # Load fresh data for the selected company
                df_table = load_projects_data(company)
                if not df_table.empty:
                    data_full = df_table.fillna("").to_dict('records')
                    tooltip_data = []
                    for row in data_full:
                        tip_row = {}
                        comments_val = str(row.get('Comments', '') or '').strip()
                        if comments_val and comments_val.lower() != 'nan':
                            tip_row['Comments'] = {'value': comments_val, 'type': 'text'}
                        tooltip_data.append(tip_row)
                    tooltip_full = tooltip_data
                else:
                    data_full = []
                    tooltip_full = []
            else:
                # No company selected - show empty table
                data_full = []
                tooltip_full = []
        else:
            # Use existing data if company hasn't changed
            data_full = data_full or []
            tooltip_full = tooltip_full or []
        
        if not data_full:
            return [], [], [], dash.no_update, dash.no_update
        
        df = pd.DataFrame(data_full)
        
        # Filter by selected countries (when any are chosen)
        if selected_countries:
            df = df[df['Country'].isin(selected_countries)]
        
        if df.empty:
            return [], [], [], dash.no_update, dash.no_update
        
        # Find likely-go-ahead column
        likely_col = None
        for col in df.columns:
            col_lower = str(col).lower()
            if 'likely' in col_lower and ('go' in col_lower or 'ahead' in col_lower):
                likely_col = col
                break
        
        # Normalize Likely To Go filter (match projects_by_time behavior)
        if not likely_filter:
            likely_filter = []
        if not isinstance(likely_filter, list):
            likely_filter = [likely_filter]
        
        selected_statuses = []
        if 'ALL' in [str(v).upper() for v in likely_filter]:
            selected_statuses = ['Y', 'N', 'UNCERTAIN', '']
        else:
            for v in likely_filter:
                v_up = str(v).upper()
                if v_up == 'Y':
                    selected_statuses.append('Y')
                elif v_up == 'N':
                    selected_statuses.append('N')
                elif v_up.startswith('U'):
                    selected_statuses.append('UNCERTAIN')
                elif v_up == 'EMPTY':
                    selected_statuses.append('')
                elif v == '':
                    selected_statuses.append('')
        
        if likely_col and selected_statuses:
            df[likely_col] = df[likely_col].astype(str).str.strip()
            col_upper = df[likely_col].str.upper()
            mask = pd.Series(False, index=df.index)
            for status in selected_statuses:
                if status == 'Y':
                    mask |= col_upper.str.startswith('Y')
                elif status == 'N':
                    mask |= col_upper.str.startswith('N')
                elif status == 'UNCERTAIN' or status == 'U':
                    mask |= col_upper.str.startswith('U')
                elif status == '':
                    mask |= (col_upper == '')
            df = df[mask].copy()
        elif likely_col and not selected_statuses:
            df = pd.DataFrame()
        
        if df.empty:
            return [], [], [], dash.no_update, dash.no_update
        
        # Preserve all available columns; order them similar to projects_by_time
        base_priority = [
            'Project Name',
            'Likely Go-ahead',
            'Field Type',
            'Country',
            'Region',
            'Group',
            'Hydrocarbon',
            'Depth',
            'Field/Block',
            'Play Type',
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
        ]
        
        all_cols = list(df.columns)
        quarter_cols = [
            c for c in all_cols
            if isinstance(c, str) and len(c) == 7 and c[4] == '_' and c[:4].isdigit()
        ]
        
        def quarter_key(name):
            try:
                year = int(name[:4])
                q = int(name[-1])
                return (year, q)
            except Exception:
                return (9999, 9)
        
        quarter_cols = sorted(quarter_cols, key=quarter_key)
        
        ordered_cols = (
            [c for c in base_priority if c in all_cols] +
            [c for c in all_cols if c not in base_priority and c not in quarter_cols] +
            quarter_cols
        )
        
        df = df[[c for c in ordered_cols if c in df.columns]].copy()
        df = df.reset_index(drop=True)
        
        # Format numeric reserve columns
        numeric_cols = ['Gas Reserves (mmboe)', 'Liquids Reserves (mmbbl)', 'Total Reserves (mmboe)']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].apply(lambda x: f'{x:,.3f}' if pd.notna(x) and x != 0 else '')
        
        # Normalize boolean / categorical displays
        bool_display_map = {
            'Y': 'Yes',
            'N': 'No',
            'U': 'Uncertain',
            'TRUE': 'Yes',
            'FALSE': 'No'
        }
        
        for col in ['Likely Go-ahead', 'Sanctioned']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].apply(lambda v: bool_display_map.get(str(v).upper(), v))
        
        # Preserve full comments for tooltips; truncate in display
        if 'Comments' in df.columns:
            original_comments = df['Comments'].copy()
            df['Comments'] = df['Comments'].astype(str).apply(lambda x: (x[:10] + '...') if len(x) > 10 else x)
        else:
            original_comments = pd.Series([''] * len(df))
        
        # Build columns with consistent display names and widths
        column_widths = {
            'Project Name': '180px',
            'Likely Go-ahead': '130px',
            'Country': '120px',
            'Region': '120px',
            'Group': '140px',
            'Field Type': '100px',
            'Hydrocarbon': '120px',
            'Depth': '80px',
            'Field/Block': '140px',
            'Play Type': '120px',
            'Operator': '120px',
            'Partner1': '100px',
            'Partner2': '100px',
            'Partner3': '100px',
            'Partner4': '100px',
            'Partner5': '100px',
            'First Oil Year': '100px',
            'Sanctioned': '80px',
            'Comments': '140px',
            'Project Status': '120px',
            'Gas Reserves (mmboe)': '140px',
            'Liquids Reserves (mmbbl)': '150px',
            'Total Reserves (mmboe)': '150px',
            'API': '80px',
            'Sulfur': '80px'
        }
        
        display_name_map = {
            'Likely Go-ahead': 'Likely To Go Ahead',
            'Field/Block': 'Field/Block',
            'Play Type': 'Play Type',
            'Group': 'Group'
        }
        
        available_cols = list(df.columns)
        quarter_cols = [
            c for c in available_cols
            if isinstance(c, str) and len(c) == 7 and c[4] == '_' and c[:4].isdigit()
        ]
        
        columns = []
        for col in available_cols:
            display_name = display_name_map.get(col, col)
            col_def = {'name': display_name, 'id': col}
            if col in column_widths:
                col_def['minWidth'] = column_widths[col]
                col_def['maxWidth'] = column_widths[col]
            elif col in quarter_cols:
                col_def['minWidth'] = '85px'
            columns.append(col_def)
        
        df = df.fillna('')
        data = df.to_dict('records')
        
        tooltip_data = []
        for idx, row in enumerate(data):
            tip_row = {}
            comment_val = original_comments.iloc[idx] if idx < len(original_comments) else ''
            if pd.notna(comment_val):
                comment_str = str(comment_val).strip()
                if comment_str and comment_str.lower() != 'nan':
                    tip_row['Comments'] = {'value': comment_str, 'type': 'text'}
            tooltip_data.append(tip_row)
        
        # Return table data and updated full data store
        return data, tooltip_data, columns, data_full, tooltip_full
    
    # Add A/Z hover sort UI on selected headers (matches projects_latest behavior)
    dash_app.clientside_callback(
        """
        function(columns) {
            setTimeout(function() {
                function addSortUI(header) {
                    if (header.querySelector('.sort-order-container')) {
                        return;
                    }
                    const sortContainer = document.createElement('div');
                    sortContainer.style.position = 'absolute';
                    sortContainer.style.right = '30px';
                    sortContainer.style.top = '50%';
                    sortContainer.style.transform = 'translateY(-50%)';
                    sortContainer.style.fontSize = '10px';
                    sortContainer.style.color = '#666';
                    sortContainer.style.cursor = 'pointer';
                    sortContainer.style.padding = '2px';
                    sortContainer.style.border = '1px solid transparent';
                    sortContainer.style.borderRadius = '2px';
                    sortContainer.style.lineHeight = '1';
                    sortContainer.style.textAlign = 'center';
                    sortContainer.style.display = 'flex';
                    sortContainer.style.flexDirection = 'column';
                    sortContainer.style.alignItems = 'center';
                    sortContainer.style.justifyContent = 'center';
                    sortContainer.style.height = '30px';
                    sortContainer.style.opacity = '0';
                    sortContainer.style.transition = 'opacity 0.2s ease';
                    sortContainer.style.zIndex = '2';
                    sortContainer.className = 'sort-order-container';
                    
                    const aElement = document.createElement('div');
                    aElement.textContent = 'A';
                    aElement.title = 'Click for ascending order';
                    aElement.style.display = 'block';
                    aElement.style.lineHeight = '1';
                    aElement.style.cursor = 'pointer';
                    aElement.style.padding = '1px 2px';
                    aElement.style.borderRadius = '1px';
                    aElement.style.fontFamily = 'Georgia, serif';
                    aElement.style.fontSize = '10px';
                    aElement.onmouseover = function() {
                        aElement.style.backgroundColor = '#d4e7ff';
                        aElement.style.fontWeight = 'bold';
                    };
                    aElement.onmouseout = function() {
                        aElement.style.backgroundColor = '';
                        aElement.style.fontWeight = '';
                    };
                    aElement.onclick = function(e) {
                        e.stopPropagation();
                        for (let i = 0; i < 3; i++) {
                            header.click();
                        }
                    };
                    
                    const zElement = document.createElement('div');
                    zElement.textContent = 'Z';
                    zElement.title = 'Click for descending order';
                    zElement.style.display = 'block';
                    zElement.style.lineHeight = '1';
                    zElement.style.cursor = 'pointer';
                    zElement.style.padding = '1px 2px';
                    zElement.style.borderRadius = '1px';
                    zElement.style.fontFamily = 'Georgia, serif';
                    zElement.style.fontSize = '10px';
                    zElement.onmouseover = function() {
                        zElement.style.backgroundColor = '#d4e7ff';
                        zElement.style.fontWeight = 'bold';
                    };
                    zElement.onmouseout = function() {
                        zElement.style.backgroundColor = '';
                        zElement.style.fontWeight = '';
                    };
                    zElement.onclick = function(e) {
                        e.stopPropagation();
                        for (let i = 0; i < 2; i++) {
                            header.click();
                        }
                    };
                    
                    sortContainer.appendChild(aElement);
                    sortContainer.appendChild(zElement);
                    header.appendChild(sortContainer);
                    
                    const sortIndicator = document.createElement('div');
                    sortIndicator.style.position = 'absolute';
                    sortIndicator.style.right = '8px';
                    sortIndicator.style.top = '50%';
                    sortIndicator.style.transform = 'translateY(-50%)';
                    sortIndicator.style.width = '15px';
                    sortIndicator.style.height = '15px';
                    sortIndicator.style.cursor = 'pointer';
                    sortIndicator.style.opacity = '0';
                    sortIndicator.style.transition = 'opacity 0.2s ease';
                    sortIndicator.style.zIndex = '1';
                    sortIndicator.title = 'Click to sort';
                    sortIndicator.className = 'sort-indicator';
                    
                    sortIndicator.innerHTML = `
                        <svg fill="#666" viewBox="0 0 301.219 301.219" xmlns="http://www.w3.org/2000/svg">
                            <g>
                                <path d="M159.365,23.736v-10c0-5.523-4.477-10-10-10H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h139.365
                                    C154.888,33.736,159.365,29.259,159.365,23.736z"/>
                                <path d="M130.586,66.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h120.586c5.523,0,10-4.477,10-10v-10
                                    C140.586,71.213,136.109,66.736,130.586,66.736z"/>
                                <path d="M111.805,129.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h101.805c5.523,0,10-4.477,10-10v-10
                                    C121.805,134.213,117.328,129.736,111.805,129.736z"/>
                                <path d="M93.025,199.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h83.025c5.522,0,10-4.477,10-10v-10
                                    C103.025,204.213,98.548,199.736,93.025,199.736z"/>
                                <path d="M74.244,262.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h64.244c5.522,0,10-4.477,10-10v-10
                                    C84.244,267.213,79.767,262.736,74.244,262.736z"/>
                                <path d="M298.29,216.877l-7.071-7.071c-1.875-1.875-4.419-2.929-7.071-2.929c-2.652,0-5.196,1.054-7.072,2.929l-34.393,34.393
                                    V18.736c0-5.523-4.477-10-10-10h-10c-5.523,0-10,4.477-10,10v225.462l-34.393-34.393c-1.876-1.875-4.419-2.929-7.071-2.929
                                    c-2.652,0-5.196,1.054-7.071,2.929l-7.072,7.071c-3.904,3.905-3.904,10.237,0,14.142l63.536,63.536
                                    c1.953,1.953,4.512,2.929,7.071,2.929c2.559,0,5.119-0.976,7.071-2.929l63.536-63.536
                                    C302.195,227.113,302.195,220.781,298.29,216.877z"/>
                            </g>
                        </svg>
                    `;
                    
                    sortIndicator.onmouseover = function() {
                        sortIndicator.style.opacity = '1';
                        sortIndicator.style.backgroundColor = '#e6f3ff';
                        sortIndicator.style.borderRadius = '2px';
                        sortIndicator.querySelector('svg').style.fill = '#1f3263';
                    };
                    
                    sortIndicator.onmouseout = function() {
                        sortIndicator.style.opacity = '0';
                        sortIndicator.style.backgroundColor = '';
                        sortIndicator.querySelector('svg').style.fill = '#666';
                    };
                    
                    sortIndicator.onclick = function(e) {
                        e.stopPropagation();
                        // Toggle sort by clicking the header twice
                        for (let i = 0; i < 2; i++) {
                            header.click();
                        }
                    };
                    
                    header.appendChild(sortIndicator);
                    
                    header.onmouseover = function() {
                        sortContainer.style.opacity = '1';
                        sortIndicator.style.opacity = '1';
                    };
                    
                    header.onmouseout = function() {
                        sortContainer.style.opacity = '0';
                        sortIndicator.style.opacity = '0';
                    };
                }
                
                const headers = document.querySelectorAll('#projects-company-table .dash-header');
                headers.forEach(header => {
                    addSortUI(header);
                });
            }, 500);
            return '';
        }
        """,
        Output('projects-company-dummy-sort', 'data'),
        Input('projects-company-table', 'columns'),
        prevent_initial_call=False
    )
    
    # Callback to sync year controls (display, dropdown, slider, prev/next buttons)
    @dash_app.callback(
        [Output('year-period-display', 'children'),
         Output('year-of-period-filter', 'value', allow_duplicate=True),
         Output('year-period-slider', 'value', allow_duplicate=True),
         Output('bar-highlight-year-store', 'data', allow_duplicate=True)],
        [Input('year-of-period-filter', 'value'),
         Input('year-period-slider', 'value'),
         Input('year-period-prev', 'n_clicks'),
         Input('year-period-next', 'n_clicks'),
         Input('year-period-timeline-prev', 'n_clicks'),
         Input('year-period-interval', 'n_intervals')],
        [State('year-period-slider', 'min'),
         State('year-period-slider', 'max'),
         State('year-period-play-store', 'data'),
         State('bar-highlight-year-store', 'data')],
        prevent_initial_call=True
    )
    def sync_year_controls(dropdown_value, slider_value, prev_clicks, next_clicks, 
                           timeline_prev_clicks, interval_tick, min_year, max_year, is_playing, bar_highlight_year):
        """Sync year display, dropdown, slider, navigation buttons; keep chart highlight unchanged."""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        current_year = dropdown_value or slider_value or min_year
        
        try:
            current_year = int(current_year)
        except (ValueError, TypeError):
            current_year = min_year
        
        # Handle different triggers
        if trigger_id == 'year-period-prev':
            new_year = max(current_year - 1, min_year)
        elif trigger_id == 'year-period-next':
            new_year = min(current_year + 1, max_year)
        elif trigger_id == 'year-period-timeline-prev':
            new_year = max(current_year - 1, min_year)
        elif trigger_id == 'year-period-interval':
            if is_playing:
                # Auto-advance to next year, loop back to min if at max
                if current_year >= max_year:
                    new_year = min_year
                else:
                    new_year = current_year + 1
            else:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        elif trigger_id == 'year-of-period-filter':
            new_year = dropdown_value
        elif trigger_id == 'year-period-slider':
            new_year = slider_value
        else:
            new_year = current_year
        
        # Do not change bar highlight when year controls change; keep prior highlight (if any)
        return str(new_year), new_year, new_year, dash.no_update

    # Clicking a bar (or invisible year markers) selects that year's controls and sets year highlight
    @dash_app.callback(
        [Output('year-of-period-filter', 'value', allow_duplicate=True),
         Output('year-period-slider', 'value', allow_duplicate=True),
         Output('bar-highlight-year-store', 'data', allow_duplicate=True),
         Output('selected-countries-store', 'data', allow_duplicate=True)],
        Input('projects-company-bar-chart', 'clickData'),
        State('selected-countries-store', 'data'),
        prevent_initial_call=True
    )
    def set_year_from_bar_click(click_data, selected_countries):
        """When a bar or year label is clicked, sync the year selection controls to that year and set highlight."""
        if not click_data or 'points' not in click_data or not click_data['points']:
            # Clear highlights when clicking outside/blank
            return dash.no_update, dash.no_update, None, dash.no_update
        
        try:
            point = click_data['points'][0]
            y_pos = point.get('y', 0)
            trace_name = point.get('data', {}).get('name', '') if hasattr(point, 'data') else ''
            
            # Skip quarter label clicks (y < 0 or quarter-click-capture trace) - those are handled separately
            if y_pos < 0 or trace_name == 'quarter-click-capture':
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            x_val = point.get('x')
            year_part = str(x_val).split(' ')[0]
            selected_year = int(year_part)
            
            # Update selected countries based on click (if it's a country bar)
            new_selected_countries = dash.no_update
            
            # If it's not a capture trace, it's a country bar
            if trace_name != 'year-click-capture' and trace_name != 'quarter-click-capture':
                clicked_country = trace_name
                selected_countries = selected_countries or []
                
                if clicked_country in selected_countries:
                    # Deselect
                    new_selected_countries = [c for c in selected_countries if c != clicked_country]
                else:
                    # Select
                    new_selected_countries = selected_countries + [clicked_country]
                    
        except (ValueError, TypeError, AttributeError, IndexError):
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        return selected_year, selected_year, selected_year, new_selected_countries
    
    # Callback to handle play/pause/stop buttons
    @dash_app.callback(
        [Output('year-period-play-store', 'data'),
         Output('year-period-interval', 'disabled'),
         Output('year-period-play', 'children')],
        [Input('year-period-play', 'n_clicks'),
         Input('year-period-stop', 'n_clicks')],
        [State('year-period-play-store', 'data')],
        prevent_initial_call=True
    )
    def toggle_year_animation(play_clicks, stop_clicks, is_playing):
        """Toggle auto-play animation of the year slider"""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'year-period-stop':
            return False, True, '▶'  # Stop playing
        elif trigger_id == 'year-period-play':
            # Toggle play state
            new_state = not bool(is_playing)
            return new_state, not new_state, '⏸' if new_state else '▶'
        
        return dash.no_update, dash.no_update, dash.no_update
    
    # Callback to populate company dropdown on initial load
    @dash_app.callback(
        [Output('company-filter', 'options'),
         Output('company-filter', 'value')],
        Input('current-submenu', 'data'),
        prevent_initial_call=False
    )
    def populate_company_dropdown(submenu):
        """Populate company dropdown with companies from database"""
        if submenu is not None and submenu != 'projects-company':
            return [], None
        
        companies = get_unique_companies()
        if not companies:
            return [], None
        
        options = [{'label': c, 'value': c} for c in companies]
        # Default to first company (or Exxon Mobil if available)
        default_value = 'Exxon Mobil' if 'Exxon Mobil' in companies else companies[0]
        
        return options, default_value
    
    # Callback to update years dropdown options when company or likely_goahead filter changes
    @dash_app.callback(
        [Output('year-of-period-filter', 'options'),
         Output('year-period-slider', 'min'),
         Output('year-period-slider', 'max'),
         Output('year-period-slider', 'marks')],
        [Input('company-filter', 'value'),
         Input('likely-to-go-filter', 'value')],
        prevent_initial_call=False
    )
    def update_years_options(company, likely_to_go):
        """Update years dropdown and slider options based on selected company and filters"""
        ltg_list = likely_to_go if isinstance(likely_to_go, list) else ([likely_to_go] if likely_to_go else [])
        years = get_unique_years(company, ltg_list)
        
        if not years:
            # Fallback to default years
            years = list(range(2025, 2030))
        
        options = [{'label': str(y), 'value': y} for y in years]
        min_year = min(years) if years else 2025
        max_year = max(years) if years else 2029
        marks = {y: {'label': '|', 'style': {'color': '#666666', 'fontSize': '14px'}} for y in years}
        
        return options, min_year, max_year, marks
    
    @dash_app.callback(
        [Output('projects-company-bar-chart', 'figure'),
         Output('projects-company-map', 'figure'),
         Output('year-of-period-container', 'style'),
         Output('production-additions-content', 'children')],
        [Input('current-submenu', 'data'),
         Input('company-filter', 'value'),
         Input('likely-to-go-filter', 'value'),
         Input('year-of-period-filter', 'value'),
         Input('year-period-slider', 'value'),
         Input('show-history-checkbox', 'value'),
         Input('selected-countries-store', 'data'),
         Input('bar-highlight-year-store', 'data'),
         Input('quarter-highlight-store', 'data')],
        prevent_initial_call=False
    )
    def update_projects_by_company(submenu, company, likely_to_go, selected_year, slider_year, show_history, selected_countries, bar_highlight_year, quarter_highlight):
        """Update projects by company chart and map"""
        # Handle checklist value (after normalization) - keep list for filtering
        ltg_list = likely_to_go if isinstance(likely_to_go, list) else ([likely_to_go] if likely_to_go else [])
        
        # Null content for Production Additions when no data
        null_content = html.Div('Null', style={
            'height': '14px',
            'width': '210px',
            'background': '#e8f5e9',
            'border': '1px solid #c5c5c5',
            'borderRadius': '2px',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center',
            'fontSize': '11px',
            'color': '#1b365d'
        })
        
        # Normal content for Production Additions when there's data
        normal_content = [
            html.Div(style={
                'height': '14px',
                'width': '210px',
                'background': 'linear-gradient(to right, #C7E8E4, #A4DCD5, #7DC9C3, #4FB2AF, #2A94A1, #1F7A8A, #1C6C7C)',
                'border': '1px solid #c5c5c5',
                'borderRadius': '2px'
            }),
            html.Div([
                html.Span('0.7', style={'fontSize': '10px', 'color': '#1b365d'}),
                html.Span('135.0', style={'fontSize': '10px', 'color': '#1b365d', 'marginLeft': 'auto'})
            ], style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'width': '210px',
                'marginTop': '2px'
            })
        ]
        
        # Check if this is the correct submenu (allow None on initial load)
        if submenu is not None and submenu != 'projects-company':
            empty_fig = go.Figure()
            empty_fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return empty_fig, empty_fig, {'display': 'none'}, null_content
        
        # If no company selected, show empty charts
        if not company:
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="Please select a company",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            empty_fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return empty_fig, empty_fig, {'display': 'none'}, null_content
        
        # Use the year from dropdown or slider (whichever is more recent)
        year_to_use = selected_year if selected_year else slider_year
        if not year_to_use:
            years = get_unique_years(company, ltg_list)
            year_to_use = years[0] if years else 2025
        
        # Load chart data with filters applied (company and likely_goahead)
        # Don't filter by countries here - we want to show ALL countries in the chart
        # Selected countries will be highlighted, non-selected will be greyed out
        df = load_chart_data(company, ltg_list)
        
        if df.empty:
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            empty_fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            # Hide Year of Period and show Null in Production Additions when no data
            return empty_fig, empty_fig, {'display': 'none'}, null_content
        
        # Pass selected countries to chart function for highlighting/greyout logic
        # The chart will show ALL countries, but highlight selected ones and grey out non-selected
        countries_to_show = selected_countries if selected_countries else None
        
        # Create bar chart - show all years by default (matches Tableau behavior)
        # The bar chart displays all available years/quarters
        bar_df = df.copy()
        bar_fig = create_stacked_bar_chart(
            bar_df,
            company or "Company",
            selected_countries, # Pass selected countries for highlighting
            highlight_year=bar_highlight_year,
            highlight_quarter=quarter_highlight
        )
        
        
        # Create map - always filtered by selected year (Year of Period filter controls the map)
        map_fig = create_world_map(year_to_use, company, ltg_list, selected_countries)

        
        # Show Year of Period section and normal Production Additions gradient when there's data
        return bar_fig, map_fig, {'display': 'block'}, normal_content

    # Download Callbacks
    
    # Download Chart Data
    @dash_app.callback(
        Output('projects-company-download-chart-csv', 'data'),
        Input('projects-company-btn-download-chart', 'n_clicks'),
        [State('company-filter', 'value'),
         State('likely-to-go-filter', 'value')],
        prevent_initial_call=True
    )
    def download_chart_data(n_clicks, company, likely_to_go):
        if not n_clicks:
            return dash.no_update
        ltg_list = likely_to_go if isinstance(likely_to_go, list) else ([likely_to_go] if likely_to_go else [])
        df = load_chart_data(company, ltg_list)
        if df.empty:
            return dash.no_update
        
        # Format to match live CSV: Remove 'Country Color' and Index
        if 'Country Color' in df.columns:
            df = df.drop(columns=['Country Color'])
            
        return dcc.send_data_frame(df.to_csv, "projects_capacity_chart_data.csv", index=False)

    # Download Map Data
    @dash_app.callback(
        Output('projects-company-download-map-csv', 'data'),
        Input('projects-company-btn-download-map', 'n_clicks'),
        [State('company-filter', 'value'),
         State('likely-to-go-filter', 'value'),
         State('year-of-period-filter', 'value'),
         State('year-period-slider', 'value')],
        prevent_initial_call=True
    )
    def download_map_data(n_clicks, company, likely_to_go, year_dropdown, year_slider):
        if not n_clicks:
            return dash.no_update
        ltg_list = likely_to_go if isinstance(likely_to_go, list) else ([likely_to_go] if likely_to_go else [])
        df = load_map_data(company, ltg_list)
        
        if df.empty:
             return dash.no_update
        
        # Filter by selected year
        year_to_use = year_dropdown if year_dropdown else year_slider
        if year_to_use:
             try:
                 df = df[df['Year of Period'] == int(year_to_use)]
             except:
                 pass
             
        return dcc.send_data_frame(df.to_csv, "projects_map_data.csv")
    
    # Download Table Data
    @dash_app.callback(
        Output('projects-company-download-table-csv', 'data'),
        Input('projects-company-btn-download-table', 'n_clicks'),
        State('projects-company-table', 'derived_virtual_data'),
        prevent_initial_call=True
    )
    def download_table_data(n_clicks, table_data):
        if not n_clicks or not table_data:
            return dash.no_update
        
        df = pd.DataFrame(table_data)
        
        # Identify quarter columns (format YYYY_QX)
        quarter_cols = [c for c in df.columns if isinstance(c, str) and len(c) == 7 and c[4] == '_' and c[:4].isdigit()]
        
        if not quarter_cols:
             return dcc.send_data_frame(df.to_csv, "projects_details.csv", index=False)
             
        # Unpivot (melt) the quarter columns to match the live CSV format
        # Keep all other columns as identifiers
        id_vars = [c for c in df.columns if c not in quarter_cols]
        
        # Melt the dataframe
        melted_df = df.melt(id_vars=id_vars, value_vars=quarter_cols, var_name='Measure Names', value_name='Measure Values')
        
        return dcc.send_data_frame(melted_df.to_csv, "projects_details.csv", index=False)
