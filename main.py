# main.py
import threading
import logging
import datetime
import config
from core import sigen_client, weather_client, data_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


class DataRefresher:

    def __init__(self):
        self.live    = None
        self.weather = None
        self.store   = data_store.get_all()
        self._lock   = threading.Lock()
        self._stop   = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        log.info("DataRefresher starting...")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def refresh_now(self):
        self._refresh()

    def _loop(self):
        self._stop.wait(config.REFRESH_SECONDS)
        while not self._stop.is_set():
            self._refresh()
            self._stop.wait(config.REFRESH_SECONDS)

    def _refresh(self):
        log.info("Refreshing data...")

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

        weather = weather_client.get_weather()
        if not weather["error"]:
            with self._lock:
                self.weather = weather
            log.info(
                "Weather: %s %s %.1f°C",
                weather["emoji"],
                weather["description"],
                weather["temperature"],
            )

        if live:
            today = datetime.date.today().isoformat()
            data_store.update_daily(
                date_str=today,
                generation_kwh=live["pv_day_kwh"],
                export_kwh=max(0.0, live["grid_power_kw"]),
                import_kwh=max(0.0, -live["grid_power_kw"]),
            )
            with self._lock:
                self.store = data_store.get_all()

        log.info("Refresh complete.")

    def snapshot(self):
        with self._lock:
            return {
                "live":    self.live,
                "weather": self.weather,
                "store":   dict(self.store),
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