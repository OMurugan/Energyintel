"""
Main Flask routes for Energy Intelligence website
"""
from flask import render_template, jsonify, request, redirect, url_for
from app.routes import main_bp
from app import db, cache
from app.models import Country, Production, Exports, Reserves, Imports
from sqlalchemy import func, extract
from datetime import datetime, timedelta


@main_bp.route('/')
@main_bp.route('/home')
def home():
    """Home page"""
    return render_template('home.html')


@main_bp.route('/news')
def news():
    """News page"""
    return render_template('news.html')


@main_bp.route('/data')
def data():
    """Data page - overview of available data"""
    return render_template('data.html')


# Removed /wcod route - Dash app handles this directly at /wcod/
# @main_bp.route('/wcod')
# @main_bp.route('/wcod/')
# def wcod():
#     """World Crude Oil Data (WCoD) - Country Overview"""
#     return render_template('wcod/country_overview.html')




@main_bp.route('/research')
def research():
    """Research page"""
    return render_template('research.html')


@main_bp.route('/services')
def services():
    """Services page"""
    return render_template('services.html')


@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@main_bp.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')


# API endpoints for dashboard data
@main_bp.route('/api/countries')
@cache.cached(timeout=3600)
def get_countries():
    """Get list of all countries"""
    countries = Country.query.order_by(Country.name).all()
    return jsonify([c.to_dict() for c in countries])


@main_bp.route('/api/production/summary')
@cache.cached(timeout=300)
def get_production_summary():
    """Get production summary statistics"""
    # Get latest date
    latest_date = db.session.query(func.max(Production.date)).scalar()
    if not latest_date:
        return jsonify({'error': 'No production data available'}), 404
    
    # Get total production for latest date
    total_production = db.session.query(
        func.sum(Production.production_bbl)
    ).filter(Production.date == latest_date).scalar() or 0
    
    # Get previous period for comparison
    prev_date = latest_date - timedelta(days=365)  # Year over year
    prev_production = db.session.query(
        func.sum(Production.production_bbl)
    ).filter(Production.date == prev_date).scalar() or 0
    
    change_pct = ((total_production - prev_production) / prev_production * 100) if prev_production > 0 else 0
    
    return jsonify({
        'latest_date': latest_date.isoformat(),
        'total_production_bbl': total_production,
        'previous_production_bbl': prev_production,
        'change_pct': round(change_pct, 2)
    })


@main_bp.route('/api/exports/summary')
@cache.cached(timeout=300)
def get_exports_summary():
    """Get exports summary statistics"""
    latest_date = db.session.query(func.max(Exports.date)).scalar()
    if not latest_date:
        return jsonify({'error': 'No export data available'}), 404
    
    total_exports = db.session.query(
        func.sum(Exports.exports_bbl)
    ).filter(Exports.date == latest_date).scalar() or 0
    
    prev_date = latest_date - timedelta(days=365)
    prev_exports = db.session.query(
        func.sum(Exports.exports_bbl)
    ).filter(Exports.date == prev_date).scalar() or 0
    
    change_pct = ((total_exports - prev_exports) / prev_exports * 100) if prev_exports > 0 else 0
    
    return jsonify({
        'latest_date': latest_date.isoformat(),
        'total_exports_bbl': total_exports,
        'previous_exports_bbl': prev_exports,
        'change_pct': round(change_pct, 2)
    })


@main_bp.route('/api/production/by-country')
@cache.cached(timeout=300)
def get_production_by_country():
    """Get production data grouped by country"""
    latest_date = db.session.query(func.max(Production.date)).scalar()
    if not latest_date:
        return jsonify([])
    
    results = db.session.query(
        Country.name,
        Country.code,
        func.sum(Production.production_bbl).label('total_production')
    ).join(Production).filter(
        Production.date == latest_date
    ).group_by(Country.id, Country.name, Country.code).order_by(
        func.sum(Production.production_bbl).desc()
    ).limit(20).all()
    
    return jsonify([
        {
            'country': r.name,
            'code': r.code,
            'production_bbl': r.total_production
        }
        for r in results
    ])


@main_bp.route('/api/production/trend')
@cache.cached(timeout=300)
def get_production_trend():
    """Get production trend over time"""
    start_date = datetime.now().date() - timedelta(days=365*5)  # 5 years
    
    results = db.session.query(
        extract('year', Production.date).label('year'),
        extract('month', Production.date).label('month'),
        func.sum(Production.production_bbl).label('total_production')
    ).filter(
        Production.date >= start_date
    ).group_by(
        extract('year', Production.date),
        extract('month', Production.date)
    ).order_by(
        extract('year', Production.date),
        extract('month', Production.date)
    ).all()
    
    return jsonify([
        {
            'date': f"{int(r.year)}-{int(r.month):02d}",
            'production_bbl': r.total_production
        }
        for r in results
    ])


def register_wcod_routes(app):
    """Register WCoD dashboard routes - all routes serve Dash app for Python header"""
    
    # All WCoD routes are handled by the Dash app at /wcod/
    # These Flask routes serve the Dash app directly to ensure Python header always loads
    # Routes starting with /wcod/ are handled directly by Dash app, no Flask route needed
    
    def serve_wcod_dash(path=None):
        """Serve the WCoD Dash app - it will handle routing internally"""
        if hasattr(app, 'dash_apps') and 'wcod' in app.dash_apps:
            dash_app = app.dash_apps['wcod']
            # Serve the Dash app's index - it will handle the pathname via client-side routing
            return dash_app.index()
        # Fallback: redirect to /wcod/ if Dash app not available
        return redirect('/wcod/')
    
    # New routes without /wcod/ prefix
    # Country tab routes
    @app.route('/country-overview')
    def country_overview():
        return serve_wcod_dash()
    
    # Crude tab routes
    @app.route('/crude-overview')
    def crude_overview():
        return serve_wcod_dash()
    
    @app.route('/crude-profile')
    def crude_profile():
        return serve_wcod_dash()
    
    @app.route('/crude-comparison')
    def crude_comparison():
        return serve_wcod_dash()
    
    @app.route('/crude-quality-comparison')
    def crude_quality():
        return serve_wcod_dash()
    
    @app.route('/crude-carbon-intensity')
    def crude_carbon():
        return serve_wcod_dash()
    
    # Trade tab routes
    @app.route('/trade/imports-country-detail')
    def trade_imports_detail():
        return serve_wcod_dash()
    
    @app.route('/trade/imports-country-comparison')
    def trade_imports_comparison():
        return serve_wcod_dash()
    
    @app.route('/trade/global-exports')
    def trade_global_exports():
        return serve_wcod_dash()
    
    @app.route('/trade/russian-exports-by-terminal-and-exporting-company')
    def trade_russian_exports():
        return serve_wcod_dash()
    
    # Prices tab routes
    @app.route('/prices/global-crude-prices')
    def prices_global_prices():
        return serve_wcod_dash()
    
    @app.route('/prices/price-scorecard-for-key-world-oil-grades')
    def prices_scorecard():
        return serve_wcod_dash()
    
    @app.route('/prices/gross-product-worth-and-margins')
    def prices_gpw_margins():
        return serve_wcod_dash()
    
    # Upstream Projects routes
    @app.route('/upstream-projects/projects-by-country')
    def projects_by_country():
        return serve_wcod_dash()
    
    @app.route('/upstream-projects/projects-by-company')
    def projects_by_company():
        return serve_wcod_dash()
    
    @app.route('/upstream-projects/projects-by-time')
    def projects_by_time():
        return serve_wcod_dash()
    
    @app.route('/upstream-projects/projects-by-status')
    def projects_by_status():
        return serve_wcod_dash()
    
    @app.route('/upstream-projects-related-articles')
    def projects_latest():
        return serve_wcod_dash()
    
    # Methodology tab routes
    @app.route('/upstream-oil-projects-tracker-methodology')
    def projects_tracker():
        return serve_wcod_dash()
    
    @app.route('/carbon-intensity-methodology')
    def projects_carbon():
        return serve_wcod_dash()
    
    # Keep old routes for backward compatibility
    # Country tab routes
    @app.route('/wcod-country-overview')
    def wcod_country_profile():
        return serve_wcod_dash()
    
    # Crude tab routes
    @app.route('/wcod-crude-profile')
    def wcod_crude_profile():
        return serve_wcod_dash()
    
    @app.route('/wcod-crude-comparison')
    def wcod_crude_comparison():
        return serve_wcod_dash()
    
    @app.route('/wcod-crude-quality-comparison')
    def wcod_crude_quality():
        return serve_wcod_dash()
    
    @app.route('/wcod-crude-carbon-intensity')
    def wcod_crude_carbon():
        return serve_wcod_dash()
    
    # Upstream Projects routes (not starting with /wcod/)
    @app.route('/wcod-upstream-projects/projects-by-status')
    def wcod_projects_by_status():
        return serve_wcod_dash()
    
    @app.route('/wcod-upstream-projects-related-articles')
    def wcod_projects_latest():
        return serve_wcod_dash()
    
    # Methodology tab routes
    @app.route('/wcod-upstream-oil-projects-tracker-methodology')
    def wcod_projects_tracker():
        return serve_wcod_dash()
    
    @app.route('/wcod-carbon-intensity-methodology')
    def wcod_projects_carbon():
        return serve_wcod_dash()

