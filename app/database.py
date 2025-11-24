"""
Database utility functions for executing queries
"""
from flask import current_app, has_app_context
from sqlalchemy import text, create_engine
import pandas as pd
from app import db


def _get_engine():
    """Get database engine, handling both app context and standalone usage"""
    if has_app_context():
        return db.engine
    else:
        # Fallback: create engine from config if no app context
        from config import config
        config_obj = config.get('default', config.get('development'))
        return create_engine(config_obj.SQLALCHEMY_DATABASE_URI)


def execute_query(query, params=None):
    """
    Execute a SQL query and return results as a list of dictionaries.
    
    Args:
        query (str): SQL query string
        params (dict, optional): Query parameters
        
    Returns:
        list: List of dictionaries representing query results
    """
    try:
        engine = _get_engine()
        with engine.connect() as connection:
            # Execute the query
            result = connection.execute(text(query), params or {})
            
            # Convert result to list of dictionaries
            columns = result.keys()
            rows = result.fetchall()
            
            # Convert to list of dictionaries
            results = [dict(zip(columns, row)) for row in rows]
            
            return results
    except Exception as e:
        if has_app_context():
            current_app.logger.error(f"Error executing query: {e}")
        else:
            print(f"Error executing query: {e}")
        raise


def execute_query_to_dataframe(query, params=None):
    """
    Execute a SQL query and return results as a pandas DataFrame.
    
    Args:
        query (str): SQL query string
        params (dict, optional): Query parameters
        
    Returns:
        pd.DataFrame: DataFrame containing query results
    """
    try:
        engine = _get_engine()
        with engine.connect() as connection:
            df = pd.read_sql(text(query), connection, params=params)
            return df
    except Exception as e:
        if has_app_context():
            current_app.logger.error(f"Error executing query to DataFrame: {e}")
        else:
            print(f"Error executing query to DataFrame: {e}")
        raise

