"""
Country to ISO-3 code mappings for consistent use across all dashboards.

This module provides a centralized mapping of country names to their ISO Alpha-3 codes,
eliminating duplication across multiple dashboard files.
"""

# Master country to ISO-3 mapping combining all variations from:
# - projects_by_country.py
# - country_profile.py  
# - imports_comparison.py
COUNTRY_TO_ISO = {
    # Core countries (common across all files)
    "United States": "USA",
    "United States of America": "USA",  # Normalized name variant
    "United Kingdom": "GBR",
    "Saudi Arabia": "SAU",
    "Russia": "RUS",
    "China": "CHN",
    "India": "IND",
    "Brazil": "BRA",
    "Canada": "CAN",
    "Mexico": "MEX",
    "Venezuela": "VEN",
    "Nigeria": "NGA",
    "Angola": "AGO",
    "Algeria": "DZA",
    "Libya": "LBY",
    "Iraq": "IRQ",
    "Iran": "IRN",
    "Kuwait": "KWT",
    "United Arab Emirates": "ARE",
    "Abu Dhabi": "ARE",  # Abu Dhabi is part of UAE
    "Dubai": "ARE",  # Dubai is part of UAE
    "Qatar": "QAT",
    "Norway": "NOR",
    "Kazakhstan": "KAZ",
    "Azerbaijan": "AZE",
    "Indonesia": "IDN",
    "Malaysia": "MYS",
    "Thailand": "THA",
    "Vietnam": "VNM",
    "Australia": "AUS",
    "Colombia": "COL",
    "Ecuador": "ECU",
    "Argentina": "ARG",
    "Chile": "CHL",
    "Peru": "PER",
    "Egypt": "EGY",
    "Sudan": "SDN",
    "South Sudan": "SSD",
    "Gabon": "GAB",
    "Congo": "COG",
    "Republic of the Congo": "COG",
    "Equatorial Guinea": "GNQ",
    "Cameroon": "CMR",
    "Ghana": "GHA",
    "Côte d'Ivoire": "CIV",
    "Cote d'Ivoire": "CIV",  # Without accent
    "Ivory Coast": "CIV",  # Alternative name
    "Tunisia": "TUN",
    "Oman": "OMN",
    "Yemen": "YEM",
    "Turkmenistan": "TKM",
    "Uzbekistan": "UZB",
    "Georgia": "GEO",
    "Turkey": "TUR",
    "Greece": "GRC",
    "Italy": "ITA",
    "Spain": "ESP",
    "France": "FRA",
    "Germany": "DEU",
    "Netherlands": "NLD",
    "Belgium": "BEL",
    "Denmark": "DNK",
    "Sweden": "SWE",
    "Finland": "FIN",
    "Poland": "POL",
    "Romania": "ROU",
    "Bulgaria": "BGR",
    "Ukraine": "UKR",
    "Japan": "JPN",
    "South Korea": "KOR",
    "Philippines": "PHL",
    "Singapore": "SGP",
    "Brunei": "BRN",
    "Myanmar": "MMR",
    "Bangladesh": "BGD",
    "Pakistan": "PAK",
    "Sri Lanka": "LKA",
    
    # Additional countries from projects_by_country.py
    "Belarus": "BLR",
    "Lithuania": "LTU",
    "Latvia": "LVA",
    "Estonia": "EST",
    "Portugal": "PRT",
    "Ireland": "IRL",
    "Austria": "AUT",
    "Switzerland": "CHE",
    "Czech Republic": "CZE",
    "Czechia": "CZE",  # Alternative name
    "Slovakia": "SVK",
    "Hungary": "HUN",
    "Slovenia": "SVN",
    "Croatia": "HRV",
    "Serbia": "SRB",
    "Bosnia and Herzegovina": "BIH",
    "Montenegro": "MNE",
    "North Macedonia": "MKD",
    "Albania": "ALB",
    "Morocco": "MAR",
    "Kenya": "KEN",
    "Ethiopia": "ETH",
    "Tanzania": "TZA",
    "Uganda": "UGA",
    "Chad": "TCD",
    "Niger": "NER",
    "Suriname": "SUR",
    "Senegal": "SEN",
    "Trinidad and Tobago": "TTO",
    "Papua New Guinea": "PNG",
    "Guyana": "GUY",
    "Bahrain": "BHR",
}

# Optional pycountry fallback
try:
    import pycountry
except ImportError:
    pycountry = None


def get_iso_code(country_name):
    """
    Return ISO Alpha-3 code for a country name.
    
    Args:
        country_name (str): Country name to look up
        
    Returns:
        str or None: ISO Alpha-3 code if found, None otherwise
    """
    if not country_name:
        return None
    
    country_clean = str(country_name).strip()
    if not country_clean:
        return None
    
    # First try direct lookup in our mapping
    if country_clean in COUNTRY_TO_ISO:
        return COUNTRY_TO_ISO[country_clean]
    
    # Try pycountry as fallback if available
    if pycountry:
        try:
            match = pycountry.countries.search_fuzzy(country_clean)
            if match:
                return match[0].alpha_3
        except Exception:
            pass
    
    return None