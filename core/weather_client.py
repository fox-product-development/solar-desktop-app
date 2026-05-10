# core/weather_client.py
import urllib.request
import json
import logging
import config

log = logging.getLogger(__name__)

# WMO weather code mappings
WMO_CODES = {
    0:  ("Clear sky",       "☀️"),
    1:  ("Mainly clear",    "🌤️"),
    2:  ("Partly cloudy",   "⛅"),
    3:  ("Overcast",        "☁️"),
    45: ("Foggy",           "🌫️"),
    48: ("Icy fog",         "🌫️"),
    51: ("Light drizzle",   "🌦️"),
    53: ("Drizzle",         "🌦️"),
    55: ("Heavy drizzle",   "🌧️"),
    61: ("Light rain",      "🌧️"),
    63: ("Rain",            "🌧️"),
    65: ("Heavy rain",      "🌧️"),
    71: ("Light snow",      "🌨️"),
    73: ("Snow",            "❄️"),
    75: ("Heavy snow",      "❄️"),
    80: ("Light showers",   "🌦️"),
    81: ("Showers",         "🌧️"),
    82: ("Heavy showers",   "🌧️"),
    95: ("Thunderstorm",    "⛈️"),
    96: ("Thunderstorm",    "⛈️"),
    99: ("Thunderstorm",    "⛈️"),
}

# System constants
PEAK_KW       = 3.09   # System peak output
EFFICIENCY    = 0.80   # Real-world efficiency factor

WEATHER_URL = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={config.LATITUDE}&longitude={config.LONGITUDE}"
    f"&current=temperature_2m,weather_code,wind_speed_10m"
    f"&hourly=shortwave_radiation,weather_code"
    f"&daily=weather_code,temperature_2m_max,temperature_2m_min"
    f"&forecast_days=3&timezone=Europe%2FLondon"
)


def _estimate_kwh(radiation_wm2):
    """Convert shortwave radiation W/m² to estimated kWh generation for that hour."""
    return round((radiation_wm2 / 1000) * PEAK_KW * EFFICIENCY, 2)


def get_weather():
    """
    Fetch weather and return structured data.

    Keys:
      temperature       – current temp °C
      description       – human readable condition
      emoji             – weather emoji
      wind_kph          – wind speed km/h
      forecast          – list of 3 daily dicts
      hourly_kwh        – list of 24 estimated kWh values for today (hours 0-23)
      error             – None or error string
    """
    try:
        with urllib.request.urlopen(WEATHER_URL, timeout=10) as resp:
            data = json.loads(resp.read())

        cur  = data["current"]
        day  = data["daily"]
        hr   = data["hourly"]
        code = int(cur["weather_code"])
        desc, emoji = WMO_CODES.get(code, ("Unknown", "🌡️"))

        # --- Hourly kWh estimates for today (first 24 hours) ---
        today_radiation = hr["shortwave_radiation"][:24]
        hourly_kwh = [_estimate_kwh(r) for r in today_radiation]

        # --- Daily total kWh estimates (sum of hourly for each day) ---
        forecast = []
        for i in range(3):
            day_code = int(day["weather_code"][i])
            day_desc, day_emoji = WMO_CODES.get(day_code, ("Unknown", "🌡️"))

            # Each day is 24 hours starting at offset i*24
            start = i * 24
            end   = start + 24
            day_radiation = hr["shortwave_radiation"][start:end]
            day_kwh = round(sum(_estimate_kwh(r) for r in day_radiation), 1)

            # Peak hour for this day
            if day_radiation:
                peak_hour = day_radiation.index(max(day_radiation))
                peak_kwh  = _estimate_kwh(max(day_radiation))
            else:
                peak_hour = 13
                peak_kwh  = 0.0

            forecast.append({
                "date":        day["time"][i],
                "description": day_desc,
                "emoji":       day_emoji,
                "temp_max":    day["temperature_2m_max"][i],
                "temp_min":    day["temperature_2m_min"][i],
                "day_kwh":     day_kwh,
                "peak_hour":   peak_hour,
                "peak_kwh":    peak_kwh,
                "hourly_kwh":  [_estimate_kwh(r) for r in day_radiation],
            })

        return {
            "temperature":  cur["temperature_2m"],
            "description":  desc,
            "emoji":        emoji,
            "wind_kph":     cur["wind_speed_10m"],
            "forecast":     forecast,
            "hourly_kwh":   hourly_kwh,
            "error":        None,
        }

    except Exception as exc:
        log.error("Weather fetch failed: %s", exc)
        return {
            "temperature":  None,
            "description":  "Unavailable",
            "emoji":        "❓",
            "wind_kph":     None,
            "forecast":     [],
            "hourly_kwh":   [0.0] * 24,
            "error":        str(exc),
        }


if __name__ == "__main__":
    import pprint
    logging.basicConfig(level=logging.INFO)
    print("Testing weather client...")
    w = get_weather()
    if w["error"]:
        print(f"FAILED: {w['error']}")
    else:
        print(f"Current: {w['emoji']} {w['description']} {w['temperature']}°C")
        print(f"\nToday's hourly generation forecast:")
        for hour, kwh in enumerate(w["hourly_kwh"]):
            if kwh > 0:
                print(f"  {hour:02d}:00  {kwh:.2f} kWh")
        print(f"\n3-day forecast:")
        for day in w["forecast"]:
            print(f"  {day['date']} {day['emoji']} {day['description']} "
                  f"~{day['day_kwh']} kWh total, "
                  f"peak {day['peak_kwh']} kWh at {day['peak_hour']:02d}:00")