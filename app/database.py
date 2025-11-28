"""
Database connection utilities for PostgreSQL

All database configuration (host, port, db name, user, password, pool
options, etc.) is centralized in `config.py`. This module simply reads
those values from the Flask app config (or directly from `Config` when
no app context is available) so there is a single source of truth.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from flask import current_app

from config import Config


def _get_sqlalchemy_uri_from_config() -> str:
    """
    Helper to read the SQLAlchemy database URI from Flask config or
    fall back to the base `Config` class.
    """
    try:
        # When running inside an application context
        uri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
        if uri:
            return uri
    except RuntimeError:
        # No active application context; fall back to Config
        pass

    return Config.SQLALCHEMY_DATABASE_URI


def get_db_connection_string() -> str:
    """
    Public helper used by the rest of the app to obtain a DB connection string.

    This now delegates entirely to the centralized configuration in `config.py`
    (via Flask's `SQLALCHEMY_DATABASE_URI`), so database credentials and
    host/port information are defined in one place only.
    """
    return _get_sqlalchemy_uri_from_config()


def get_db_engine():
    """
    Create a SQLAlchemy engine for direct database access
    """
    connection_string = get_db_connection_string()

    # Prefer engine options from Flask config; fall back to `Config`
    engine_options = {}
    try:
        engine_options = current_app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}) or {}
    except RuntimeError:
        # No app context; use options defined on the base Config
        engine_options = getattr(Config, "SQLALCHEMY_ENGINE_OPTIONS", {}) or {}

    engine = create_engine(connection_string, **engine_options)
    return engine


def get_db_session():
    """
    Get a database session for raw SQL queries
    """
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def execute_query(query, params=None):
    """
    Execute a raw SQL query and return results
    
    Args:
        query: SQL query string
        params: Optional dictionary of parameters for parameterized queries
    
    Returns:
        List of result rows
    
    Raises:
        Exception: With detailed error message if database connection or query fails
    """
    # Extract connection details for error message (without password)
    connection_string = get_db_connection_string()
    db_host = db_port = db_name = db_user = "unknown"
    try:
        from urllib.parse import urlparse
        parsed = urlparse(connection_string)
        db_host = parsed.hostname or "unknown"
        db_port = str(parsed.port) if parsed.port else "unknown"
        db_name = parsed.path.lstrip('/') or "unknown"
        db_user = parsed.username or "unknown"
    except Exception:
        pass
    
    try:
        engine = get_db_engine()
        with engine.connect() as connection:
            if params:
                result = connection.execute(text(query), params)
            else:
                result = connection.execute(text(query))
            
            # If it's a SELECT query, return rows
            if query.strip().upper().startswith('SELECT'):
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


def test_connection():
    """
    Test the database connection
    """
    try:
        engine = get_db_engine()
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)

