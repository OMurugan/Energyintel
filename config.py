"""
Configuration settings for Energy Intelligence application
Now uses centralized database connection from core.data_helpers
"""
import os
from pathlib import Path
from dotenv import load_dotenv

basedir = Path(__file__).parent.absolute()

# Import centralized database connection utilities
from core.data_helpers import get_db_connection_string


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration - PostgreSQL
    # Uses centralized database connection from core.data_helpers
    # This ensures a single source of truth for database credentials
    SQLALCHEMY_DATABASE_URI = get_db_connection_string()
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # PostgreSQL connection pool settings
    # Schema will be overridden in DevelopmentConfig and ProductionConfig
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 10,
            'options': '-csearch_path=dev'  # Default to dev schema
        }
    }
    
    # Flask-Caching configuration
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Dash configuration
    DASH_ROUTES_PATHNAME_PREFIX = '/dash/'
    
    # Application settings
    DEBUG = os.environ.get('DASH_DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))


class DevelopmentConfig(Config):
    """Development configuration - uses schema from DB_SCHEMA env var (defaults to 'dev')"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    
    # Override engine options to use schema from .env file (DB_SCHEMA)
    # Defaults to 'dev' if not set in .env
    load_dotenv()
    dev_schema = os.getenv('DB_SCHEMA', 'dev')
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 10,
            'options': f'-csearch_path={dev_schema}'
        }
    }


class ProductionConfig(Config):
    """Production configuration - uses schema from DB_SCHEMA env var (defaults to 'public')"""
    DEBUG = False
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Override engine options for production - uses schema from .env file (DB_SCHEMA)
    # Defaults to 'public' if not set in .env
    load_dotenv()
    production_schema = os.getenv('DB_SCHEMA', 'public')
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 10,
            'options': f'-csearch_path={production_schema}'
        }
    }


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
