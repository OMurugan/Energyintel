"""
Database connection utilities for PostgreSQL
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from flask import current_app
from urllib.parse import quote_plus
import os


def get_db_connection_string():
    """
    Get PostgreSQL connection string from environment variables or Flask config
    """
    # Try to get from environment first
    if os.environ.get('DATABASE_URL'):
        return os.environ.get('DATABASE_URL')
    
    # Build from individual components
    host = os.environ.get('DB_HOST', 'ei-primary.cluster-ro-ciegxadcyunf.us-east-1.rds.amazonaws.com')
    port = os.environ.get('DB_PORT', '5432')
    database = os.environ.get('DB_NAME', 'api')
    user = os.environ.get('DB_USER', 'ranjinim')
    password = os.environ.get('DB_PASSWORD', 'K(^Hklc5221d5Y')
    # URL-encode password to handle special characters
    encoded_password = quote_plus(password)
    
    return f'postgresql://{user}:{encoded_password}@{host}:{port}/{database}'


def get_db_engine():
    """
    Create a SQLAlchemy engine for direct database access
    """
    connection_string = get_db_connection_string()
    
    engine = create_engine(
        connection_string,
        pool_size=10,
        pool_recycle=3600,
        pool_pre_ping=True,
        connect_args={
            'connect_timeout': 10,
            'options': '-csearch_path=dev'
        }
    )
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
    """
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

