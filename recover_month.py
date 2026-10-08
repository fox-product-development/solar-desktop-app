# recover_month.py
#
# Manual recovery tool — pulls one calendar month of per-day history from the
# Sigenergy Developer API and writes it into the local data store.
#
# Usage (run from the project folder, with the app closed):
#   python recover_month.py 2026-07
#
# Makes one month request per run. Keep runs 15 minutes apart.

import sys
import logging
import datetime
import config
from core import sigen_dev_client, data_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def _parse_month(arg: str) -> datetime.date | None:
    try:
        return datetime.datetime.strptime(arg, "%Y-%m").date()
    except ValueError:
        return None


def main():
    if len(sys.argv) != 2:
        print("Usage: python recover_month.py YYYY-MM")
        return

    month_date = _parse_month(sys.argv[1])
    if not month_date:
        print(f"Invalid month '{sys.argv[1]}' — use YYYY-MM, e.g. 2026-07")
        return

    month_str = month_date.strftime("%Y-%m")
    today     = datetime.date.today().isoformat()

    print(f"Requesting {month_str} from Sigenergy...")
    days = sigen_dev_client.get_month_daily_breakdown(month_date)
    days = [d for d in days if config.INSTALL_DATE <= d["date"] <= today]

    if not days:
        print("No days returned — check the log above for errors (e.g. code 1201). Nothing written.")
        return

    print(f"\n{'Date':<12}{'Gen kWh':>10}{'Export':>10}{'Import':>10}")
    for d in days:
        print(f"{d['date']:<12}{d['generation_kwh']:>10.2f}"
              f"{d['export_kwh']:>10.2f}{d['import_kwh']:>10.2f}")

    total_gen = sum(d["generation_kwh"] for d in days)
    total_exp = sum(d["export_kwh"]     for d in days)
    total_imp = sum(d["import_kwh"]     for d in days)
    print(f"{'Total':<12}{total_gen:>10.2f}{total_exp:>10.2f}{total_imp:>10.2f}\n")

    answer = input(f"Write {len(days)} days to {config.DATA_FILE}? (y/n): ")
    if answer.strip().lower() != "y":
        print("Cancelled. Nothing written.")
        return

    for d in days:
        data_store.update_daily(
            date_str=d["date"],
            generation_kwh=d["generation_kwh"],
            export_kwh=d["export_kwh"],
            import_kwh=d["import_kwh"],
        )

    print(f"Done — {len(days)} days written for {month_str}.")


if __name__ == "__main__":
    main()