"""
Database connection utilities for PostgreSQL

DEPRECATED: This module is kept for backward compatibility.
All database operations should now use core.data_helpers instead.

This module now delegates to core.data_helpers to ensure a single source of truth.
"""
# Import all database functions from the centralized location
from core.data_helpers import (
    get_db_connection_string,
    get_db_engine,
    get_db_session,
    execute_query,
    test_connection
)

# Re-export for backward compatibility
__all__ = [
    'get_db_connection_string',
    'get_db_engine',
    'get_db_session',
    'execute_query',
    'test_connection'
]

