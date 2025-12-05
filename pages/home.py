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
        "path": "/country-overview#country",
        "links": [
            ("Country Overview", "/country-overview"),
            ("Country Profile", "/country-profile"),
        ],
    },
    {
        "title": "Crude",
        "path": "/crude-overview#crude",
        "links": [
            ("Crude Overview", "/crude-overview"),
            ("Crude Profile", "/crude-profile"),
            ("Crude Comparison", "/crude-comparison"),
            ("Crude Quality Comparison", "/crude-quality"),
            ("Crude Carbon Intensity", "/crude-carbon"),
        ],
    },
    {
        "title": "Trade",
        "path": "/imports-detail#trade",
        "links": [
            ("Imports - Country Detail", "/imports-detail"),
            ("Imports - Country Comparison", "/imports-comparison"),
            ("Global Exports", "/global-exports"),
            ("Russian Exports by Terminal and Exporting Company", "/russian-exports"),
        ],
    },
    {
        "title": "Prices",
        "path": "/global-prices#prices",
        "links": [
            ("Global Crude Prices", "/global-prices"),
            ("Price Scorecard for Key World Oil Grades", "/price-scorecard"),
            ("Gross Product Worth and Margins", "/gpw-margins"),
        ],
    },
    {
        "title": "Upstream Projects",
        "path": "/projects-by-country#upstream-projects",
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
        "path": "/projects-tracker#methodology",
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


