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
    from app.dashboards.wcod.crude_carbon import create_crude_carbon_dashboard
    from app.dashboards.wcod.crude_comparison import create_crude_comparison_dashboard
    from app.dashboards.wcod.crude_overview import create_crude_overview_dashboard
    from app.dashboards.wcod.country_profile import create_country_profile_dashboard as create_wcod_country_profile_dashboard
    from app.dashboards.wcod.crude_profile import create_crude_profile_dashboard
    print('app',app)
    # Create Dash apps - each gets its own server instance
    # Dash apps will be accessible at their url_base_pathname
    wcod_dash = create_wcod_dashboard(app, '/wcod/')
    country_dash = create_country_profile_dashboard(app, '/dash/country-profile/')
    production_dash = create_production_dashboard(app, '/dash/production/')
    exports_dash = create_exports_dashboard(app, '/dash/exports/')
    crude_quality_dash = create_crude_quality_dashboard(app, '/dash/crude-quality/')
    crude_carbon_dash = create_crude_carbon_dashboard(app, '/dash/crude-carbon/')
    crude_comparison_dash = create_crude_comparison_dashboard(app, '/dash/crude-comparison/')
    crude_overview_dash = create_crude_overview_dashboard(app, '/dash/crude-overview/')
    wcod_country_profile_dash = create_wcod_country_profile_dashboard(app, '/dash/wcod-country-profile/')
    crude_profile_dash = create_crude_profile_dashboard(app, '/dash/crude-profile/')
    # Store dash apps on Flask app for reference
    print('country_dash',country_dash)
    print('crude_quality_dash',crude_quality_dash)
    print('crude_carbon_dash',crude_carbon_dash)
    print('crude_comparison_dash',crude_comparison_dash)
    print('crude_overview_dash',crude_overview_dash)
    print('wcod_country_profile_dash',wcod_country_profile_dash)
    print('crude_profile_dash',crude_profile_dash)
    app.dash_apps = {
        'wcod': wcod_dash,
        'country-profile': country_dash,
        'production': production_dash,
        'exports': exports_dash,
        'crude-quality': crude_quality_dash,
        'crude-carbon': crude_carbon_dash,
        'crude-comparison': crude_comparison_dash,
        'crude-overview': crude_overview_dash,
        'wcod-country-profile': wcod_country_profile_dash,
        'crude-profile': crude_profile_dash
    }

