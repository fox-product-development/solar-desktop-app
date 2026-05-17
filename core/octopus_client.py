# core/octopus_client.py
#
# Octopus Energy REST API client.
#
# Confirmed from live probe:
#   GET https://api.octopus.energy/v1/electricity-meter-points/{MPAN}/meters/{serial}/consumption/
#   Auth: Basic (API_KEY, "")
#   group_by=day returns one record per day
#   Works identically for import and export MPANs
#   Returns: {"results": [{"interval_start": "...", "consumption": float}, ...]}
#
# Both MPANs confirmed:
#   OCTOPUS_MPAN_EXPORT = "1050003758926"  — matches Sigenergy export figures
#   OCTOPUS_MPAN_IMPORT = "1012381556884"  — matches Sigenergy import figures

import logging
import datetime
import requests
import config

log = logging.getLogger(__name__)

BASE         = "https://api.octopus.energy/v1"
INSTALL_DATE = datetime.date(2026, 5, 7)

# Simple in-memory cache — keyed by (mpan, date_str)
# Refreshed at most once per session startup + once per day
_cache: dict = {}
_cache_date: datetime.date | None = None


def _configured() -> bool:
    return bool(
        getattr(config, "OCTOPUS_API_KEY",      "").strip() and
        getattr(config, "OCTOPUS_MPAN_EXPORT",  "").strip() and
        getattr(config, "OCTOPUS_MPAN_IMPORT",  "").strip() and
        getattr(config, "OCTOPUS_METER_SERIAL", "").strip()
    )


def _fetch_daily(mpan: str, since: datetime.date) -> list[dict]:
    """
    Fetch daily consumption from Octopus for a given MPAN since a date.
    Returns list of {"date": "YYYY-MM-DD", "kwh": float}.
    """
    period_from = since.isoformat() + "T00:00:00Z"
    url = f"{BASE}/electricity-meter-points/{mpan}/meters/{config.OCTOPUS_METER_SERIAL}/consumption/"

    results = []
    page_url = url

    while page_url:
        try:
            resp = requests.get(
                page_url,
                auth=(config.OCTOPUS_API_KEY, ""),
                params={
                    "period_from": period_from,
                    "group_by":    "day",
                    "order_by":    "period",
                    "page_size":   100,
                } if page_url == url else None,  # params only on first page
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for r in data.get("results", []):
                date_str = r["interval_start"][:10]
                results.append({
                    "date": date_str,
                    "kwh":  round(float(r["consumption"]), 3),
                })

            page_url = data.get("next")  # paginate if needed

        except Exception as exc:
            log.error("Octopus fetch failed (MPAN %s): %s", mpan, exc)
            break

    return results


def _refresh_cache():
    """Fetch import and export data and populate the cache."""
    global _cache, _cache_date

    log.info("Refreshing Octopus data cache...")
    since = INSTALL_DATE

    export_days = _fetch_daily(config.OCTOPUS_MPAN_EXPORT, since)
    import_days = _fetch_daily(config.OCTOPUS_MPAN_IMPORT, since)

    # Index by date for easy lookup
    export_by_date = {d["date"]: d["kwh"] for d in export_days}
    import_by_date = {d["date"]: d["kwh"] for d in import_days}

    all_dates = sorted(set(list(export_by_date) + list(import_by_date)))
    _cache = {
        date: {
            "export_kwh": export_by_date.get(date, 0.0),
            "import_kwh": import_by_date.get(date, 0.0),
        }
        for date in all_dates
    }
    _cache_date = datetime.date.today()
    log.info("Octopus cache refreshed: %d days of data.", len(_cache))


def get_daily_data(force_refresh: bool = False) -> dict:
    """
    Returns a dict keyed by "YYYY-MM-DD" with {"export_kwh", "import_kwh"}.
    Refreshes from API once per day or on first call.
    """
    global _cache_date

    if not _configured():
        log.warning("Octopus API not configured — skipping.")
        return {}

    today = datetime.date.today()
    if force_refresh or not _cache or _cache_date != today:
        _refresh_cache()

    return _cache


def backfill_from_octopus() -> int:
    """
    Fetch all Octopus import/export history and upsert into the data store.
    Uses Octopus as the authoritative source for export_kwh and import_kwh,
    overwriting Sigenergy estimates where Octopus data exists.
    Returns number of days written.
    """
    from core import data_store

    daily = get_daily_data(force_refresh=True)
    if not daily:
        return 0

    written = 0
    for date_str, values in daily.items():
        # Get existing generation figure from store (Sigenergy is authoritative for gen)
        store     = data_store.get_all()
        history   = store.get("daily_history", [])
        existing  = next((d for d in history if d["date"] == date_str), None)
        gen_kwh   = existing["generation_kwh"] if existing else 0.0

        data_store.update_daily(
            date_str=date_str,
            generation_kwh=gen_kwh,
            export_kwh=values["export_kwh"],
            import_kwh=values["import_kwh"],
        )
        written += 1

    log.info("Octopus backfill complete: %d days written.", written)
    return written


def get_today() -> dict:
    """
    Today's import/export from Octopus.
    Note: Octopus data is typically delayed by 1-2 days for smart meter reads,
    so today may return 0.0 — use Sigenergy for today's live figures.

    Returns {"export_kwh": float, "import_kwh": float}.
    """
    daily    = get_daily_data()
    today    = datetime.date.today().isoformat()
    return daily.get(today, {"export_kwh": 0.0, "import_kwh": 0.0})


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing Octopus client...\n")

    if not _configured():
        print("OCTOPUS_API_KEY / MPAN / SERIAL not set in config.py")
        raise SystemExit(1)

    daily = get_daily_data(force_refresh=True)
    if not daily:
        print("No data returned.")
    else:
        print(f"{'Date':<12} {'Export kWh':>12} {'Import kWh':>12}")
        print("-" * 38)
        for date_str in sorted(daily):
            d = daily[date_str]
            print(f"{date_str:<12} {d['export_kwh']:>12.3f} {d['import_kwh']:>12.3f}")

        total_export = sum(d["export_kwh"] for d in daily.values())
        total_import = sum(d["import_kwh"] for d in daily.values())
        seg_rate     = getattr(config, "OCTOPUS_SEG_RATE", 0.12)
        print(f"\n  Total export : {total_export:.3f} kWh  →  £{total_export * seg_rate:.2f}")
        print(f"  Total import : {total_import:.3f} kWh")