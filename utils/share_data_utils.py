from utils.runtime_utils import warn_missing_module

warn_missing_module("pandas")
import pandas as pd
import os
import typing as t

from . import date_utils, logger
from .ticker_mapping import ticker_currency_info
from .rates import rbi_rates_utils


def __validate_dates(
    historic_entry_time_in_ms: int,
    desired_purchase_time_in_ms: int,
    used_fmv_time_in_ms: int,
):
    if historic_entry_time_in_ms > desired_purchase_time_in_ms:
        raise AssertionError(
            f"Historical FMV date {date_utils.log_timestamp(historic_entry_time_in_ms)} "
            + "can NOT be newer than purchase date "
            + f"= {date_utils.log_timestamp(desired_purchase_time_in_ms)}"
        )
    days_diff = (
        date_utils.last_work_day_in_ms(desired_purchase_time_in_ms)
        - historic_entry_time_in_ms
    ) / (24 * 60 * 60 * 1000)

    date_utils.last_work_day_in_ms(desired_purchase_time_in_ms)

    if days_diff > 0:
        msg = (
            f"Historical FMV at {date_utils.log_timestamp(desired_purchase_time_in_ms)} "
            + "was NOT available(maybe due to Public Holiday or weekends) last available data is "
            + f"{int(days_diff)} days old(on {date_utils.display_time(historic_entry_time_in_ms)})"
        )
        logger.log(msg)
        logger.log(
            f"Hence using the next available FMV at {date_utils.log_timestamp(used_fmv_time_in_ms)}"
        )
        # if days_diff > 2:
        #     raise Exception(msg)


TimedFmv = t.TypedDict("TimedFmv", {"entry_time_in_millis": int, "fmv": float})


TimedFmvWithInrRate = t.TypedDict(
    "TimedFmvWithInrRate",
    {
        "entry_time_in_millis": int,
        "fmv": float,
        "inr_rate": float,
    },
)


price_map_cache: t.Dict[str, t.List[TimedFmv]] = {}


def __init_map(ticker: str) -> t.List[TimedFmv]:
    if ticker not in price_map_cache:
        print(f"Parsing FMV price map for ticker = {ticker}")
        ticker_price_map: t.List[TimedFmv] = []
        script_path = os.path.realpath(os.path.dirname(__file__))
        historic_share_path = os.path.join(
            script_path,
            os.pardir,
            "historic_data",
            "shares",
            ticker.lower(),
            "data.csv",
        )
        if not os.path.exists(historic_share_path):
            raise AssertionError(
                f"Historic share data for share {ticker} NOT present at {historic_share_path}"
            )
        df = pd.read_csv(historic_share_path)

        # locate columns flexibly (some CSVs use 'Close/Last')
        date_col = next((c for c in df.columns if c.strip().lower() == "date"), "Date")
        close_col = next(
            (c for c in df.columns if "close" in c.strip().lower()),
            None,
        )
        if close_col is None:
            raise AssertionError(f"No close column found in {historic_share_path}; cols={list(df.columns)}")

        for _, data in df.iterrows():
            raw_date = data[date_col]
            # support common date formats: MM/DD/YYYY, YYYY-MM-DD, and named months
            parsed = None
            for parser in (date_utils.parse_mm_dd, date_utils.parse_yyyy_mm_dd, date_utils.parse_named_mon):
                try:
                    parsed = parser(str(raw_date))
                    break
                except Exception:
                    continue
            if parsed is None:
                raise ValueError(f"Unable to parse date '{raw_date}' in {historic_share_path}")

            entry_time_in_ms = parsed["time_in_millis"]

            # normalize close value: strip $ and commas and convert to float
            raw_close = data[close_col]
            if isinstance(raw_close, str):
                raw_close = raw_close.strip().replace("$", "").replace(",", "")
            try:
                fmv = float(raw_close)
            except Exception:
                raise ValueError(f"Unable to parse close value '{data[close_col]}' for date {raw_date}")

            ticker_price_map.append({"entry_time_in_millis": entry_time_in_ms, "fmv": fmv})

        price_map_cache[ticker] = ticker_price_map

    return price_map_cache[ticker]


def get_fmv(ticker: str, purchase_time_in_ms: int) -> float:
    logger.debug_log(
        f"{ticker}: Querying FMV at {date_utils.display_time(purchase_time_in_ms)}"
    )
    previous_entry_data = None
    # Ensure we iterate the price map in ascending time order so that
    # `previous_entry_data` semantically represents the last available
    # historical price before `purchase_time_in_ms`. CSVs may be newest-first
    # which would break the previous logic.
    for entry_data in sorted(__init_map(ticker), key=lambda e: e["entry_time_in_millis"]):
        entry_time_in_ms = entry_data["entry_time_in_millis"]
        if entry_time_in_ms >= purchase_time_in_ms:
            if entry_time_in_ms > purchase_time_in_ms:
                # if there's no previous entry, can't validate; return nearest available FMV
                if previous_entry_data is None:
                    return entry_data["fmv"]
                previous_entry_time_in_ms = previous_entry_data["entry_time_in_millis"]
                __validate_dates(
                    previous_entry_time_in_ms, purchase_time_in_ms, entry_time_in_ms
                )
                return entry_data["fmv"]
            return entry_data["fmv"]

        previous_entry_data = entry_data
    ticker_share_price = os.path.join("historic_data", "shares", ticker, "data.csv")
    raise AssertionError(
        f"No FMV data for share ticker {ticker} in {ticker_share_price} for date "
        + f"{date_utils.log_timestamp(purchase_time_in_ms)}"
    )


def get_closing_price(ticker: str, end_time_in_ms: int) -> float:
    price_map = list(
        filter(
            lambda price: price["entry_time_in_millis"] <= end_time_in_ms,
            sorted(
                __init_map(ticker),
                key=lambda price: price["entry_time_in_millis"],
                reverse=True,
            ),
        )
    )

    return price_map[0]["fmv"]


def get_peak_price_in_inr(
    ticker: str, start_time_in_ms: int, end_time_in_ms: int
) -> float:
    if start_time_in_ms > end_time_in_ms:
        raise AssertionError(
            f"start_time_in_ms = {start_time_in_ms} is greater "
            + f"than equal to end_time_in_ms = {end_time_in_ms}"
        )

    # filter and sort ascending (older -> newer) so per-day INR calculations are consistent
    price_map = [
        p
        for p in sorted(__init_map(ticker), key=lambda price: price["entry_time_in_millis"])
        if p["entry_time_in_millis"] >= start_time_in_ms and p["entry_time_in_millis"] <= end_time_in_ms
    ]

    if not price_map:
        raise AssertionError(
            f"No price data for ticker={ticker} between {date_utils.display_time(start_time_in_ms)} and {date_utils.display_time(end_time_in_ms)}"
        )

    # build list of per-day values with INR conversion applied per-day
    enriched = []
    for price in price_map:
        inr_rate = rbi_rates_utils.get_rate_for_prev_mon_for_time_in_ms(
            ticker_currency_info[ticker], price["entry_time_in_millis"]
        )
        enriched.append({
            **price,
            "inr_rate": inr_rate,
            "effective_inr": price["fmv"] * inr_rate,
        })

    # debug output: full per-day breakdown
    logger.debug_log_json(
        {
            "ticker": ticker,
            "start_time": date_utils.display_time(start_time_in_ms),
            "end_time": date_utils.display_time(end_time_in_ms),
            "per_day": [
                {
                    "date": date_utils.display_time(p["entry_time_in_millis"]),
                    "fmv_usd": p["fmv"],
                    "inr_rate": p["inr_rate"],
                    "effective_inr": p["effective_inr"],
                }
                for p in enriched
            ],
        }
    )

    # pick the day with highest effective_inr
    max_value = max(enriched, key=lambda p: p["effective_inr"])
    peak_price_in_inr = max_value["effective_inr"]

    logger.log(
        f"Peak price for ticker = {ticker} from {date_utils.display_time(start_time_in_ms)} "
        + f"to {date_utils.display_time(end_time_in_ms)} is {peak_price_in_inr} "
        + f"INR (USD {max_value['fmv']} on {date_utils.display_time(max_value['entry_time_in_millis'])} at rate {max_value['inr_rate']})"
    )

    return peak_price_in_inr


def get_peak_fmv(ticker: str, start_time_in_ms: int, end_time_in_ms: int) -> float:
    """Return peak FMV in the share's currency (USD) between start and end (inclusive).

    This mirrors the filtering used in get_peak_price_in_inr but returns the USD FMV
    without converting to INR. Caller can decide which FX rate to apply.
    """
    if start_time_in_ms > end_time_in_ms:
        raise AssertionError(
            f"start_time_in_ms = {start_time_in_ms} is greater "
            + f"than equal to end_time_in_ms = {end_time_in_ms}"
        )

    price_map = list(
        filter(
            lambda price: price["entry_time_in_millis"] <= end_time_in_ms
            and price["entry_time_in_millis"] >= start_time_in_ms,
            sorted(__init_map(ticker), key=lambda price: price["entry_time_in_millis"], reverse=True),
        )
    )
    if not price_map:
        raise AssertionError(
            f"No price data for ticker={ticker} between {date_utils.display_time(start_time_in_ms)} and {date_utils.display_time(end_time_in_ms)}"
        )

    max_value = max(price_map, key=lambda price: price["fmv"])
    return max_value["fmv"]
