"""
Main application entry point
"""
import os
from app import create_app

# Get configuration from environment
config_name = os.environ.get('FLASK_ENV', 'default')

app = create_app(config_name)

if __name__ == '__main__':
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )

