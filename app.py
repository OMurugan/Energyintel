"""
Main application entry point
"""
import os
from dotenv import load_dotenv
from app import create_app

# Load environment variables from .env file
load_dotenv()

# Get configuration from environment
config_name = os.environ.get('FLASK_ENV', 'default')

app = create_app(config_name)

if __name__ == '__main__':
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )

