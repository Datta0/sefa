#!/usr/bin/env python3
"""CLI to parse Morgan Stanley RSU/benefit history files.

Usage:
    python scripts/run_morgan_parser.py --input /path/to/file.xlsx --out output/dir [--ticker goog]
"""
import argparse
import os
import sys
import json

# Ensure project root is on sys.path so `from parser...` works when running the script
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

from parser.demat.morgan_stanley import morgan_stanley_rsu_parser as parser
from utils import file_utils


def purchase_to_dict(p):
    return {
        "ticker": p.ticker,
        "quantity": p.quantity,
        "date": p.date,
        "purchase_fmv": {"price": p.purchase_fmv.price, "currency": p.purchase_fmv.currency_code},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input xlsx/csv file")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--ticker", required=False, help="Ticker to use if the sheet lacks a Symbol column")
    args = ap.parse_args()

    purchases = parser.parse(args.input, args.out, ticker=(args.ticker.lower() if args.ticker else None))

    # write JSON output
    file_utils.write_to_file(args.out, "purchases.json", purchases, override=True, print_path_to_console=True)
    print(json.dumps([purchase_to_dict(p) for p in purchases], indent=2))


if __name__ == "__main__":
    main()
