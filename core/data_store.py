# core/data_store.py
import json
import os
import logging
import datetime
import config

log = logging.getLogger(__name__)

def _load():
    if not os.path.exists(config.DATA_FILE):
        return _default()
    try:
        with open(config.DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in _default().items():
            data.setdefault(k, v)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        log.error("Could not read %s: %s", config.DATA_FILE, exc)
        return _default()

def _default():
    return {
        "cumulative_export_kwh":           0.0,
        "cumulative_export_earnings_gbp":  0.0,
        "best_hour_kwh":                   0.0,
        "install_cost_gbp":                None,
        "rates": [
            {
                "value":      0.12,
                "start_date": "2026-05-08",
                "end_date":   None
            }
        ],
        "daily_history": [],
    }

def _save(data):
    os.makedirs(os.path.dirname(config.DATA_FILE), exist_ok=True)
    try:
        with open(config.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as exc:
        log.error("Could not write %s: %s", config.DATA_FILE, exc)

def _rate_for_date(date_str, rates):
    """Return the export rate in £/kWh that was active on a given date."""
    for rate in reversed(rates):
        if date_str >= rate["start_date"]:
            if rate["end_date"] is None or date_str <= rate["end_date"]:
                return rate["value"]
    return 0.12  # fallback

def get_all():
    return _load()

def get_cumulative_earnings():
    return _load()["cumulative_export_earnings_gbp"]

def get_best_hour():
    return _load()["best_hour_kwh"]

def set_install_cost(cost_gbp):
    data = _load()
    data["install_cost_gbp"] = cost_gbp
    _save(data)

def update_best_hour(kwh):
    data = _load()
    if kwh > data["best_hour_kwh"]:
        data["best_hour_kwh"] = round(kwh, 3)
        _save(data)
        log.info("New best hour: %.3f kWh", kwh)

def add_rate(value, start_date, end_date=None):
    """Add a new export rate period."""
    data = _load()
    # Close off the current open rate
    for rate in data["rates"]:
        if rate["end_date"] is None:
            rate["end_date"] = start_date
    data["rates"].append({
        "value":      value,
        "start_date": start_date,
        "end_date":   end_date
    })
    _save(data)

def update_daily(date_str, generation_kwh, export_kwh, import_kwh):
    data    = _load()
    history = data["daily_history"]
    rate    = _rate_for_date(date_str, data["rates"])
    earnings = round(export_kwh * rate, 4)

    record = {
        "date":                date_str,
        "generation_kwh":      round(generation_kwh, 3),
        "export_kwh":          round(export_kwh, 3),
        "import_kwh":          round(import_kwh, 3),
        "export_earnings_gbp": earnings,
        "rate_gbp":            rate,
    }

    existing = next((d for d in history if d["date"] == date_str), None)
    if existing:
        existing.update(record)
    else:
        history.append(record)
        history.sort(key=lambda d: d["date"])

    # Recompute cumulative totals from scratch
    data["cumulative_export_kwh"] = round(
        sum(d["export_kwh"] for d in history), 3)
    data["cumulative_export_earnings_gbp"] = round(
        sum(d["export_earnings_gbp"] for d in history), 4)

    _save(data)

def get_last_n_days(n=7):
    return _load()["daily_history"][-n:]

def get_payoff_progress():
    data    = _load()
    earned  = data["cumulative_export_earnings_gbp"]
    cost    = data["install_cost_gbp"]
    if not cost:
        return {
            "install_cost_gbp": None,
            "earned_gbp":       earned,
            "remaining_gbp":    None,
            "percent_complete": 0.0,
        }
    remaining = max(0.0, cost - earned)
    pct       = min(100.0, (earned / cost) * 100)
    return {
        "install_cost_gbp": cost,
        "earned_gbp":       round(earned, 2),
        "remaining_gbp":    round(remaining, 2),
        "percent_complete": round(pct, 2),
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing data store...")

    update_daily("2026-05-07", generation_kwh=8.2,  export_kwh=5.1,  import_kwh=1.2)
    update_daily("2026-05-08", generation_kwh=14.3, export_kwh=9.8,  import_kwh=0.4)
    update_daily("2026-05-09", generation_kwh=10.1, export_kwh=6.2,  import_kwh=0.8)
    set_install_cost(6500.00)

    import json
    print(json.dumps(get_all(), indent=2))
    print("\nPayoff progress:", get_payoff_progress())