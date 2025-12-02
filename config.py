"""
Configuration settings for Energy Intelligence Flask application
"""
import os
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv

basedir = Path(__file__).parent.absolute()


def get_db_credentials():
    """
    Get database credentials from Dash Enterprise or fallback to .env file.
    Returns tuple: (db_name, user, password, host, port)
    """
    try:
        # Try Dash Enterprise data sources first (if locally logged in or on enterprise server)
        from dash_enterprise_libraries import data_sources as ds
        creds = ds.credentials("PostgreSQL")
        db_name = getattr(creds, "dbname") or getattr(creds, "database", None)
        user = getattr(creds, "username")
        password = getattr(creds, "password")
        host = getattr(creds, "host")
        port = getattr(creds, "port")
        return db_name, user, password, host, port
    except Exception:
        # Fallback to .env file
        load_dotenv()
        db_name = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        return db_name, user, password, host, port


def build_database_uri(db_name, user, password, host, port):
    """Build PostgreSQL connection URI from components"""
    encoded_password = quote_plus(password) if password else ''
    return f'postgresql://{user}:{encoded_password}@{host}:{port}/{db_name}'


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration - PostgreSQL
    # Priority: 1. DATABASE_URL env var, 2. Dash Enterprise/.env, 3. Legacy env vars, 4. Hardcoded defaults
    if os.environ.get('DATABASE_URL'):
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    else:
        # Try Dash Enterprise or .env file first
        try:
            db_name, db_user, db_password, db_host, db_port = get_db_credentials()
            if all([db_name, db_user, db_password, db_host, db_port]):
                SQLALCHEMY_DATABASE_URI = build_database_uri(db_name, db_user, db_password, db_host, db_port)
            else:
                raise ValueError("Missing database credentials")
        except Exception:
            # Fallback to legacy environment variables or hardcoded defaults
            DB_HOST = os.environ.get('DB_HOST', 'ei-primary.cluster-ro-ciegxadcyunf.us-east-1.rds.amazonaws.com')
            DB_PORT = os.environ.get('DB_PORT', '5432')
            DB_NAME = os.environ.get('DB_NAME', 'api')
            DB_USER = os.environ.get('DB_USER', 'ranjinim')
            DB_PASSWORD = os.environ.get('DB_PASSWORD', 'K(^Hklc5221d5Y')
            SQLALCHEMY_DATABASE_URI = build_database_uri(DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
    
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
