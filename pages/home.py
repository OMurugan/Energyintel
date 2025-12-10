import dash
from dash import html, dcc


dash.register_page(
    __name__,
    path="/",
    name="Home",
)


SECTIONS = [
    {
        "title": "Country",
        "path": "/country-overview",
        "links": [
            ("Country Overview", "/country-overview"),
            ("Country Profile", "/country-profile"),
        ],
    },
    {
        "title": "Crude",
        "path": "/crude-overview",
        "links": [
            ("Crude Overview", "/crude-overview"),
            ("Crude Profile", "/crude-profile"),
            ("Crude Comparison", "/crude-comparison"),
            ("Crude Quality Comparison", "/crude-quality-comparison"),
            ("Crude Carbon Intensity", "/crude-carbon"),
        ],
    },
    {
        "title": "Trade",
        "path": "/trade/imports-country-detail",
        "links": [
            ("Imports - Country Detail", "/trade/imports-country-detail"),
            ("Imports - Country Comparison", "/trade/imports-country-comparison"),
            ("Global Exports", "/trade/global-exports"),
            ("Russian Exports by Terminal and Exporting Company", "/trade/russian-exports"),
        ],
    },
    {
        "title": "Prices",
        "path": "/prices/global-crude-prices",
        "links": [
            ("Global Crude Prices", "/prices/global-crude-prices"),
            ("Price Scorecard for Key World Oil Grades", "/prices/price-scorecard"),
            ("Gross Product Worth and Margins", "/prices/gross-product-worth-and-margins"),
        ],
    },
    {
        "title": "Upstream Projects",
        "path": "/projects-by-country",
        "links": [
            ("Projects by Country", "/projects-by-country"),
            ("Projects by Company", "/projects-by-company"),
            ("Projects by Time", "/projects-by-time"),
            ("Projects by Status", "/projects-by-status"),
            ("Latest Updates", "/projects-latest"),           
        ],
    },
    {
        "title": "Methodology",
        "path": "/projects-tracker",
        "links": [
            ("Upstream Oil Projects Tracker", "/projects-tracker"),
            ("Carbon Intensity", "/projects-carbon"),
        ],
    },
]


def layout():
    return html.Div(
        [
            html.H2("EnergyIntel Dash Pages"),
            html.P("Main tabs and relevant page links:"),
            html.Div(
                [
                    html.Div(
                        [
                            html.H4(
                                html.A(section["title"], href=section["path"]),
                                style={"marginBottom": "8px"},
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        html.A(name, href=href),
                                        style={"marginBottom": "4px"},
                                    )
                                    for name, href in section["links"]
                                ],
                                style={"marginTop": "4px", "marginBottom": "16px"},
                            ),
                        ],
                        style={"marginBottom": "12px"},
                    )
                    for section in SECTIONS
                ]
            ),
        ],
        style={"padding": "24px"},
    )


def init_callbacks(app, server):
    # No callbacks for the home page
    return None


