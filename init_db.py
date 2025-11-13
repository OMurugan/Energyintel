"""
Database initialization script
Creates tables and seeds sample data
"""
from app import create_app, db
from app.models import Country, Production, Exports, Reserves, Imports
from datetime import date, timedelta
import random

def seed_countries():
    """Seed countries data"""
    countries_data = [
        {'code': 'USA', 'name': 'United States', 'region': 'North America', 'continent': 'North America'},
        {'code': 'SAU', 'name': 'Saudi Arabia', 'region': 'Middle East', 'continent': 'Asia'},
        {'code': 'RUS', 'name': 'Russia', 'region': 'Europe', 'continent': 'Europe'},
        {'code': 'IRN', 'name': 'Iran', 'region': 'Middle East', 'continent': 'Asia'},
        {'code': 'IRQ', 'name': 'Iraq', 'region': 'Middle East', 'continent': 'Asia'},
        {'code': 'CAN', 'name': 'Canada', 'region': 'North America', 'continent': 'North America'},
        {'code': 'ARE', 'name': 'United Arab Emirates', 'region': 'Middle East', 'continent': 'Asia'},
        {'code': 'CHN', 'name': 'China', 'region': 'Asia', 'continent': 'Asia'},
        {'code': 'KWT', 'name': 'Kuwait', 'region': 'Middle East', 'continent': 'Asia'},
        {'code': 'BRA', 'name': 'Brazil', 'region': 'South America', 'continent': 'South America'},
        {'code': 'NGA', 'name': 'Nigeria', 'region': 'Africa', 'continent': 'Africa'},
        {'code': 'VEN', 'name': 'Venezuela', 'region': 'South America', 'continent': 'South America'},
        {'code': 'MEX', 'name': 'Mexico', 'region': 'North America', 'continent': 'North America'},
        {'code': 'NOR', 'name': 'Norway', 'region': 'Europe', 'continent': 'Europe'},
        {'code': 'KAZ', 'name': 'Kazakhstan', 'region': 'Asia', 'continent': 'Asia'},
    ]
    
    for country_data in countries_data:
        country = Country.query.filter_by(code=country_data['code']).first()
        if not country:
            country = Country(**country_data)
            db.session.add(country)
    
    db.session.commit()
    print("✓ Countries seeded")


def seed_production_data():
    """Seed production data for the last 5 years"""
    countries = Country.query.all()
    if not countries:
        print("No countries found. Please seed countries first.")
        return
    
    # Generate monthly data for the last 5 years
    end_date = date.today()
    start_date = end_date - timedelta(days=365*5)
    
    current_date = start_date
    while current_date <= end_date:
        # Use first day of month
        if current_date.day == 1:
            for country in countries:
                # Check if data already exists
                existing = Production.query.filter_by(
                    country_id=country.id,
                    date=current_date
                ).first()
                
                if not existing:
                    # Generate realistic production values (in barrels)
                    base_production = {
                        'USA': 18000000,
                        'SAU': 11000000,
                        'RUS': 11000000,
                        'IRN': 4000000,
                        'IRQ': 4500000,
                        'CAN': 5000000,
                        'ARE': 3000000,
                        'CHN': 4000000,
                        'KWT': 2800000,
                        'BRA': 3000000,
                        'NGA': 2000000,
                        'VEN': 1500000,
                        'MEX': 2000000,
                        'NOR': 2000000,
                        'KAZ': 1800000,
                    }
                    
                    base = base_production.get(country.code, 1000000)
                    # Add some variation
                    production_bbl = base * (1 + random.uniform(-0.1, 0.1))
                    production_mt = production_bbl * 0.136  # Approximate conversion
                    
                    production = Production(
                        country_id=country.id,
                        date=current_date,
                        production_bbl=production_bbl,
                        production_mt=production_mt
                    )
                    db.session.add(production)
        
        current_date += timedelta(days=1)
    
    db.session.commit()
    print("✓ Production data seeded")


def seed_exports_data():
    """Seed exports data"""
    countries = Country.query.all()
    if not countries:
        return
    
    end_date = date.today()
    start_date = end_date - timedelta(days=365*5)
    
    current_date = start_date
    while current_date <= end_date:
        if current_date.day == 1:
            for country in countries:
                existing = Exports.query.filter_by(
                    country_id=country.id,
                    date=current_date
                ).first()
                
                if not existing:
                    # Exports are typically 60-80% of production for major exporters
                    production = Production.query.filter_by(
                        country_id=country.id,
                        date=current_date
                    ).first()
                    
                    if production:
                        export_ratio = random.uniform(0.5, 0.9)
                        exports_bbl = production.production_bbl * export_ratio
                        exports_mt = exports_bbl * 0.136
                        
                        export = Exports(
                            country_id=country.id,
                            date=current_date,
                            exports_bbl=exports_bbl,
                            exports_mt=exports_mt
                        )
                        db.session.add(export)
        
        current_date += timedelta(days=1)
    
    db.session.commit()
    print("✓ Exports data seeded")


def seed_reserves_data():
    """Seed reserves data (updated annually)"""
    countries = Country.query.all()
    if not countries:
        return
    
    # Reserves data is typically updated annually
    for year in range(2020, 2025):
        reserve_date = date(year, 1, 1)
        
        for country in countries:
            existing = Reserves.query.filter_by(
                country_id=country.id,
                date=reserve_date
            ).first()
            
            if not existing:
                # Base reserves in barrels (billions)
                base_reserves = {
                    'VEN': 300000000000,
                    'SAU': 260000000000,
                    'CAN': 170000000000,
                    'IRN': 160000000000,
                    'IRQ': 140000000000,
                    'KWT': 100000000000,
                    'ARE': 100000000000,
                    'RUS': 80000000000,
                    'USA': 50000000000,
                    'NGA': 37000000000,
                    'KAZ': 30000000000,
                    'CHN': 26000000000,
                    'BRA': 13000000000,
                    'MEX': 7000000000,
                    'NOR': 8000000000,
                }
                
                base = base_reserves.get(country.code, 10000000000)
                reserves_bbl = base * (1 + random.uniform(-0.05, 0.05))
                reserves_mt = reserves_bbl * 0.136
                proven_reserves_bbl = reserves_bbl * 0.9
                
                reserve = Reserves(
                    country_id=country.id,
                    date=reserve_date,
                    reserves_bbl=reserves_bbl,
                    reserves_mt=reserves_mt,
                    proven_reserves_bbl=proven_reserves_bbl
                )
                db.session.add(reserve)
    
    db.session.commit()
    print("✓ Reserves data seeded")


def init_database():
    """Initialize database with tables and sample data"""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        print("✓ Tables created")
        
        # Seed data
        print("\nSeeding data...")
        seed_countries()
        seed_production_data()
        seed_exports_data()
        seed_reserves_data()
        
        print("\n✓ Database initialization complete!")


if __name__ == '__main__':
    init_database()

