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
        "best_day_kwh":                    0.0,
        "best_day_date":                   None,
        "daily_history": [],
    }

def _save(data):
    os.makedirs(os.path.dirname(config.DATA_FILE), exist_ok=True)
    try:
        with open(config.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as exc:
        log.error("Could not write %s: %s", config.DATA_FILE, exc)

def _rate_for_date(date_str):
    if date_str < config.OCTOPUS_START_DATE:
        return 0.0
    return config.OCTOPUS_SEG_RATE

def get_all():
    return _load()

def get_cumulative_earnings():
    return _load()["cumulative_export_earnings_gbp"]

def get_best_hour():
    return _load()["best_hour_kwh"]

def update_best_hour(kwh):
    data = _load()
    if kwh > data["best_hour_kwh"]:
        data["best_hour_kwh"] = round(kwh, 3)
        _save(data)
        log.info("New best hour: %.3f kWh", kwh)

def update_daily(date_str, generation_kwh, export_kwh, import_kwh):
    data    = _load()
    history = data["daily_history"]
    rate    = _rate_for_date(date_str)
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

    if generation_kwh > data["best_day_kwh"]:
        data["best_day_kwh"]  = round(generation_kwh, 3)
        data["best_day_date"] = date_str
        log.info("New best day: %.3f kWh on %s", generation_kwh, date_str)

    _save(data)

def get_last_n_days(n=7):
    return _load()["daily_history"][-n:]

def get_payoff_progress():
    """
    Full payoff status: earned-to-date, remaining, percent complete,
    time-remaining estimate, and average daily contributions.
    install cost and key dates come from config.py (static, never from JSON).
    """
    cost = getattr(config, "INSTALL_COST_GBP", None)
    if not cost:
        return {
            "install_cost_gbp":       None,
            "earned_gbp":             0.0,
            "remaining_gbp":          None,
            "percent_complete":       0.0,
            "countdown_text":         "--",
            "avg_daily_export_earn":  0.0,
            "avg_daily_import_saved": 0.0,
        }

    data    = _load()
    history = data["daily_history"]

    seg_rate     = config.OCTOPUS_SEG_RATE
    imp_rate     = config.OCTOPUS_IMPORT_RATE
    install_date = config.INSTALL_DATE
    seg_date     = config.OCTOPUS_START_DATE

    # Export earnings: only from SEG start date
    total_export_earn = sum(
        d["export_kwh"] * seg_rate
        for d in history if d["date"] >= seg_date
    )

    # Import savings: self-used generation (gen - export) from install date
    total_import_saved = sum(
        max(0.0, d["generation_kwh"] - d["export_kwh"]) * imp_rate
        for d in history if d["date"] >= install_date
    )

    total_earn = round(total_export_earn + total_import_saved, 2)
    remaining  = max(0.0, cost - total_earn)
    pct        = min(100.0, (total_earn / cost) * 100)

    install_date_obj = datetime.date.fromisoformat(install_date)
    seg_date_obj      = datetime.date.fromisoformat(seg_date)
    today             = datetime.date.today()
    days_since_seg     = max(1, (today - seg_date_obj).days + 1)
    days_since_install = max(1, (today - install_date_obj).days + 1)

    avg_daily_export_earn  = total_export_earn  / days_since_seg
    avg_daily_import_saved = total_import_saved / days_since_install
    avg_daily_total        = avg_daily_export_earn + avg_daily_import_saved

    if avg_daily_total > 0 and remaining > 0:
        days_left = remaining / avg_daily_total
        years     = int(days_left // 365)
        months    = int((days_left % 365) // 30)
        days_left_part = int(days_left % 30)
        parts = []
        if years:  parts.append(f"{years}y")
        if months: parts.append(f"{months}m")
        if days_left_part or not parts: parts.append(f"{days_left_part}d")
        countdown_text = " ".join(parts)
    elif remaining <= 0:
        countdown_text = "Paid off! 🎉"
    else:
        countdown_text = "--"

    return {
        "install_cost_gbp":       cost,
        "earned_gbp":             total_earn,
        "remaining_gbp":          round(remaining, 2),
        "percent_complete":       round(pct, 2),
        "countdown_text":         countdown_text,
        "avg_daily_export_earn":  round(avg_daily_export_earn, 2),
        "avg_daily_import_saved": round(avg_daily_import_saved, 2),
    }

def get_seven_day_averages():
    """Average generation/export/earnings/import-saving over the last 7 days."""
    data    = _load()
    last7   = data["daily_history"][-7:]

    if not last7:
        return {
            "avg_gen":          0.0,
            "avg_export":       0.0,
            "avg_export_earn":  0.0,
            "avg_import_saved": 0.0,
        }

    avg_gen       = sum(d["generation_kwh"] for d in last7) / 7
    avg_exp       = sum(d["export_kwh"] for d in last7) / 7
    avg_earn      = avg_exp * config.OCTOPUS_SEG_RATE
    avg_self_used = sum(max(0.0, d["generation_kwh"] - d["export_kwh"]) for d in last7) / 7
    avg_imp_save  = avg_self_used * config.OCTOPUS_IMPORT_RATE

    return {
        "avg_gen":          round(avg_gen, 2),
        "avg_export":       round(avg_exp, 2),
        "avg_export_earn":  round(avg_earn, 2),
        "avg_import_saved": round(avg_imp_save, 2),
    }

def recalculate_best_day():
    """One-time backfill: find the best day from existing history and save it."""
    data    = _load()
    history = data["daily_history"]
    if history:
        best = max(history, key=lambda d: d["generation_kwh"])
        data["best_day_kwh"]  = round(best["generation_kwh"], 3)
        data["best_day_date"] = best["date"]
        _save(data)
        log.info("Backfilled best day: %.3f kWh on %s",
                 data["best_day_kwh"], data["best_day_date"])

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

    SEG_START = config.OCTOPUS_START_DATE
    return {
        "generation_kwh": round(sum(d["generation_kwh"] for d in days), 2),
        "export_kwh":     round(sum(d["export_kwh"] for d in days if d["date"] >= SEG_START), 2),
        "import_kwh":     round(sum(d["import_kwh"] for d in days), 2),
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