# Energy Intelligence - Tableau to Dash Migration

This project migrates Tableau-based dashboards from Energy Intelligence website to fully interactive Plotly Dash applications integrated within a Flask framework.

## 🏗️ Project Structure

```
energy/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models/              # SQLAlchemy models
│   │   ├── country.py
│   │   ├── production.py
│   │   ├── exports.py
│   │   ├── imports.py
│   │   └── reserves.py
│   ├── routes/              # Flask routes
│   │   ├── __init__.py
│   │   └── views.py
│   ├── dashboards/          # Dash applications
│   │   ├── __init__.py
│   │   ├── wcod_dashboard.py
│   │   ├── country_profile_dashboard.py
│   │   ├── production_dashboard.py
│   │   └── exports_dashboard.py
│   └── templates/           # HTML templates
│       ├── base.html
│       ├── home.html
│       ├── wcod.html
│       └── ...
├── config.py                # Configuration settings
├── app.py                   # Application entry point
├── init_db.py              # Database initialization
├── requirements.txt        # Python dependencies
└── gunicorn_config.py      # Production server config
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Database

Create a PostgreSQL database:

```bash
createdb energyintel
```

Or using SQL:
```sql
CREATE DATABASE energyintel;
CREATE USER energyuser WITH PASSWORD 'energypass';
GRANT ALL PRIVILEGES ON DATABASE energyintel TO energyuser;
```

### 3. Configure Environment

Copy `.env.example` to `.env` and update with your database credentials:

```bash
DATABASE_URL=postgresql://energyuser:energypass@localhost/energyintel
SECRET_KEY=your-secret-key-here
DASH_ENV=development
```

### 4. Initialize Database

```bash
python init_db.py
```

This will create all tables and seed sample data.

### 5. Run Development Server

```bash
python app.py
```

Or using Flask CLI:
```bash
export FLASK_APP=app.py
flask run
```

The application will be available at `http://localhost:5000`

## 📊 Dashboards

### Available Dashboards

1. **WCoD Main Dashboard** (`/dash/wcod/`)
   - Comprehensive overview with KPIs
   - Production by country bar charts
   - Production trend line charts
   - Exports analysis
   - Interactive filters (region, country, time range)

2. **Production Dashboard** (`/dash/production/`)
   - Production heatmap
   - Regional breakdown
   - Country-level analysis

3. **Exports Dashboard** (`/dash/exports/`)
   - Top exporting countries
   - Global exports trends
   - Regional comparisons

4. **Country Profile Dashboard** (`/dash/country-profile/`)
   - Country-specific KPIs
   - Production trends
   - Exports/imports analysis
   - Trade balance visualization

## 🗄️ Database Models

### Country
- Basic country information (code, name, region, continent)

### Production
- Monthly production data by country
- Units: barrels (bbl) and metric tons (mt)

### Exports
- Monthly export data by country
- Optional destination country tracking

### Imports
- Monthly import data by country
- Optional source country tracking

### Reserves
- Annual reserves data by country
- Proven reserves tracking

## 🔧 Configuration

### Development

Set `DASH_ENV=development` in your `.env` file or environment variables.

### Production

1. Set `DASH_ENV=production`
2. Configure Redis for caching (optional but recommended)
3. Use Gunicorn to run the application:

```bash
gunicorn -c gunicorn_config.py app:app
```

Or with environment variables:
```bash
gunicorn --bind 0.0.0.0:8000 --workers 4 app:app
```

## 📝 API Endpoints

The Flask application provides REST API endpoints for data access:

- `GET /api/countries` - List all countries
- `GET /api/production/summary` - Production summary statistics
- `GET /api/exports/summary` - Exports summary statistics
- `GET /api/production/by-country` - Production data by country
- `GET /api/production/trend` - Production trend over time

## 🎨 Styling

The application uses:
- **Bootstrap 5** for responsive layout
- **Inter font** for typography
- **Plotly** for interactive visualizations
- Custom CSS matching Tableau aesthetics

## 🔄 Migration Process

This project follows a four-step migration approach:

1. **Reverse-engineer Tableau logic** - Analyze Tableau workbooks and calculations
2. **Prepare data in PostgreSQL** - Normalize and structure data
3. **Rebuild with Plotly Dash** - Create equivalent visualizations
4. **Integrate with Flask** - Deploy as part of web application

## 👥 Team Roles

- **Murugan**: Flask app structure, PostgreSQL integration, deployment setup
- **Navin**: Dashboard KPI logic, API layer, data access optimization
- **Ranjini**: Dash layout, callbacks, frontend alignment to Tableau

## 📦 Dependencies

See `requirements.txt` for complete list. Key dependencies:

- Flask 3.0.0
- Dash 2.14.2
- Plotly 5.18.0
- SQLAlchemy 2.0.23
- PostgreSQL (psycopg2-binary)
- Flask-Caching 2.1.0

## 🐛 Troubleshooting

### Database Connection Issues

Ensure PostgreSQL is running and credentials in `.env` are correct.

### Import Errors

Make sure you're running from the project root directory and all dependencies are installed.

### Dashboard Not Loading

Check that Dash apps are properly registered in `app/dashboards/__init__.py` and the DispatcherMiddleware is configured correctly.

## 📄 License

Proprietary - Energy Intelligence

