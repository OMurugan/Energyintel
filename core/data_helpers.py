"""
Database connection utilities for Dash Enterprise
SINGLE SOURCE OF TRUTH for all database connections and queries
Uses Dash Enterprise data sources pattern
"""
import os
from urllib.parse import quote_plus, urlparse

import numpy as np
import pandas as pd
from dash_enterprise_libraries import data_sources as ds
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ======================= Database Credentials =======================
# Single source of truth for database credentials
# Priority: 1. Dash Enterprise data sources, 2. DATABASE_URL env var, 3. Individual env vars, 4. Hardcoded defaults

def _get_db_credentials():
    """
    Get database credentials from Dash Enterprise or fallback to .env file.
    Returns tuple: (db_name, user, password, host, port)
    This is the SINGLE SOURCE OF TRUTH for database credentials.
    """
    # Priority 1: Try Dash Enterprise data sources first
    try:
        creds = ds.credentials("PostgreSQL")
        db_name = getattr(creds, "dbname", None) or getattr(creds, "database", None)
        user = getattr(creds, "username", None)
        password = getattr(creds, "password", None)
        host = getattr(creds, "host", None)
        port = getattr(creds, "port", None)
        if all([db_name, user, password, host, port]):
            return db_name, user, password, host, port
    except Exception:
        pass
    
    # Priority 2: Try DATABASE_URL environment variable
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        try:
            parsed = urlparse(database_url)
            db_name = parsed.path.lstrip('/') if parsed.path else None
            user = parsed.username
            password = parsed.password
            host = parsed.hostname
            port = parsed.port or '5432'
            if all([db_name, user, password, host, port]):
                return db_name, user, password, host, port
        except Exception:
            pass
    
    # Priority 3: Fallback to .env file or individual environment variables
    load_dotenv()
    db_name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")    
    
    return db_name, user, password, host, port


# Get credentials once at module load
POSTGRES_DB_API, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT = _get_db_credentials()


def create_db_engine(
    user: str, password: str, host: str, port: str, database: str, echo=False
):
    """
    Function to create a database engine
    Args:
        user (str) : postgres username
        password (str) : postgres password
        host(str) : postgres host url
        port (str) : postgres port number
        database (str) : postgres database name
        echo=False if True, the Engine will log all statements as well as
        a repr() of their parameter lists to the default log handler

    Returns:
        Engine (sqlalchemy.engine.Engine)
    """
    # Handle port as string or int
    port_str = str(port) if port else "5432"
    
    engine = create_engine(
        (
            f"postgresql+psycopg2://{user}:"  # noqa
            f"{quote_plus(password)}@{host}:{port_str}/"  # noqa
            f"{database}"
        ),
        echo=echo,
    )
    return engine


def get_db_engine():
    """
    Get database engine using Dash Enterprise credentials or .env fallback
    """
    return create_db_engine(
        POSTGRES_USER,
        POSTGRES_PASSWORD,
        POSTGRES_HOST,
        POSTGRES_PORT,
        POSTGRES_DB_API,
    )


def execute_query(query, params=None):
    """
    Execute a raw SQL query and return results
    Compatible with Dash Enterprise pattern
    
    Args:
        query: SQL query string
        params: Optional dictionary of parameters for parameterized queries
    
    Returns:
        List of result rows (as dictionaries) for SELECT queries
        Row count for other queries
    
    Raises:
        Exception: With detailed error message if database connection or query fails
    """
    # Extract connection details for error message (without password)
    db_host = POSTGRES_HOST or "unknown"
    db_port = POSTGRES_PORT or "unknown"
    db_name = POSTGRES_DB_API or "unknown"
    db_user = POSTGRES_USER or "unknown"
    
    try:
        engine = get_db_engine()
        with engine.connect() as connection:
            if params:
                result = connection.execute(text(query), params)
            else:
                result = connection.execute(text(query))
            
            # If it's a SELECT query, return rows
            if query.strip().upper().startswith(('SELECT', 'WITH')):
                columns = result.keys()
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            else:
                connection.commit()
                return result.rowcount
                
    except Exception as e:
        error_msg = (
            f"Database connection error:\n"
            f"  Host: {db_host}\n"
            f"  Port: {db_port}\n"
            f"  Database: {db_name}\n"
            f"  User: {db_user}\n"
            f"  Error: {str(e)}\n\n"
            f"Please check:\n"
            f"  1. Database server is running and accessible\n"
            f"  2. Network connectivity to {db_host}:{db_port}\n"
            f"  3. Database credentials in .env file or Dash Enterprise data sources\n"
            f"  4. Firewall/security group settings allow connections from this host"
        )
        raise Exception(error_msg) from e


def get_db_connection_string():
    """
    Get database connection string (for compatibility with existing code)
    This is the SINGLE SOURCE OF TRUTH for database connection strings.
    """
    password = quote_plus(POSTGRES_PASSWORD) if POSTGRES_PASSWORD else ''
    port_str = str(POSTGRES_PORT) if POSTGRES_PORT else '5432'
    return f'postgresql://{POSTGRES_USER}:{password}@{POSTGRES_HOST}:{port_str}/{POSTGRES_DB_API}'


def get_db_session():
    """
    Get a database session for raw SQL queries
    Uses the centralized database connection
    """
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def test_connection():
    """
    Test the database connection
    Returns: (success: bool, message: str)
    """
    try:
        engine = get_db_engine()
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        return True, "Connection successful"
    except Exception as e:
        db_host = POSTGRES_HOST or "unknown"
        db_port = POSTGRES_PORT or "unknown"
        return False, f"Connection failed to {db_host}:{db_port} - {str(e)}"


# =============== Helpers for metrics & shaping ===============
def rp_ratio(prod_000bd, reserves_bbl_b):
    """
    R/P (years) = Reserves (billion bbl) / Production (billion bbl per year).
    prod_000bd ('000 b/d) → billion bbl/year via factor 0.365.
    """
    if prod_000bd is None or np.isnan(prod_000bd) or prod_000bd == 0:
        return np.nan
    return reserves_bbl_b / (prod_000bd * 0.365)


def year_options(df):
    years = sorted([int(y) for y in df["year"].dropna().unique()])
    return [{"label": str(y), "value": int(y)} for y in years], (
        years[-1] if years else None
    )


def country_options(df, country_col="country_long_name"):
    countries = sorted(df[country_col].dropna().unique())
    return [{"label": c, "value": c} for c in countries]

