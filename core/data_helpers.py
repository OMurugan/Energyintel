"""
Database connection utilities for Dash Enterprise
SINGLE SOURCE OF TRUTH for all database connections and queries
"""
import os
from urllib.parse import quote_plus, urlparse

import numpy as np
import pandas as pd
from dash_enterprise_libraries import data_sources as ds
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ===============================================================
#              1) LOAD DATABASE CREDENTIALS
# ===============================================================
def _get_db_credentials():
    """Get database credentials from Dash Enterprise, DATABASE_URL or .env"""
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

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        try:
            parsed = urlparse(database_url)
            db_name = parsed.path.lstrip("/")
            return (
                db_name,
                parsed.username,
                parsed.password,
                parsed.hostname,
                parsed.port or "5432",
            )
        except Exception:
            pass

    load_dotenv()
    return (
        os.getenv("DB_NAME"),
        os.getenv("DB_USER"),
        os.getenv("DB_PASSWORD"),
        os.getenv("DB_HOST"),
        os.getenv("DB_PORT", "5432"),
    )


POSTGRES_DB_API, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT = _get_db_credentials()


# ===============================================================
#           2) CREATE GLOBAL SQLALCHEMY ENGINE (ONE TIME)
# ===============================================================
def create_db_engine(user, password, host, port, database):
    """Create a single reusable SQLAlchemy engine with pooling."""
    return create_engine(
        f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{database}",
        pool_pre_ping=True,
        pool_recycle=360,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )


# ⭐ GLOBAL ENGINE — DO NOT RECREATE PER QUERY
ENGINE = create_db_engine(
    POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB_API
)


def get_db_engine():
    """Return global shared engine."""
    return ENGINE


# ===============================================================
#                   3) EXECUTE QUERY SAFELY
# ===============================================================
def execute_query(query, params=None):
    """
    Execute SQL and return rows as list[dict].
    Prevents connection leaks and pool overflow.
    """
    try:
        with ENGINE.connect() as conn:
            result = conn.execute(text(query), params or {})

            if query.strip().upper().startswith(("SELECT", "WITH")):
                return [dict(row._mapping) for row in result.fetchall()]

            return result.rowcount

    except Exception as e:
        raise Exception(
            f"Database connection error:\n"
            f"  Error: {str(e)}\n\n"
            f"Possible causes:\n"
            f"  - DB credentials incorrect\n"
            f"  - Too many active connections\n"
            f"  - Network / security group blocking access\n"
            f"  - DB server overloaded"
        ) from e


# ===============================================================
#           4) SESSIONS (For advanced raw SQL usage)
# ===============================================================
SessionLocal = sessionmaker(bind=ENGINE)

def get_db_session():
    return SessionLocal()


# ===============================================================
#                   5) TEST CONNECTION
# ===============================================================
def test_connection():
    try:
        with ENGINE.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Connection successful"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


# ===============================================================
#                   6) UTILITY HELPERS
# ===============================================================
def rp_ratio(prod_000bd, reserves_bbl_b):
    if prod_000bd is None or np.isnan(prod_000bd) or prod_000bd == 0:
        return np.nan
    return reserves_bbl_b / (prod_000bd * 0.365)


def year_options(df):
    years = sorted(df["year"].dropna().astype(int).unique())
    return [{"label": str(y), "value": y} for y in years], (years[-1] if years else None)


def country_options(df, country_col="country_long_name"):
    return [{"label": c, "value": c} for c in sorted(df[country_col].dropna().unique())]
