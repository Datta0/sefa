import typing as t

from models.org import Organization

ticker_org_info: t.Dict[str, Organization] = {
    "adbe": Organization(
        name="Adobe Incorporation",
        address="345 Park Avenue San Jose, CA",
        country_name="2 - United States",
        zip_code="95110",
        nature="Listed",
    ),
    "ntnx": Organization(
        name="Nutanix, Inc.",
        address="1740 Technology Drive San Jose, CA",
        country_name="2 - United States",
        zip_code="95110",
        nature="Listed",
    ),
    "goog": Organization(
        name="Alphabet Inc.",
        address="1600 Amphitheatre Parkway Mountain View, CA",
        country_name="2 - United States",
        zip_code="94043",
        nature="Listed",
    ),
    "msft": Organization(
        name="Microsoft Corporation",
        address="One Microsoft Way Redmond, WA",
        country_name="2 - United States",
        zip_code="98052",
        nature="Listed",
    ),
    "crm": Organization(
        name="Salesforce.com, Inc.",
        address="415 Mission Street San Francisco, CA",
        country_name="2 - United States",
        zip_code="94105",
        nature="Listed",
    ),
    "amzn": Organization(
        name="Amazon.com, Inc.",
        address="410 Terry Avenue North Seattle, WA",
        country_name="2 - United States",
        zip_code="98109",
        nature="Listed",
    ),
    "meta": Organization(
        name="Meta Platforms, Inc.",
        address="1 Hacker Way Menlo Park, CA",
        country_name="2 - United States",
        zip_code="94025",
        nature="Listed",
    ),
    "tsla": Organization(
        name="Tesla, Inc.",
        address="1 Tesla Road Austin, TX",
        country_name="2 - United States",
        zip_code="78725",
        nature="Listed",
    ),
    "nvda": Organization(
        name="NVIDIA Corporation",
        address="2788 San Tomas Expressway Santa Clara, CA",
        country_name="2 - United States",
        zip_code="95051",
        nature="Listed",
    ),
    "aapl": Organization(
        name="Apple Inc.",
        address="One Apple Park Way Cupertino, CA",
        country_name="2 - United States",
        zip_code="95014",
        nature="Listed",
    ),
}

ticker_currency_info: t.Dict[str, str] = {
    "adbe": "USD",
    "ntnx": "USD",
    "goog": "USD",
    "msft": "USD",
    "crm": "USD",
    "amzn": "USD",
    "meta": "USD",
    "tsla": "USD",
    "nvda": "USD",
    "aapl": "USD",
}
