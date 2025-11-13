# Setup Guide - Energy Intelligence

## Prerequisites

- Python 3.10 or higher
- PostgreSQL 12 or higher
- pip (Python package manager)

## Step-by-Step Setup

### 1. Create Virtual Environment

```bash
cd /var/www/projects/energyintel/energy
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up PostgreSQL Database

```bash
# Create database
sudo -u postgres createdb energyintel

# Or using SQL
sudo -u postgres psql
CREATE DATABASE energyintel;
CREATE USER energyuser WITH PASSWORD 'energypass';
GRANT ALL PRIVILEGES ON DATABASE energyintel TO energyuser;
\q
```

### 4. Configure Environment

Create a `.env` file in the project root:

```bash
DATABASE_URL=postgresql://energyuser:energypass@localhost/energyintel
SECRET_KEY=your-secret-key-change-this-in-production
FLASK_ENV=development
FLASK_DEBUG=True
HOST=0.0.0.0
PORT=5000
```

### 5. Initialize Database

```bash
python init_db.py
```

This will:
- Create all database tables
- Seed sample countries (USA, Saudi Arabia, Russia, etc.)
- Generate 5 years of production, exports, and reserves data

### 6. Run the Application

**Development:**
```bash
python app.py
# or
./run.sh
```

**Production (with Gunicorn):**
```bash
gunicorn -c gunicorn_config.py app:app
```

### 7. Access the Application

- Main website: http://localhost:5000
- WCoD Dashboard: http://localhost:5000/dash/wcod/
- Production Dashboard: http://localhost:5000/dash/production/
- Exports Dashboard: http://localhost:5000/dash/exports/
- Country Profile: http://localhost:5000/dash/country-profile/

## Troubleshooting

### Database Connection Issues

If you get database connection errors:

1. Verify PostgreSQL is running:
   ```bash
   sudo systemctl status postgresql
   ```

2. Check database credentials in `.env` file

3. Test connection:
   ```bash
   psql -U energyuser -d energyintel -h localhost
   ```

### Import Errors

Make sure you're in the project root directory and virtual environment is activated:

```bash
pwd  # Should show: /var/www/projects/energyintel/energy
which python  # Should point to venv/bin/python
```

### Dashboard Not Loading

1. Check that all dashboards are registered in `app/dashboards/__init__.py`
2. Verify Flask app is running without errors
3. Check browser console for JavaScript errors

## Data Management

### Reset Database

To drop and recreate all tables:

```bash
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.drop_all(); db.create_all()"
python init_db.py
```

### Add More Data

Edit `init_db.py` to add more countries or extend the date range for sample data.

## Production Deployment

1. Set `FLASK_ENV=production` in `.env`
2. Configure Redis for caching (optional but recommended)
3. Use Gunicorn with multiple workers:
   ```bash
   gunicorn --bind 0.0.0.0:8000 --workers 4 app:app
   ```
4. Set up Nginx as reverse proxy
5. Use a process manager like systemd or supervisor

## Next Steps

- Customize dashboards in `app/dashboards/`
- Add more data models in `app/models/`
- Extend API endpoints in `app/routes/views.py`
- Customize templates in `app/templates/`

