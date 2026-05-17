# core/sigen_dev_client.py
#
# Sigenergy Developer API client (key-based auth).
#
# Confirmed working endpoints:
#   POST openapi/auth/login/key          — authentication (data field is double-JSON)
#   POST openapi/board/onboard           — register app (code 1116 = partial, still works)
#   GET  openapi/systems/{id}/history    — history at Day/Month/Year/Lifetime level
#
# Confirmed field names from live API responses:
#   Month-level items: powerGeneration, powerToGrid, powerFromGrid
#   Day-level items:   pvTotalPower, toGridPower, fromGridPower
#   Day-level summary: always zero — must sum items instead
#   dataTime format:   "20260507 00:00" — first 8 chars are YYYYMMDD

import base64
import json
import logging
import time
import datetime
import requests
import config

log = logging.getLogger(__name__)

REGION_URLS = {
    "eu": "https://api-eu.sigencloud.com",
    "cn": "https://api.sigencloud.com",
}

TOKEN_REFRESH_BUFFER_S = 600

_token: str | None       = None
_token_expires_at: float = 0.0


# ── Auth ──────────────────────────────────────────────────────────────────────

def _base_url() -> str:
    return REGION_URLS.get(config.SIGEN_REGION, REGION_URLS["eu"])


def _get_token() -> str | None:
    global _token, _token_expires_at

    if _token and time.time() < _token_expires_at - TOKEN_REFRESH_BUFFER_S:
        return _token

    raw_key = f"{config.SIGEN_APP_KEY}:{config.SIGEN_APP_SECRET}"
    b64_key = base64.b64encode(raw_key.encode()).decode()

    try:
        resp = requests.post(
            f"{_base_url()}/openapi/auth/login/key",
            json={"key": b64_key},
            timeout=15,
        )
        resp.raise_for_status()
        outer = resp.json()

        if outer.get("code") != 0:
            log.error("Dev auth failed: code=%s msg=%s", outer.get("code"), outer.get("msg"))
            return None

        # data field is a JSON string — must be parsed twice
        inner             = json.loads(outer["data"])
        _token            = inner["accessToken"]
        expires_in        = int(inner.get("expiresIn", 43199))
        _token_expires_at = time.time() + expires_in
        log.info("Dev token obtained, expires in %ds", expires_in)
        return _token

    except Exception as exc:
        log.error("Dev auth error: %s", exc)
        return None


def _headers() -> dict | None:
    token = _get_token()
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "sigen-region":  config.SIGEN_REGION,
        "Content-Type":  "application/json",
    }


# ── Onboard ───────────────────────────────────────────────────────────────────

def onboard() -> bool:
    """
    Register this app against the system.
    Code 1116 = partial access — data endpoints still work, treated as success.
    Non-fatal if it fails — callers should continue regardless.
    """
    headers = _headers()
    if not headers:
        return False
    try:
        resp = requests.post(
            f"{_base_url()}/openapi/board/onboard",
            headers=headers,
            json=[config.SIGEN_SYSTEM_ID],
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()

        if body.get("code") != 0:
            log.warning("Onboard: code=%s msg=%s", body.get("code"), body.get("msg"))
            return False

        for r in body.get("data", []):
            codes = r.get("codeList", [])
            if r.get("result") or 1303 in codes or 1116 in codes:
                log.info("Onboard OK for %s (codes=%s)", r.get("systemId"), codes)
                return True
            log.warning("Onboard rejected for %s: codes=%s", r.get("systemId"), codes)
            return False

        return True

    except Exception as exc:
        log.warning("Onboard error: %s", exc)
        return False


# ── Internal history fetch ────────────────────────────────────────────────────

def _get_history(level: str, date: datetime.date) -> dict | None:
    """
    GET openapi/systems/{id}/history

    level: "Day" | "Month" | "Year" | "Lifetime"
    date:  reference date

    Returns {"summary": {...}, "items": [...]} or None on failure.
    Handles the double-JSON data field automatically.
    """
    headers = _headers()
    if not headers:
        return None

    try:
        resp = requests.get(
            f"{_base_url()}/openapi/systems/{config.SIGEN_SYSTEM_ID}/history",
            headers=headers,
            params={"level": level, "date": date.strftime("%Y-%m-%d")},
            timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()

        if body.get("code") != 0:
            log.error("_get_history(%s %s): code=%s msg=%s",
                      level, date, body.get("code"), body.get("msg"))
            return None

        raw = body.get("data", {})
        d   = json.loads(raw) if isinstance(raw, str) else raw

        return {
            "summary": {
                "powerGeneration": float(d.get("powerGeneration", 0.0)),
                "powerToGrid":     float(d.get("powerToGrid",     0.0)),
                "powerFromGrid":   float(d.get("powerFromGrid",   0.0)),
            },
            "items": d.get("itemList", []),
        }

    except Exception as exc:
        log.error("_get_history(%s %s) failed: %s", level, date, exc)
        return None


# ── Public functions ──────────────────────────────────────────────────────────

def get_today_stats() -> dict | None:
    """
    Today's generation/export/import totals (kWh).

    Uses the Month-level breakdown which gives accurate per-day totals.
    The Day-level items are cumulative running totals — summing them is wrong.

    Returns {"generation_kwh", "export_kwh", "import_kwh"} or None.
    """
    today = datetime.date.today().isoformat()
    days  = get_month_daily_breakdown(datetime.date.today())
    match = next((d for d in days if d["date"] == today), None)
    return match  # None if today not yet in response


_month_cache: dict = {}  # {month_str: {"fetched_at": float, "days": list}}
MONTH_CACHE_TTL_S = 300  # 5 minutes


def get_month_daily_breakdown(target_date: datetime.date) -> list[dict]:
    """
    Per-day records for the month containing target_date.
    Cached for 5 minutes to respect API rate limits.

    Confirmed item field names: powerGeneration, powerToGrid, powerFromGrid.
    dataTime format: "20260507 00:00" — first 8 chars parsed as YYYYMMDD.

    Returns list of {"date", "generation_kwh", "export_kwh", "import_kwh"}.
    """
    month_str = target_date.strftime("%Y-%m")
    cached    = _month_cache.get(month_str)
    if cached and time.time() - cached["fetched_at"] < MONTH_CACHE_TTL_S:
        return cached["days"]

    result = _get_history("Month", target_date)
    if not result:
        return []

    days = []
    for item in result["items"]:
        raw_dt = (item.get("dataTime") or "").strip()
        if len(raw_dt) < 8:
            continue
        try:
            date_str = datetime.datetime.strptime(raw_dt[:8], "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            continue

        days.append({
            "date":           date_str,
            "generation_kwh": round(float(item.get("powerGeneration", 0.0)), 3),
            "export_kwh":     round(float(item.get("powerToGrid",     0.0)), 3),
            "import_kwh":     round(float(item.get("powerFromGrid",   0.0)), 3),
        })

    _month_cache[month_str] = {"fetched_at": time.time(), "days": days}
    return days


def backfill_history(since_date: datetime.date | None = None) -> int:
    """
    Pull per-day history and upsert into the local data store.
    Walks month-by-month from since_date (default: install date) to today.
    Returns number of day records written.
    """
    from core import data_store

    onboard()  # non-fatal if it fails

    install_date = datetime.date(2026, 5, 7)
    if since_date is None:
        since_date = install_date

    today   = datetime.date.today()
    written = 0
    cursor  = since_date.replace(day=1)

    while cursor <= today:
        log.info("Backfilling %d-%02d...", cursor.year, cursor.month)
        days = get_month_daily_breakdown(cursor)

        for day in days:
            if day["date"] < install_date.isoformat():
                continue
            if day["date"] > today.isoformat():
                continue
            data_store.update_daily(
                date_str=day["date"],
                generation_kwh=day["generation_kwh"],
                export_kwh=day["export_kwh"],
                import_kwh=day["import_kwh"],
            )
            written += 1

        # Advance to first of next month
        cursor = (cursor.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

    log.info("Backfill complete: %d records written.", written)
    return written


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing Sigenergy developer client...\n")

    print("── Onboard ──")
    print(f"  {'OK' if onboard() else 'FAILED — continuing anyway'}")

    print("\n── Today's stats ──")
    today = get_today_stats()
    if today:
        print(f"  Generation : {today['generation_kwh']:.2f} kWh")
        print(f"  Export     : {today['export_kwh']:.2f} kWh")
        print(f"  Import     : {today['import_kwh']:.2f} kWh")
    else:
        print("  FAILED")

    print("\n── Month breakdown (May 2026) ──")
    days = get_month_daily_breakdown(datetime.date(2026, 5, 1))
    if days:
        for d in days:
            print(f"  {d['date']}  gen={d['generation_kwh']:.2f}  "
                  f"export={d['export_kwh']:.2f}  import={d['import_kwh']:.2f}")
        best = max(days, key=lambda x: x["generation_kwh"])
        print(f"\n  Best day: {best['date']} — {best['generation_kwh']:.2f} kWh")
    else:
        print("  FAILED")