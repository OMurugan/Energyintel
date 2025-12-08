"""
Database initialization script
Creates tables and seeds sample data
"""
from core.data_helpers import execute_query
from datetime import date, timedelta
import random

def create_tables():
    print("Creating database tables...")
    execute_query("""
    CREATE SCHEMA IF NOT EXISTS dev;
    
    CREATE TABLE IF NOT EXISTS dev.dim_country (
        dim_country_id VARCHAR(50) PRIMARY KEY,
        country_code VARCHAR(10) UNIQUE NOT NULL,
        country_long_name VARCHAR(255) UNIQUE NOT NULL,
        region VARCHAR(100),
        continent VARCHAR(100),
        opec_grp VARCHAR(50)
    );
    
    CREATE TABLE IF NOT EXISTS dev.fact_crude_production (
        fact_crude_production_id SERIAL PRIMARY KEY,
        country_id VARCHAR(50) REFERENCES dev.dim_country(dim_country_id),
        date DATE NOT NULL,
        production_bbl NUMERIC,
        production_mt NUMERIC
    );
    
    CREATE TABLE IF NOT EXISTS dev.fact_crude_exports (
        fact_crude_exports_id SERIAL PRIMARY KEY,
        country_id VARCHAR(50) REFERENCES dev.dim_country(dim_country_id),
        date DATE NOT NULL,
        exports_bbl NUMERIC,
        exports_mt NUMERIC
    );
    
    CREATE TABLE IF NOT EXISTS dev.fact_crude_imports (
        fact_crude_imports_id SERIAL PRIMARY KEY,
        country_id VARCHAR(50) REFERENCES dev.dim_country(dim_country_id),
        date DATE NOT NULL,
        imports_bbl NUMERIC,
        imports_mt NUMERIC
    );
    
    CREATE TABLE IF NOT EXISTS dev.fact_crude_reserves (
        fact_crude_reserves_id SERIAL PRIMARY KEY,
        country_id VARCHAR(50) REFERENCES dev.dim_country(dim_country_id),
        date DATE NOT NULL,
        reserves_bbl NUMERIC,
        reserves_mt NUMERIC,
        proven_reserves_bbl NUMERIC
    );

    CREATE TABLE IF NOT EXISTS dev.dim_company (
        company_id VARCHAR(50) PRIMARY KEY,
        company_name VARCHAR(255) UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dev.dim_crude (
        dim_crude_id VARCHAR(50) PRIMARY KEY,
        crude_name VARCHAR(255) UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dev.fact_upstream_project_tracker (
        project_id VARCHAR(50) PRIMARY KEY,
        project_name VARCHAR(255) NOT NULL,
        country_id VARCHAR(50) REFERENCES dev.dim_country(dim_country_id),
        operator_id VARCHAR(50) REFERENCES dev.dim_company(company_id),
        partner1_id VARCHAR(50) REFERENCES dev.dim_company(company_id),
        partner2_id VARCHAR(50) REFERENCES dev.dim_company(company_id),
        partner3_id VARCHAR(50) REFERENCES dev.dim_company(company_id),
        partner4_id VARCHAR(50) REFERENCES dev.dim_company(company_id),
        partner5_id VARCHAR(50) REFERENCES dev.dim_company(company_id),
        crude_id VARCHAR(50) REFERENCES dev.dim_crude(dim_crude_id),
        project_status VARCHAR(100),
        project_start_date DATE,
        last_update_date DATE,
        capacity_bbl_per_day NUMERIC,
        carbon_intensity NUMERIC,
        likely_goahead VARCHAR(50),
        field_type VARCHAR(100),
        field VARCHAR(255),
        play_type VARCHAR(100),
        hydrocarbon VARCHAR(100),
        depth VARCHAR(100),
        sanctioned BOOLEAN,
        external_comments TEXT,
        reserves_gas_mmboe VARCHAR(100),
        reserves_liquids_mmbbl VARCHAR(100),
        api_cat VARCHAR(100),
        sulfur_cat VARCHAR(100),
        operator_pc NUMERIC,
        partner1_pc NUMERIC,
        partner2_pc NUMERIC,
        partner3_pc NUMERIC,
        partner4_pc NUMERIC,
        partner5_pc NUMERIC,
        include BOOLEAN
    );

    CREATE TABLE IF NOT EXISTS dev.fact_upstream_tracker_prod_estimates (
        estimate_id SERIAL PRIMARY KEY,
        project_id VARCHAR(50) REFERENCES dev.fact_upstream_project_tracker(project_id),
        "2024_Q1" NUMERIC,
        "2024_Q2" NUMERIC,
        "2024_Q3" NUMERIC,
        "2024_Q4" NUMERIC,
        "2025_Q1" NUMERIC,
        "2025_Q2" NUMERIC,
        "2025_Q3" NUMERIC,
        "2025_Q4" NUMERIC,
        "2026_Q1" NUMERIC,
        "2026_Q2" NUMERIC,
        "2026_Q3" NUMERIC,
        "2026_Q4" NUMERIC,
        "2027_Q1" NUMERIC,
        "2027_Q2" NUMERIC,
        "2027_Q3" NUMERIC,
        "2027_Q4" NUMERIC,
        "2028_Q1" NUMERIC,
        "2028_Q2" NUMERIC,
        "2028_Q3" NUMERIC,
        "2028_Q4" NUMERIC,
        "2029_Q1" NUMERIC,
        "2029_Q2" NUMERIC,
        "2029_Q3" NUMERIC,
        "2029_Q4" NUMERIC
    );

    CREATE TABLE IF NOT EXISTS dev.fact_upstream_tracker_prod_estimates_incremental (
        incremental_id SERIAL PRIMARY KEY,
        project_id VARCHAR(50) REFERENCES dev.fact_upstream_project_tracker(project_id),
        period DATE NOT NULL,
        value NUMERIC
    );
    """)
    print("✓ Tables created")

def seed_countries():
    """Seed countries data"""
    countries_data = [
        {'code': 'USA', 'name': 'United States', 'region': 'North America', 'continent': 'North America', 'opec_grp': 'Non-Opec-Plus'},
        {'code': 'SAU', 'name': 'Saudi Arabia', 'region': 'Middle East', 'continent': 'Asia', 'opec_grp': 'opec'},
        {'code': 'RUS', 'name': 'Russia', 'region': 'Europe', 'continent': 'Europe', 'opec_grp': 'opec_plus'},
        {'code': 'IRN', 'name': 'Iran', 'region': 'Middle East', 'continent': 'Asia', 'opec_grp': 'opec'},
        {'code': 'IRQ', 'name': 'Iraq', 'region': 'Middle East', 'continent': 'Asia', 'opec_grp': 'opec'},
        {'code': 'CAN', 'name': 'Canada', 'region': 'North America', 'continent': 'North America', 'opec_grp': 'Non-Opec-Plus'},
        {'code': 'ARE', 'name': 'United Arab Emirates', 'region': 'Middle East', 'continent': 'Asia', 'opec_grp': 'opec'},
        {'code': 'CHN', 'name': 'China', 'region': 'Asia', 'continent': 'Asia', 'opec_grp': 'Non-Opec-Plus'},
        {'code': 'KWT', 'name': 'Kuwait', 'region': 'Middle East', 'continent': 'Asia', 'opec_grp': 'opec'},
        {'code': 'BRA', 'name': 'Brazil', 'region': 'South America', 'continent': 'South America', 'opec_grp': 'Non-Opec-Plus'},
        {'code': 'NGA', 'name': 'Nigeria', 'region': 'Africa', 'continent': 'Africa', 'opec_grp': 'opec'},
        {'code': 'VEN', 'name': 'Venezuela', 'region': 'South America', 'continent': 'South America', 'opec_grp': 'opec'},
        {'code': 'MEX', 'name': 'Mexico', 'region': 'North America', 'continent': 'North America', 'opec_grp': 'Non-Opec-Plus'},
        {'code': 'NOR', 'name': 'Norway', 'region': 'Europe', 'continent': 'Europe', 'opec_grp': 'Non-Opec-Plus'},
        {'code': 'KAZ', 'name': 'Kazakhstan', 'region': 'Asia', 'continent': 'Asia', 'opec_grp': 'opec_plus'},
    ]
    
    for country_data in countries_data:
        # Check if country already exists
        existing_country = execute_query(f"SELECT * FROM dev.dim_country WHERE country_code = '{country_data['code']}';")
        
        if not existing_country:
            execute_query(f"INSERT INTO dev.dim_country (dim_country_id, country_code, country_long_name, region, continent, opec_grp) VALUES ('{country_data['code']}', '{country_data['code']}', '{country_data['name']}', '{country_data['region']}', '{country_data['continent']}', '{country_data['opec_grp']}');")
    
    print("✓ Countries seeded")

def seed_production_data():
    """Seed production data for the last 5 years"""
    countries_df = execute_query("SELECT dim_country_id, country_code FROM dev.dim_country;")
    if countries_df.empty:
        print("No countries found. Please seed countries first.")
        return
    
    end_date = date.today()
    start_date = end_date - timedelta(days=365*5)
    
    current_date = start_date
    while current_date <= end_date:
        if current_date.day == 1:
            for _, country_row in countries_df.iterrows():
                country_id = country_row['dim_country_id']
                country_code = country_row['country_code']
                
                existing = execute_query(f"SELECT * FROM dev.fact_crude_production WHERE country_id = '{country_id}' AND date = '{current_date.isoformat()}';")
                
                if not existing:
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
                    
                    base = base_production.get(country_code, 1000000)
                    production_bbl = base * (1 + random.uniform(-0.1, 0.1))
                    production_mt = production_bbl * 0.136
                    
                    execute_query(f"INSERT INTO dev.fact_crude_production (country_id, date, production_bbl, production_mt) VALUES ('{country_id}', '{current_date.isoformat()}', {production_bbl}, {production_mt});")
        
        current_date += timedelta(days=1)
    
    print("✓ Production data seeded")

def seed_exports_data():
    """Seed exports data"""
    countries_df = execute_query("SELECT dim_country_id, country_code FROM dev.dim_country;")
    if countries_df.empty:
        return
    
    end_date = date.today()
    start_date = end_date - timedelta(days=365*5)
    
    current_date = start_date
    while current_date <= end_date:
        if current_date.day == 1:
            for _, country_row in countries_df.iterrows():
                country_id = country_row['dim_country_id']
                
                existing = execute_query(f"SELECT * FROM dev.fact_crude_exports WHERE country_id = '{country_id}' AND date = '{current_date.isoformat()}';")
                
                if not existing:
                    production_result = execute_query(f"SELECT production_bbl FROM dev.fact_crude_production WHERE country_id = '{country_id}' AND date = '{current_date.isoformat()}';")
                    if production_result and 'production_bbl' in production_result[0]:
                        production_bbl = production_result[0]['production_bbl']
                        export_ratio = random.uniform(0.5, 0.9)
                        exports_bbl = production_bbl * export_ratio
                        exports_mt = exports_bbl * 0.136
                        
                        execute_query(f"INSERT INTO dev.fact_crude_exports (country_id, date, exports_bbl, exports_mt) VALUES ('{country_id}', '{current_date.isoformat()}', {exports_bbl}, {exports_mt});")
        
        current_date += timedelta(days=1)
    
    print("✓ Exports data seeded")

def seed_imports_data():
    """Seed imports data"""
    countries_df = execute_query("SELECT dim_country_id, country_code FROM dev.dim_country;")
    if countries_df.empty:
        return
    
    end_date = date.today()
    start_date = end_date - timedelta(days=365*5)
    
    current_date = start_date
    while current_date <= end_date:
        if current_date.day == 1:
            for _, country_row in countries_df.iterrows():
                country_id = country_row['dim_country_id']
                
                existing = execute_query(f"SELECT * FROM dev.fact_crude_imports WHERE country_id = '{country_id}' AND date = '{current_date.isoformat()}';")
                
                if not existing:
                    # Imports are typically 20-40% of production for some countries, or more for net importers
                    production_result = execute_query(f"SELECT production_bbl FROM dev.fact_crude_production WHERE country_id = '{country_id}' AND date = '{current_date.isoformat()}';")
                    if production_result and 'production_bbl' in production_result[0]:
                        production_bbl = production_result[0]['production_bbl']
                        import_ratio = random.uniform(0.2, 0.6)
                        imports_bbl = production_bbl * import_ratio
                        imports_mt = imports_bbl * 0.136
                        
                        execute_query(f"INSERT INTO dev.fact_crude_imports (country_id, date, imports_bbl, imports_mt) VALUES ('{country_id}', '{current_date.isoformat()}', {imports_bbl}, {imports_mt});")
        
        current_date += timedelta(days=1)
    
    print("✓ Imports data seeded")

def seed_reserves_data():
    """Seed reserves data (updated annually)"""
    countries_df = execute_query("SELECT dim_country_id, country_code FROM dev.dim_country;")
    if countries_df.empty:
        return
    
    for year in range(2020, date.today().year + 1):
        reserve_date = date(year, 1, 1)
        
        for _, country_row in countries_df.iterrows():
            country_id = country_row['dim_country_id']
            country_code = country_row['country_code']
            
            existing = execute_query(f"SELECT * FROM dev.fact_crude_reserves WHERE country_id = '{country_id}' AND date = '{reserve_date.isoformat()}';")
            
            if not existing:
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
                
                base = base_reserves.get(country_code, 10000000000)
                reserves_bbl = base * (1 + random.uniform(-0.05, 0.05))
                reserves_mt = reserves_bbl * 0.136
                proven_reserves_bbl = reserves_bbl * 0.9
                
                execute_query(f"INSERT INTO dev.fact_crude_reserves (country_id, date, reserves_bbl, reserves_mt, proven_reserves_bbl) VALUES ('{country_id}', '{reserve_date.isoformat()}', {reserves_bbl}, {reserves_mt}, {proven_reserves_bbl});")
    
    print("✓ Reserves data seeded")

def seed_companies():
    print("Seeding companies data...")
    companies_data = [
        {'company_id': 'EXXON', 'company_name': 'ExxonMobil'},
        {'company_id': 'SHELL', 'company_name': 'Shell'},
        {'company_id': 'BP', 'company_name': 'BP Plc'},
        {'company_id': 'CHEVRON', 'company_name': 'Chevron'},
        {'company_id': 'TOTAL', 'company_name': 'TotalEnergies'},
        {'company_id': 'SAUDI_ARAMCO', 'company_name': 'Saudi Aramco'},
        {'company_id': 'ADNOC', 'company_name': 'ADNOC'},
        {'company_id': 'QATAR_ENERGY', 'company_name': 'QatarEnergy'},
        {'company_id': 'PEMEX', 'company_name': 'Pemex'},
        {'company_id': 'PETROBRAS', 'company_name': 'Petrobras'},
    ]
    for company_data in companies_data:
        existing_company = execute_query(f"SELECT * FROM dev.dim_company WHERE company_id = '{company_data['company_id']}';")
        if not existing_company:
            execute_query(f"INSERT INTO dev.dim_company (company_id, company_name) VALUES ('{company_data['company_id']}', '{company_data['company_name']}');")
    print("✓ Companies seeded")

def seed_crudes():
    print("Seeding crude data...")
    crude_data = [
        {'crude_id': 'ARAB_LIGHT', 'crude_name': 'Arab Light'},
        {'crude_id': 'WTI', 'crude_name': 'WTI'},
        {'crude_id': 'BRENT', 'crude_name': 'Brent'},
        {'crude_id': 'URALS', 'crude_name': 'Urals'},
        {'crude_id': 'BONNY_LIGHT', 'crude_name': 'Bonny Light'},
    ]
    for crude_entry in crude_data:
        existing_crude = execute_query(f"SELECT * FROM dev.dim_crude WHERE dim_crude_id = '{crude_entry['crude_id']}';")
        if not existing_crude:
            execute_query(f"INSERT INTO dev.dim_crude (dim_crude_id, crude_name) VALUES ('{crude_entry['crude_id']}', '{crude_entry['crude_name']}');")
    print("✓ Crudes seeded")

def seed_upstream_projects_data():
    print("Seeding upstream project data...")
    projects_data = [
        {
            'project_id': 'PROJ001',
            'project_name': 'Permian Basin Expansion',
            'country_id': 'USA',
            'operator_id': 'EXXON',
            'project_status': 'Operating',
            'project_start_date': date(2020, 1, 1),
            'last_update_date': date(2025, 11, 15),
            'capacity_bbl_per_day': 1500000,
            'carbon_intensity': 15,
            'likely_goahead': 'Y',
            'field_type': 'Onshore',
            'field': 'Permian',
            'play_type': 'Shale',
            'hydrocarbon': 'Oil',
            'depth': 'Deep',
            'sanctioned': True,
            'external_comments': 'Major expansion project.',
            'reserves_gas_mmboe': '500',
            'reserves_liquids_mmbbl': '5000',
            'api_cat': 'Light',
            'sulfur_cat': 'Sweet',
            'operator_pc': 100,
            'include': True
        },
        {
            'project_id': 'PROJ002',
            'project_name': 'Ghawar Increment',
            'country_id': 'SAU',
            'operator_id': 'SAUDI_ARAMCO',
            'project_status': 'Planned',
            'project_start_date': date(2026, 1, 1),
            'last_update_date': date(2025, 10, 20),
            'capacity_bbl_per_day': 500000,
            'carbon_intensity': 10,
            'likely_goahead': 'Y',
            'field_type': 'Onshore',
            'field': 'Ghawar',
            'play_type': 'Conventional',
            'hydrocarbon': 'Oil',
            'depth': 'Shallow',
            'sanctioned': False,
            'external_comments': 'Potential new development in existing field.',
            'reserves_gas_mmboe': '100',
            'reserves_liquids_mmbbl': '1000',
            'api_cat': 'Medium',
            'sulfur_cat': 'Sour',
            'operator_pc': 100,
            'include': True
        },
        {
            'project_id': 'PROJ003',
            'project_name': 'Offshore Brazil New Field',
            'country_id': 'BRA',
            'operator_id': 'PETROBRAS',
            'partner1_id': 'SHELL',
            'project_status': 'Discovery',
            'project_start_date': None,
            'last_update_date': date(2025, 9, 10),
            'capacity_bbl_per_day': None,
            'carbon_intensity': None,
            'likely_goahead': 'Uncertain',
            'field_type': 'Offshore',
            'field': 'New Pre-Salt',
            'play_type': 'Pre-Salt',
            'hydrocarbon': 'Oil',
            'depth': 'Ultra-Deep',
            'sanctioned': False,
            'external_comments': 'Recent discovery, appraisal ongoing.',
            'reserves_gas_mmboe': '200',
            'reserves_liquids_mmbbl': '2000',
            'api_cat': 'Heavy',
            'sulfur_cat': 'Sweet',
            'operator_pc': 70,
            'partner1_pc': 30,
            'include': True
        }
    ]
    
    for project_data in projects_data:
        project_id = project_data['project_id']
        existing_project = execute_query(f"SELECT * FROM dev.fact_upstream_project_tracker WHERE project_id = '{project_id}';")
        
        if not existing_project:
            columns = ', '.join(project_data.keys())
            values = ', '.join([f"'{(v.isoformat() if isinstance(v, date) else str(v)).replace("'", "''')}'" if v is not None else 'NULL' for v in project_data.values()])
            execute_query(f"INSERT INTO dev.fact_upstream_project_tracker ({columns}) VALUES ({values});")
    
    print("✓ Upstream project data seeded")

def seed_upstream_estimates_data():
    print("Seeding upstream production estimates...")
    estimates = [
        {'project_id': 'PROJ001', '2024_Q1': 1000, '2024_Q2': 1050, '2024_Q3': 1100, '2024_Q4': 1150,
            '2025_Q1': 1200, '2025_Q2': 1250, '2025_Q3': 1300, '2025_Q4': 1350,
            '2026_Q1': 1400, '2026_Q2': 1450, '2026_Q3': 1500, '2026_Q4': 1500,
            '2027_Q1': 1500, '2027_Q2': 1450, '2027_Q3': 1400, '2027_Q4': 1350,
            '2028_Q1': 1300, '2028_Q2': 1250, '2028_Q3': 1200, '2028_Q4': 1150,
            '2029_Q1': 1100, '2029_Q2': 1050, '2029_Q3': 1000, '2029_Q4': 950},
        {'project_id': 'PROJ002', '2024_Q1': 0, '2024_Q2': 0, '2024_Q3': 0, '2024_Q4': 0,
            '2025_Q1': 0, '2025_Q2': 0, '2025_Q3': 0, '2025_Q4': 0,
            '2026_Q1': 100, '2026_Q2': 200, '2026_Q3': 300, '2026_Q4': 400,
            '2027_Q1': 450, '2027_Q2': 500, '2027_Q3': 480, '2027_Q4': 450,
            '2028_Q1': 420, '2028_Q2': 400, '2028_Q3': 380, '2028_Q4': 350,
            '2029_Q1': 320, '2029_Q2': 300, '2029_Q3': 280, '2029_Q4': 250},
    ]

    for estimate in estimates:
        project_id = estimate['project_id']
        existing_estimate = execute_query(f"SELECT * FROM dev.fact_upstream_tracker_prod_estimates WHERE project_id = '{project_id}';")
        if not existing_estimate:
            columns = ', '.join(estimate.keys())
            values = ', '.join([str(v) if v is not None else 'NULL' for v in estimate.values()])
            execute_query(f"INSERT INTO dev.fact_upstream_tracker_prod_estimates ({columns}) VALUES ({values});")

    print("✓ Upstream production estimates seeded")

def seed_upstream_estimates_incremental_data():
    print("Seeding upstream production estimates incremental...")
    incremental_estimates = [
        {'project_id': 'PROJ001', 'period': date(2024, 1, 1), 'value': 1000},
        {'project_id': 'PROJ001', 'period': date(2024, 4, 1), 'value': 1050},
        {'project_id': 'PROJ001', 'period': date(2024, 7, 1), 'value': 1100},
        {'project_id': 'PROJ001', 'period': date(2024, 10, 1), 'value': 1150},
        {'project_id': 'PROJ002', 'period': date(2026, 1, 1), 'value': 100},
        {'project_id': 'PROJ002', 'period': date(2026, 4, 1), 'value': 200},
    ]

    for incremental_estimate in incremental_estimates:
        project_id = incremental_estimate['project_id']
        period = incremental_estimate['period'].isoformat()
        existing_estimate = execute_query(f"SELECT * FROM dev.fact_upstream_tracker_prod_estimates_incremental WHERE project_id = '{project_id}' AND period = '{period}';")
        if not existing_estimate:
            columns = ', '.join(incremental_estimate.keys())
            values = ', '.join([f"'{(v.isoformat() if isinstance(v, date) else str(v)).replace("'", "''')}'" if v is not None else 'NULL' for v in incremental_estimate.values()])
            execute_query(f"INSERT INTO dev.fact_upstream_tracker_prod_estimates_incremental ({columns}) VALUES ({values});")
    print("✓ Upstream production estimates incremental seeded")

def init_database():
    """Initialize database with tables and sample data"""
    create_tables()
    
    print("\nSeeding data...")
    seed_countries()
    seed_companies()
    seed_crudes()
    seed_production_data()
    seed_exports_data()
    seed_imports_data()
    seed_reserves_data()
    seed_upstream_projects_data()
    seed_upstream_estimates_data()
    seed_upstream_estimates_incremental_data()
    
    print("\n✓ Database initialization complete!")

if __name__ == '__main__':
    init_database()

