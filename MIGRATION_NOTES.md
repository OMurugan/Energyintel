# Flask to Dash Enterprise Migration Notes

## Completed Migration Steps

### 1. Core Infrastructure ✅
- Created `core/data_helpers.py` - Database connection using Dash Enterprise `data_sources` pattern
- Created `core/raw_data.py` - Data loading and caching module
- Created `assets/theme.py` - Dash Design Kit theme configuration
- Created `Procfile` - Dash Enterprise deployment configuration

### 2. Main Application ✅
- Updated `app.py` - Now standalone Dash Enterprise app with embedding support
- Updated `requirements.txt` - Dash Enterprise compatible dependencies
- Modified `app/dashboards/wcod_dashboard.py` - Works standalone without Flask server

### 3. Database Migration ✅
- Updated `app/dashboards/wcod/country_overview.py` - Uses `core.data_helpers.execute_query`
- Updated `app/dashboards/wcod/country_profile.py` - Uses `core.data_helpers.execute_query`
- Updated `app/dashboards/wcod/crude_comparison.py` - Uses `core.data_helpers.execute_query`

## Remaining Work

### Modules Still Using Flask-SQLAlchemy
The following modules still reference `from app import db` and may need conversion to raw SQL queries:

1. `app/dashboards/wcod/projects_by_country.py`
2. `app/dashboards/wcod/projects_by_company.py`
3. `app/dashboards/wcod/projects_by_time.py`
4. `app/dashboards/wcod/projects_carbon.py`
5. `app/dashboards/wcod/projects_latest.py`
6. `app/dashboards/wcod/projects_tracker.py`
7. `app/dashboards/wcod/imports_comparison.py`

**Action Required**: These modules should be updated to use `core.data_helpers.execute_query()` instead of Flask-SQLAlchemy ORMs.

### Embedding Support
- Dash Enterprise embedding is configured via `Embeddable(origins="*")` plugin
- Reference implementation available at `/var/www/projects/energyintel/SOURCES/dash_test_wcod-local.html`

### Database Connection Pattern
The new pattern uses:
```python
from core.data_helpers import execute_query, get_db_engine

# For raw SQL queries
results = execute_query("SELECT * FROM table")

# For pandas DataFrames
engine = get_db_engine()
df = pd.read_sql(query, engine)
```

### Deployment
- Use `Procfile` for Dash Enterprise deployment
- Ensure environment variables are set in Dash Enterprise data sources:
  - `POSTGRES_DB_API` (or `DB_NAME`)
  - `POSTGRES_USER` (or `DB_USER`)
  - `POSTGRES_PASSWORD` (or `DB_PASSWORD`)
  - `POSTGRES_HOST` (or `DB_HOST`)
  - `POSTGRES_PORT` (or `DB_PORT`)

## Testing Checklist
- [ ] Verify app starts without Flask dependencies
- [ ] Test database connections work with Dash Enterprise data sources
- [ ] Test embedding functionality
- [ ] Verify all dashboard modules load correctly
- [ ] Test modules that still use Flask-SQLAlchemy (may need conversion)

## Notes
- Flask is still a dependency (Dash uses it internally), but Flask-SQLAlchemy and Flask-Caching are no longer needed
- The app now works standalone without requiring a Flask application factory
- All routes are handled by Dash routing, not Flask routes
- Static assets should be served from `app/assets/` directory (Dash handles this automatically)

