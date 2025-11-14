"""
Dash dashboard registration
"""


def register_dashboards(app):
    """Register all Dash dashboards with Flask app"""
    from app.dashboards.wcod_dashboard import create_wcod_dashboard
    from app.dashboards.country_profile_dashboard import create_country_profile_dashboard
    from app.dashboards.production_dashboard import create_production_dashboard
    from app.dashboards.exports_dashboard import create_exports_dashboard
    from app.dashboards.wcod.crude_quality import create_crude_quality_dashboard
    print('app',app)
    # Create Dash apps - each gets its own server instance
    # Dash apps will be accessible at their url_base_pathname
    wcod_dash = create_wcod_dashboard(app, '/wcod/')
    country_dash = create_country_profile_dashboard(app, '/dash/country-profile/')
    production_dash = create_production_dashboard(app, '/dash/production/')
    exports_dash = create_exports_dashboard(app, '/dash/exports/')
    crude_dash = create_crude_quality_dashboard(app, '/dash/crude-quality/')
    # Store dash apps on Flask app for reference
    print('country_dash',country_dash)
    print('crude_dash',crude_dash)
    app.dash_apps = {
        'wcod': wcod_dash,
        'country-profile': country_dash,
        'production': production_dash,
        'exports': exports_dash,
        'crude-quality': crude_dash
    }

