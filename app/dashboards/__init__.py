"""
Dash dashboard registration
"""


def register_dashboards(app):
    """Register all Dash dashboards with Flask app"""
    from app.dashboards.wcod_dashboard import create_wcod_dashboard
    from app.dashboards.country_profile_dashboard import create_country_profile_dashboard
    from app.dashboards.production_dashboard import create_production_dashboard
    from app.dashboards.exports_dashboard import create_exports_dashboard
    
    # Create Dash apps - each gets its own server instance
    # Dash apps will be accessible at their url_base_pathname
    wcod_dash = create_wcod_dashboard(app, '/wcod/')
    country_dash = create_country_profile_dashboard(app, '/dash/country-profile/')
    production_dash = create_production_dashboard(app, '/dash/production/')
    exports_dash = create_exports_dashboard(app, '/dash/exports/')
    
    # Store dash apps on Flask app for reference
    app.dash_apps = {
        'wcod': wcod_dash,
        'country-profile': country_dash,
        'production': production_dash,
        'exports': exports_dash
    }

