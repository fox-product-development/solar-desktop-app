# core/sigen_client.py
import asyncio
import logging
from sigen import Sigen
import config

log = logging.getLogger(__name__)

async def _get_client():
    client = Sigen(
        username=config.SIGEN_USERNAME,
        password=config.SIGEN_PASSWORD,
        region=config.SIGEN_REGION,
    )
    await client.async_initialize()
    return client

async def _fetch_live(client):
    raw = await client.get_energy_flow()
    
    pv_power   = float(raw.get("pvPower", 0.0))
    load_power = float(raw.get("loadPower", 0.0))
    grid_power = float(raw.get("buySellPower", 0.0))
    day_nrg    = float(raw.get("pvDayNrg", 0.0))

    # Load satisfaction — % of current load covered by solar
    # Load satisfaction
    if pv_power >= load_power and load_power > 0:
        load_pct = 100.0
    elif pv_power > 0 and load_power > 0:
        load_pct = round((pv_power / load_power) * 100, 1)
    else:
        load_pct = 0.0

    return {
        "pv_power_kw":      pv_power,
        "load_power_kw":    load_power,
        "grid_power_kw":    grid_power,   # positive = exporting, negative = importing
        "is_exporting":     grid_power > 0,
        "pv_day_kwh":       day_nrg,
        "load_satisfied_pct": load_pct,
    }

def get_live_data():
    async def _run():
        client = await _get_client()
        try:
            return await _fetch_live(client)
        finally:
            pass  # sigen library manages its own session
    try:
        return asyncio.run(_run())
    except Exception as exc:
        log.error("get_live_data failed: %s", exc)
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing Sigen client...")
    data = get_live_data()
    if data:
        print(f"  Generation  : {data['pv_power_kw']} kW")
        print(f"  Load        : {data['load_power_kw']} kW")
        print(f"  Grid        : {data['grid_power_kw']} kW ({'exporting' if data['is_exporting'] else 'importing'})")
        print(f"  Today so far: {data['pv_day_kwh']} kWh")
        print(f"  Load satisfied: {data['load_satisfied_pct']}%")
    else:
        print("FAILED")