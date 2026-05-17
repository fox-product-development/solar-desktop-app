# main.py
import threading
import logging
import datetime
import config
from core import sigen_client, sigen_dev_client, weather_client, data_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def _dev_api_configured() -> bool:
    return bool(
        getattr(config, "SIGEN_APP_KEY",    "").strip() and
        getattr(config, "SIGEN_APP_SECRET", "").strip() and
        getattr(config, "SIGEN_SYSTEM_ID",  "").strip()
    )


class DataRefresher:

    def __init__(self):
        self.live    = None
        self.weather = None
        self.store   = data_store.get_all()
        self._lock   = threading.Lock()
        self._stop   = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

        if _dev_api_configured():
            # Backfill runs once at startup in a background thread so the UI
            # isn't blocked. Populates daily_history with real API figures and
            # sets best_day correctly from the full history.
            threading.Thread(target=self._backfill, daemon=True).start()
        else:
            log.warning("Dev API credentials not set — backfill and today stats unavailable.")

    def start(self):
        log.info("DataRefresher starting...")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def refresh_now(self):
        self._refresh()

    def _backfill(self):
        log.info("Starting historical backfill...")
        try:
            written = sigen_dev_client.backfill_history()
            log.info("Backfill wrote %d records.", written)
            data_store.repair_best_day()
            with self._lock:
                self.store = data_store.get_all()
        except Exception as exc:
            log.error("Backfill failed: %s", exc)

    def _loop(self):
        self._stop.wait(config.REFRESH_SECONDS)
        while not self._stop.is_set():
            self._refresh()
            self._stop.wait(config.REFRESH_SECONDS)

    def _refresh(self):
        log.info("Refreshing data...")

        # 1. Live data — instantaneous kW readings
        live = sigen_client.get_live_data()
        if live:
            with self._lock:
                self.live = live
            log.info(
                "Live: %.2fkW gen / %.2fkW load / %.2fkW %s",
                live["pv_power_kw"],
                live["load_power_kw"],
                abs(live["grid_power_kw"]),
                "exporting" if live["is_exporting"] else "importing",
            )

        # 2. Today's accurate running totals from the dev API (sums 5-min intervals)
        today_stats = None
        if _dev_api_configured():
            today_stats = sigen_dev_client.get_today_stats()
            if today_stats:
                log.info(
                    "Today: gen=%.2fkWh  export=%.2fkWh  import=%.2fkWh",
                    today_stats["generation_kwh"],
                    today_stats["export_kwh"],
                    today_stats["import_kwh"],
                )

        # 3. Weather
        weather = weather_client.get_weather()
        if not weather["error"]:
            with self._lock:
                self.weather = weather
            log.info("Weather: %s %s %.1f°C",
                     weather["emoji"], weather["description"], weather["temperature"])

        # 4. Update today's record in the data store.
        #    Use dev API totals when available; fall back to live pvDayNrg
        #    for generation and 0 for export/import (backfill corrects history).
        if live:
            today      = datetime.date.today().isoformat()
            gen_kwh    = today_stats["generation_kwh"] if today_stats else live["pv_day_kwh"]
            export_kwh = today_stats["export_kwh"]     if today_stats else 0.0
            import_kwh = today_stats["import_kwh"]     if today_stats else 0.0

            data_store.update_daily(
                date_str=today,
                generation_kwh=gen_kwh,
                export_kwh=export_kwh,
                import_kwh=import_kwh,
            )
            with self._lock:
                self.store = data_store.get_all()

        log.info("Refresh complete.")

    def snapshot(self):
        with self._lock:
            store = dict(self.store)
            return {
                "live":    self.live,
                "weather": self.weather,
                "store":   store,
                "best_day": {
                    "kwh":  store.get("best_day_kwh",  0.0),
                    "date": store.get("best_day_date", None),
                },
            }


def main():
    log.info("Solar Monitor starting...")

    refresher = DataRefresher()

    log.info("Performing initial data fetch...")
    refresher.refresh_now()
    refresher.start()

    from ui.widget import SolarWidget
    app = SolarWidget(refresher)
    app.mainloop()

    refresher.stop()


if __name__ == "__main__":
    main()