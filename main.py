# main.py
import threading
import logging
import time
import datetime
import config
from core import sigen_client, weather_client, data_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


class DataRefresher:
    """
    Runs a background thread that polls all data sources every
    REFRESH_SECONDS and stores results as simple attributes.
    The UI reads from these via a thread-safe snapshot() call.
    """

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
        """Blocking first fetch — call before starting the UI."""
        self._refresh()

    def _loop(self):
        self._stop.wait(config.REFRESH_SECONDS)  # wait first
        while not self._stop.is_set():
            self._refresh()
            self._stop.wait(config.REFRESH_SECONDS)

    def _refresh(self):
        log.info("Refreshing data...")

        # --- Sigen live data ---
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

        # --- Weather ---
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

        # --- Persist today's running totals ---
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
        """Return a thread-safe copy of all current data for the UI."""
        with self._lock:
            return {
                "live":    self.live,
                "weather": self.weather,
                "store":   dict(self.store),
            }


def main():
    log.info("Solar Monitor starting...")

    refresher = DataRefresher()

    # Blocking first fetch so UI has data immediately on launch
    log.info("Performing initial data fetch...")
    refresher.refresh_now()

    # Start background polling
    refresher.start()

    # --- Temporary console output until UI is built ---
    try:
        while True:
            snap = refresher.snapshot()
            live    = snap["live"]
            weather = snap["weather"]
            store   = snap["store"]

            print("\n" + "="*50)
            print(f"  {datetime.datetime.now().strftime('%H:%M:%S %d %b %Y')}")
            print("="*50)

            if weather:
                print(f"  {weather['emoji']}  {weather['description']}  "
                      f"{weather['temperature']}°C  "
                      f"wind {weather['wind_kph']} km/h")

            if live:
                print(f"\n  Generation : {live['pv_power_kw']} kW")
                print(f"  Load       : {live['load_power_kw']} kW "
                      f"({live['load_satisfied_pct']}% from solar)")
                print(f"  Grid       : {abs(live['grid_power_kw'])} kW "
                      f"({'exporting' if live['is_exporting'] else 'importing'})")
                print(f"  Today      : {live['pv_day_kwh']} kWh")

            payoff = data_store.get_payoff_progress()
            print(f"\n  Cumulative earnings : "
                  f"£{store['cumulative_export_earnings_gbp']:.2f}")
            if payoff["install_cost_gbp"]:
                print(f"  Payoff progress     : "
                      f"{payoff['percent_complete']}%")

            time.sleep(config.REFRESH_SECONDS)

    except KeyboardInterrupt:
        log.info("Shutting down.")
        refresher.stop()


if __name__ == "__main__":
    main()