import typing as t
from utils import date_utils, share_data_utils
from utils.ticker_mapping import ticker_currency_info
from models.purchase import Purchase, Price

import pandas as pd


def _parse_number(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    # remove commas and currency symbols
    s = s.replace(",", "").replace("$", "").replace("£", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_rsu_df(df: pd.DataFrame, ticker: t.Optional[str] = None) -> t.List[Purchase]:
    """Parse a Morgan Stanley RSU-like DataFrame and return list of Purchase objects.

    Assumptions / behaviour:
    - The DataFrame should have columns: 'Date', 'Type' (with 'Released Shares'),
      'Order Status' (ideally 'Completed') and 'Quantity'.
    - If `ticker` is not provided, the parser will try to read a 'Symbol' column.
      If neither is available it will raise AssertionError.
    - Date format expected: 25-Dec-2024 (%%d-%%b-%%Y)
    """
    purchases: t.List[Purchase] = []

    # determine ticker
    determined_ticker = None
    if ticker:
        determined_ticker = ticker.lower()
    elif "Symbol" in df.columns:
        # take symbol from first non-empty value
        for v in df["Symbol"]:
            if v and str(v).strip():
                determined_ticker = str(v).strip().lower()
                break
    assert (
        determined_ticker is not None
    ), "Ticker not found: please pass `ticker` or include a 'Symbol' column"
    # normalize some common column name variants locally
    # prefer date header variants like 'Vest Date', 'Date'
    date_candidates = ["Date", "Vest Date", "VestDate", "Trade Date", "Transaction Date"]
    status_candidates = ["Order Status", "Status"]
    qty_candidates = ["Net Share Proceeds", "Quantity", "Qty. or Amount", "Qty"]

    # rename detected date column to 'Date' so parsing below is consistent
    for c in date_candidates:
        if c in df.columns and c != "Date":
            df.rename(columns={c: "Date"}, inplace=True)
            break

    # rename status column to 'Order Status' if needed
    for c in status_candidates:
        if c in df.columns and c != "Order Status":
            df.rename(columns={c: "Order Status"}, inplace=True)
            break

    for _, row in df.iterrows():
        typ = None
        if "Type" in df.columns:
            typ = row.get("Type")
        elif "Order Type" in df.columns:
            typ = row.get("Order Type")

        status = row.get("Order Status") if "Order Status" in df.columns else None

        if typ is None:
            continue

        typ_s = str(typ).strip().lower()
        # accept 'release', 'released', 'released shares' etc.
        if ("release" in typ_s) and (
            status is None or "complete" in str(status).strip().lower()
        ):
            date_str = row.get("Date")
            if not date_str or str(date_str).strip() == "":
                continue
            # date_str may already be a string in DD-Mon-YYYY or a datetime object
            if hasattr(date_str, "strftime"):
                # datetime -> convert to named month format
                date_obj = date_utils.parse_named_mon(date_str.strftime("%d-%b-%Y"))
            else:
                date_obj = date_utils.parse_named_mon(str(date_str).strip())

            # find quantity from preferred candidates (Net Share Proceeds first)
            qty_val = None
            for qc in qty_candidates:
                if qc in df.columns:
                    qty_val = row.get(qc)
                    if qty_val is not None and str(qty_val).strip() != "":
                        break

            quantity = _parse_number(qty_val)

            # obtain FMV using share_data_utils (consistent with other parsers)
            fmv = share_data_utils.get_fmv(determined_ticker, date_obj["time_in_millis"])
            currency = ticker_currency_info.get(determined_ticker, "USD")
            purchases.append(
                Purchase(
                    date=date_obj,
                    purchase_fmv=Price(fmv, currency),
                    quantity=quantity,
                    ticker=determined_ticker,
                )
            )

    return purchases


def parse(
    input_file_abs_path: str, output_folder_abs_path: str, ticker: t.Optional[str] = None
) -> t.List[Purchase]:
    """Reads CSV or Excel and returns parsed purchases.

    This helper supports .csv and .xlsx/.xls files. For CSV it reads directly.
    If the DataFrame contains real datetime values in the 'Date' column they are
    converted to 'DD-Mon-YYYY' string format before parsing. Optionally pass
    `ticker` when the sheet lacks a Symbol column.
    """
    if str(input_file_abs_path).lower().endswith(".csv"):
        df = pd.read_csv(input_file_abs_path)
    else:
        # try excel
        xl = pd.ExcelFile(input_file_abs_path, engine="openpyxl")
        # pick first sheet by default
        df = xl.parse(xl.sheet_names[0], skiprows=0, header=0)

    # normalize Date if it's a datetime dtype
    if "Date" in df.columns and pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df["Date"] = df["Date"].dt.strftime("%d-%b-%Y")

    purchases = parse_rsu_df(df, ticker=ticker)

    return purchases
