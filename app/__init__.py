"""
Flask application factory
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
import dash

from config import config

# Initialize extensions
db = SQLAlchemy()
cache = Cache()


def create_app(config_name='default'):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    cache.init_app(app)
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Import and register dashboards
    from app.dashboards import register_dashboards
    register_dashboards(app)
    
    # Register WCoD dashboard routes after dashboards are registered
    from app.routes.views import register_wcod_routes
    register_wcod_routes(app)
    
    return app


def create_dash_app(server, url_base_pathname):
    """Factory for creating Dash apps"""
    dash_app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname=url_base_pathname,
        external_stylesheets=[
            'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
            'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
        ],
        suppress_callback_exceptions=True
    )
    return dash_app

