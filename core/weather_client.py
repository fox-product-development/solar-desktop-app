# core/weather_client.py
import urllib.request
import json
import logging
import config

log = logging.getLogger(__name__)

# WMO weather code mappings — icon is the PNG filename in assets/icons/weather/
WMO_CODES = {
    0:  ("Clear sky",       "clear"),
    1:  ("Mainly clear",    "mainly_clear"),
    2:  ("Partly cloudy",   "partly_cloudy"),
    3:  ("Overcast",        "overcast"),
    45: ("Foggy",           "foggy"),
    48: ("Icy fog",         "foggy"),
    51: ("Light drizzle",   "drizzle"),
    53: ("Drizzle",         "drizzle"),
    55: ("Heavy drizzle",   "rain"),
    61: ("Light rain",      "drizzle"),
    63: ("Rain",            "rain"),
    65: ("Heavy rain",      "rain"),
    71: ("Light snow",      "snow"),
    73: ("Snow",            "snow"),
    75: ("Heavy snow",      "heavy_snow"),
    80: ("Light showers",   "showers"),
    81: ("Showers",         "showers"),
    82: ("Heavy showers",   "heavy_showers"),
    95: ("Thunderstorm",    "thunderstorm"),
    96: ("Thunderstorm",    "thunderstorm"),
    99: ("Thunderstorm",    "thunderstorm"),
}

PEAK_KW    = 3.09
EFFICIENCY = 0.80

WEATHER_URL = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={config.LATITUDE}&longitude={config.LONGITUDE}"
    f"&current=temperature_2m,weather_code,wind_speed_10m"
    f"&hourly=shortwave_radiation,weather_code"
    f"&daily=weather_code,temperature_2m_max,temperature_2m_min"
    f"&forecast_days=3&timezone=Europe%2FLondon"
)


def _estimate_kwh(radiation_wm2):
    return round((radiation_wm2 / 1000) * PEAK_KW * EFFICIENCY, 2)


def get_weather():
    try:
        with urllib.request.urlopen(WEATHER_URL, timeout=10) as resp:
            data = json.loads(resp.read())

        cur  = data["current"]
        day  = data["daily"]
        hr   = data["hourly"]
        code = int(cur["weather_code"])
        desc, icon = WMO_CODES.get(code, ("Unknown", "unknown"))

        today_radiation = hr["shortwave_radiation"][:24]
        hourly_kwh = [_estimate_kwh(r) for r in today_radiation]

        forecast = []
        for i in range(3):
            day_code = int(day["weather_code"][i])
            day_desc, day_icon = WMO_CODES.get(day_code, ("Unknown", "unknown"))

            start = i * 24
            end   = start + 24
            day_radiation = hr["shortwave_radiation"][start:end]
            day_kwh = round(sum(_estimate_kwh(r) for r in day_radiation), 1)

            if day_radiation:
                peak_hour = day_radiation.index(max(day_radiation))
                peak_kwh  = _estimate_kwh(max(day_radiation))
            else:
                peak_hour = 13
                peak_kwh  = 0.0

            forecast.append({
                "date":        day["time"][i],
                "description": day_desc,
                "icon":        day_icon,
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
            "icon":         icon,
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
            "icon":         "unknown",
            "wind_kph":     None,
            "forecast":     [],
            "hourly_kwh":   [0.0] * 24,
            "error":        str(exc),
        }