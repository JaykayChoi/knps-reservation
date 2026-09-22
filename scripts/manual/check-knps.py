"""Opt-in live KNPS lookup. Run from the repository root."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

from config import load_environment
from providers.knps import fetch_reservations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('date', help='Target date in YYYYMMDD form')
    parser.add_argument('--park', action='append', default=[])
    parser.add_argument('--facility-type', action='append', default=[])
    args = parser.parse_args()
    load_environment()
    rows = fetch_reservations([args.date], args.facility_type, args.park)
    print(f'Available result count: {len(rows)}')
    for row in rows[:10]:
        print(row)


if __name__ == '__main__':
    main()
