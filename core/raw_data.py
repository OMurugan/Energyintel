"""
Load and cache raw data from database
This module loads data once at startup for performance
"""
from core.data_helpers import get_db_engine
from sqlalchemy import text
import pandas as pd

# Global data storage - will be populated on first access
RAW_COUNTRY = pd.DataFrame()
RAW_CRUDE_ANNUAL = pd.DataFrame()
YEAR_OPTS = []
DEFAULT_YEAR = None
COUNTRY_OPTIONS = []


def load_all_data():
    """
    Load all data from database
    This should be called once at app startup
    """
    global RAW_COUNTRY, RAW_CRUDE_ANNUAL, YEAR_OPTS, DEFAULT_YEAR, COUNTRY_OPTIONS
    
    if not RAW_COUNTRY.empty:
        # Data already loaded
        return
    
    try:
        ENGINE = get_db_engine()
        
        # First, let's check what tables actually exist
        print("Checking available tables in database...")
        tables_query = text("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_type = 'BASE TABLE' 
            AND table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        """)
        
        tables_df = pd.read_sql(tables_query, ENGINE)
        print(f"Available tables in database:\n{tables_df.to_string()}")
        
        # Let's check if the tables exist without schema prefix
        QUERY_COUNTRY = text(
            """
            SELECT
                country_id,
                country_long_name,
                EXTRACT(YEAR FROM yr)::int AS year,
                output,     -- production ('000 b/d)
                exports,    -- exports ('000 b/d)
                reserves,   -- reserves (Billion bbl)
                COALESCE(to_be_deleted, FALSE) AS to_be_deleted
            FROM fact_wcod_country
            WHERE COALESCE(to_be_deleted, FALSE) = FALSE
            """
        )
        
        QUERY_ANNUAL_CRUDE = text(
            """
            SELECT
                country_name,
                grp.OPEC_GRP,
                crude_name,
                EXTRACT(YEAR FROM yr)::int AS year,
                production_kbpd,
                exports_kbpd,
                api,
                sulfur_pct,
                "tan_mg_koh/g",
                ports_terminals,
                classification,
                crude_alias,
                producers,
                sellers,
                ci_rank
            FROM fact_wcod_crude a
            LEFT JOIN dim_country grp ON grp.DIM_COUNTRY_ID = a.COUNTRY_ID
            WHERE COALESCE(to_be_deleted, FALSE) = FALSE
            """
        )
        
        try:
            # Try to get country-level data without schema prefix
            print("Attempting to load country data...")
            raw_country = pd.read_sql(QUERY_COUNTRY, ENGINE)
            print(f"Successfully loaded {len(raw_country)} country records")
            
            raw_country = raw_country.rename(
                columns={
                    "output": "production",  # keep naming consistent in the UI
                }
            )

            # Guard against duplicates (country,year) by keeping the latest insert if
            #  present (remove this if your data is guaranteed unique)
            raw_country = raw_country.sort_values(
                ["country_id", "year"]
            ).drop_duplicates(subset=["country_id", "year"], keep="last")
            
            # Try to get annual crude data
            print("Attempting to load crude data...")
            raw_crude_annual = pd.read_sql(QUERY_ANNUAL_CRUDE, ENGINE)
            print(f"Successfully loaded {len(raw_crude_annual)} crude records")
            
            # Calculate options
            from core.data_helpers import year_options, country_options
            YEAR_OPTS, DEFAULT_YEAR = year_options(raw_country)
            COUNTRY_OPTIONS = country_options(raw_country)
            
            # Store globally
            RAW_COUNTRY = raw_country
            RAW_CRUDE_ANNUAL = raw_crude_annual
            
            print(f"Data loading completed successfully:")
            print(f"- Country records: {len(RAW_COUNTRY)}")
            print(f"- Crude annual records: {len(RAW_CRUDE_ANNUAL)}")
            print(f"- Available years: {YEAR_OPTS}")
            print(f"- Default year: {DEFAULT_YEAR}")
            print(f"- Number of countries: {len(COUNTRY_OPTIONS)}")
            
        except Exception as table_error:
            print(f"Error loading from public schema: {table_error}")
            
            # Try to find the actual table names by searching all schemas
            print("\nSearching for tables with similar names in all schemas...")
            search_query = text("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE (table_name ILIKE '%wcod%' OR table_name ILIKE '%fact%' OR table_name ILIKE '%country%')
                AND table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
            """)
            
            similar_tables = pd.read_sql(search_query, ENGINE)
            if not similar_tables.empty:
                print(f"Found similar tables:\n{similar_tables.to_string()}")
                
                # Try the first matching table
                schema = similar_tables.iloc[0]['table_schema']
                table = similar_tables.iloc[0]['table_name']
                print(f"\nTrying table: {schema}.{table}")
                
                try:
                    test_query = text(f"SELECT * FROM {schema}.{table} LIMIT 5")
                    test_data = pd.read_sql(test_query, ENGINE)
                    print(f"Sample data from {schema}.{table}:\n{test_data.head()}")
                except Exception as test_error:
                    print(f"Could not read from {schema}.{table}: {test_error}")
            else:
                print("No similar tables found.")
            
            # Create empty DataFrames for development
            print("\nCreating empty data structures for development...")
            create_empty_data()
            
    except Exception as e:
        print(f"Error connecting to database: {e}")
        # Create empty data structures for development
        print("Creating empty data structures for development...")
        create_empty_data()


def create_empty_data():
    """Create empty data structures for development when database is not available"""
    global RAW_COUNTRY, RAW_CRUDE_ANNUAL, YEAR_OPTS, DEFAULT_YEAR, COUNTRY_OPTIONS
    
    # Create empty DataFrames with expected columns
    RAW_COUNTRY = pd.DataFrame(columns=[
        'country_id', 'country_long_name', 'year', 'production', 
        'exports', 'reserves', 'to_be_deleted'
    ])
    
    # Add some sample data for development
    sample_countries = [
        {'country_id': 'US', 'country_long_name': 'United States', 'year': 2023, 'production': 13200, 'exports': 3500, 'reserves': 44.4},
        {'country_id': 'SA', 'country_long_name': 'Saudi Arabia', 'year': 2023, 'production': 10000, 'exports': 7000, 'reserves': 267.0},
        {'country_id': 'RU', 'country_long_name': 'Russia', 'year': 2023, 'production': 10700, 'exports': 5000, 'reserves': 80.0},
        {'country_id': 'CA', 'country_long_name': 'Canada', 'year': 2023, 'production': 4800, 'exports': 3500, 'reserves': 168.0},
        {'country_id': 'IQ', 'country_long_name': 'Iraq', 'year': 2023, 'production': 4500, 'exports': 3400, 'reserves': 145.0},
    ]
    
    for country in sample_countries:
        RAW_COUNTRY = pd.concat([RAW_COUNTRY, pd.DataFrame([country])], ignore_index=True)
    
    # Create crude data
    RAW_CRUDE_ANNUAL = pd.DataFrame(columns=[
        'country_name', 'OPEC_GRP', 'crude_name', 'year',
        'production_kbpd', 'exports_kbpd', 'api', 'sulfur_pct',
        'tan_mg_koh/g', 'ports_terminals', 'classification',
        'crude_alias', 'producers', 'sellers', 'ci_rank'
    ])
    
    # Add sample crude data
    sample_crudes = [
        {'country_name': 'United States', 'OPEC_GRP': 'Non-OPEC', 'crude_name': 'WTI', 'year': 2023, 'production_kbpd': 6500, 'exports_kbpd': 1500, 'api': 40.5, 'sulfur_pct': 0.34},
        {'country_name': 'Saudi Arabia', 'OPEC_GRP': 'OPEC', 'crude_name': 'Arab Light', 'year': 2023, 'production_kbpd': 7000, 'exports_kbpd': 6000, 'api': 33.0, 'sulfur_pct': 1.77},
        {'country_name': 'Russia', 'OPEC_GRP': 'Non-OPEC', 'crude_name': 'Urals', 'year': 2023, 'production_kbpd': 5000, 'exports_kbpd': 4500, 'api': 31.5, 'sulfur_pct': 1.48},
        {'country_name': 'Nigeria', 'OPEC_GRP': 'OPEC', 'crude_name': 'Bonny Light', 'year': 2023, 'production_kbpd': 1800, 'exports_kbpd': 1600, 'api': 35.0, 'sulfur_pct': 0.14},
    ]
    
    for crude in sample_crudes:
        RAW_CRUDE_ANNUAL = pd.concat([RAW_CRUDE_ANNUAL, pd.DataFrame([crude])], ignore_index=True)
    
    # Set default values
    YEAR_OPTS = [2023, 2022, 2021]
    DEFAULT_YEAR = 2023
    
    # Create country options from sample data
    COUNTRY_OPTIONS = []
    for _, row in RAW_COUNTRY.drop_duplicates('country_id').iterrows():
        COUNTRY_OPTIONS.append({
            'label': row['country_long_name'],
            'value': row['country_id']
        })
    
    print(f"Created sample data for development:")
    print(f"- Country records: {len(RAW_COUNTRY)}")
    print(f"- Crude annual records: {len(RAW_CRUDE_ANNUAL)}")
    print(f"- Available years: {YEAR_OPTS}")
    print(f"- Default year: {DEFAULT_YEAR}")
    print(f"- Number of countries: {len(COUNTRY_OPTIONS)}")


# Helper function to get data (with lazy loading if needed)
def get_country_data():
    """Get country data, loading if necessary"""
    if RAW_COUNTRY.empty:
        load_all_data()
    return RAW_COUNTRY.copy()


def get_crude_annual_data():
    """Get crude annual data, loading if necessary"""
    if RAW_CRUDE_ANNUAL.empty:
        load_all_data()
    return RAW_CRUDE_ANNUAL.copy()


def get_year_options():
    """Get year options, loading if necessary"""
    if not YEAR_OPTS:
        load_all_data()
    return YEAR_OPTS.copy(), DEFAULT_YEAR


def get_country_options():
    """Get country options, loading if necessary"""
    if not COUNTRY_OPTIONS:
        load_all_data()
    return COUNTRY_OPTIONS.copy()