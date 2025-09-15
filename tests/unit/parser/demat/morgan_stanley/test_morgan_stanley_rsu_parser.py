import pandas as pd
from parser.demat.morgan_stanley import morgan_stanley_rsu_parser


def test_parse_morgan_stanley_rsu_from_dataframe():
    data = {
        "Date": ["25-Dec-2024", "25-Jan-2025", "25-Feb-2025", "25-Mar-2025"],
        "Order Number": ["N/A", "N/A", "N/A", "N/A"],
        "Plan": ["GSU Class C"] * 4,
        "Type": ["Released Shares"] * 4,
        "Order Status": ["Completed"] * 4,
        "Price": ["17,440.85452", "17,823.09322", "15,994.879944", "15,000.882768"],
        "Quantity": ["10.332", "5.511", "4.821", "5.517"],
        "Net Share Proceeds": ["$0.00"] * 4,
        "Tax Payment Method": ["N/A"] * 4,
        "Symbol": ["ADBE"] * 4,
    }
    df = pd.DataFrame(data)
    purchases = morgan_stanley_rsu_parser.parse_rsu_df(df)
    assert len(purchases) == 4
    # spot check first row
    first = purchases[0]
    assert first.ticker == "adbe"
    assert first.quantity == 10.332
    assert first.date["disp_time"] == "25-Dec-2024"
