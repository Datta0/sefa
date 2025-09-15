#!/usr/bin/env python3
"""Parse a Morgan Stanley RSU file and convert to FA entries (FAA3) CSV used for ITR.

This script runs the demat parser then calls the itr FAA3 converter to produce
the `fa_entries.csv` under output/<ticker>/fa_entries.csv (same layout as etrade flow).

Usage:
  python scripts/run_morgan_to_fa.py --input /path/to/file.xlsx --out ./output --ticker goog --calendar-mode calendar --assessment-year 2025
"""
import argparse
import os
import sys
from datetime import datetime

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from parser.demat.morgan_stanley import morgan_stanley_rsu_parser as ms_parser
from parser.itr import faa3_parser
from utils import logger
import json
from models.purchase import Purchase, Price


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input Morgan Stanley xlsx/csv file")
    ap.add_argument("--out", required=True, help="Output directory (will contain purchases.json and fa_entries.csv)")
    ap.add_argument("--ticker", required=True, help="Ticker for the holdings (e.g., goog)")
    ap.add_argument("--calendar-mode", choices=["calendar","financial"], default="calendar")
    ap.add_argument("--assessment-year", type=int, default=datetime.now().year, help="Assessment year used for ITR computations")
    ap.add_argument("--verbose", action="store_true", help="Enable verbose debug logging")
    args = ap.parse_args()

    if args.verbose:
        logger.set_debug(True)

    # parse purchases or load pre-parsed JSON
    if str(args.input).lower().endswith('.json'):
        # expect a list of purchase dicts as produced by run_morgan_parser
        with open(args.input) as f:
            data = json.load(f)
        purchases = [
            Purchase(
                date=d['date'],
                purchase_fmv=Price(
                    d['purchase_fmv'].get('price') or d['purchase_fmv'].get('price', 0),
                    d['purchase_fmv'].get('currency_code') or d['purchase_fmv'].get('currency') or 'USD',
                ),
                quantity=d['quantity'],
                ticker=d['ticker'],
            )
            for d in data
        ]
    else:
        # parse purchases from Morgan Stanley xlsx/csv
        purchases = ms_parser.parse(args.input, args.out, ticker=args.ticker)

    if not purchases:
        print("No purchases parsed; aborting FAA3 conversion.")
        return

    # call itr converter; it will write fa_entries.csv under out/<ticker>/fa_entries.csv
    faa3_parser.parse(
        args.calendar_mode,
        purchases,
        args.assessment_year,
        args.out,
    )

    print("FAA3 conversion complete. Check the output folder for fa_entries.csv under the ticker folder.")


if __name__ == "__main__":
    main()
