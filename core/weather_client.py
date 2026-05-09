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

WEATHER_URL = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={config.LATITUDE}&longitude={config.LONGITUDE}"
    f"&current=temperature_2m,weather_code,wind_speed_10m"
    f"&daily=weather_code,temperature_2m_max,temperature_2m_min,"
    f"sunshine_duration"
    f"&forecast_days=3&timezone=Europe%2FLondon"
)

def get_weather():
    try:
        with urllib.request.urlopen(WEATHER_URL, timeout=10) as resp:
            data = json.loads(resp.read())

        cur  = data["current"]
        day  = data["daily"]
        code = int(cur["weather_code"])
        desc, emoji = WMO_CODES.get(code, ("Unknown", "🌡️"))

        # Build 3-day forecast list
        forecast = []
        for i in range(3):
            day_code = int(day["weather_code"][i])
            day_desc, day_emoji = WMO_CODES.get(day_code, ("Unknown", "🌡️"))
            # sunshine_duration is in seconds, convert to hours
            sunshine_hrs = round(day["sunshine_duration"][i] / 3600, 1)
            forecast.append({
                "date":         day["time"][i],
                "description":  day_desc,
                "emoji":        day_emoji,
                "temp_max":     day["temperature_2m_max"][i],
                "temp_min":     day["temperature_2m_min"][i],
                "sunshine_hrs": sunshine_hrs,
            })

        return {
            "temperature":  cur["temperature_2m"],
            "description":  desc,
            "emoji":        emoji,
            "wind_kph":     cur["wind_speed_10m"],
            "forecast":     forecast,
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
            "error":        str(exc),
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing weather client...")
    w = get_weather()
    if w["error"]:
        print(f"FAILED: {w['error']}")
    else:
        print(f"  Current : {w['emoji']} {w['description']} {w['temperature']}°C wind {w['wind_kph']} km/h")
        print(f"\n  3-day forecast:")
        for day in w["forecast"]:
            print(f"    {day['date']} {day['emoji']} {day['description']} "
                  f"H:{day['temp_max']}° L:{day['temp_min']}° "
                  f"sunshine:{day['sunshine_hrs']}hrs")