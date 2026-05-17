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
    for rate in reversed(rates):
        if date_str >= rate["start_date"]:
            if rate["end_date"] is None or date_str <= rate["end_date"]:
                return rate["value"]
    return 0.12

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
    data = _load()
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

def get_period_totals(period="day", reference_date=None):
    if reference_date is None:
        reference_date = datetime.date.today()

    data    = _load()
    history = data["daily_history"]

    if period == "day":
        date_str = reference_date.isoformat()
        days = [d for d in history if d["date"] == date_str]

    elif period == "week":
        monday = reference_date - datetime.timedelta(days=reference_date.weekday())
        sunday = monday + datetime.timedelta(days=6)
        days = [d for d in history
                if monday.isoformat() <= d["date"] <= sunday.isoformat()]

    elif period == "month":
        month_str = reference_date.strftime("%Y-%m")
        days = [d for d in history if d["date"].startswith(month_str)]

    elif period == "year":
        year_str = str(reference_date.year)
        days = [d for d in history if d["date"].startswith(year_str)]

    else:  # lifetime
        days = history

    SEG_START = "2026-05-15"
    return {
        "generation_kwh": round(sum(d["generation_kwh"] for d in days), 2),
        "export_kwh":     round(sum(d["export_kwh"] for d in days if d["date"] >= SEG_START), 2),
        "earnings_gbp":   round(sum(d["export_earnings_gbp"] for d in days if d["date"] >= SEG_START), 2),
        "days":           len(days),
    }

def get_period_label(period, reference_date=None):
    if reference_date is None:
        reference_date = datetime.date.today()

    if period == "year":
        return str(reference_date.year)
    elif period == "month":
        return reference_date.strftime("%B %Y")
    elif period == "week":
        monday = reference_date - datetime.timedelta(days=reference_date.weekday())
        sunday = monday + datetime.timedelta(days=6)
        return f"{monday.day}–{sunday.day} {sunday.strftime('%b')}"
    else:
        return "All time"