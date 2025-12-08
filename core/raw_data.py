"""
Load and cache raw data from database
This module loads data once at startup for performance
"""
import time

from core.data_helpers import get_db_engine, execute_query
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
        t0 = time.monotonic()
        ENGINE = get_db_engine()
        t_engine = time.monotonic()
        
        # Query country-level data
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
        
        # Query annual crude data
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
        
        # Get country-level data
        raw_country = pd.read_sql(QUERY_COUNTRY, ENGINE)
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
        
        # Get annual crude data
        raw_crude_annual = pd.read_sql(QUERY_ANNUAL_CRUDE, ENGINE)
        
        # Calculate options
        from core.data_helpers import year_options, country_options
        YEAR_OPTS, DEFAULT_YEAR = year_options(raw_country)
        COUNTRY_OPTIONS = country_options(raw_country)
        
        # Store globally
        RAW_COUNTRY = raw_country
        RAW_CRUDE_ANNUAL = raw_crude_annual

        t_done = time.monotonic()
        print(
            f"[raw_data] engine: {t_engine - t0:.2f}s | "
            f"country query: {len(raw_country)} rows | "
            f"crude query: {len(raw_crude_annual)} rows | "
            f"total: {t_done - t0:.2f}s"
        )
        
    except Exception as e:
        print(f"Error loading data: {e}")
        # Keep empty DataFrames on error
        pass

