"""
Application factory for Flask app and Dash integration.
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from app.config import config

db = SQLAlchemy()

def create_app(config_name=None):
    """Create and configure a Flask application.
    """
    if config_name is None:
        config_name = os.getenv("FLASK_CONFIG", "default")

    app = Flask(__name__)

    app.config.from_object(config[config_name])

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions, register blueprints, etc.
    db.init_app(app)
    
    return app

def create_dash_app(server, url_base_pathname):
    """Create a Dash application linked to a Flask server.
    """
    import dash
    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname=url_base_pathname,
        assets_folder=server.root_path + '/assets'
    )
    return app


