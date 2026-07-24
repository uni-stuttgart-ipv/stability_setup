from fastapi import APIRouter, HTTPException, Query
from app.schemas import Item
from typing import List, Optional
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
import os
from dotenv import load_dotenv

router = APIRouter()

#load environment variables from .env file
load_dotenv()

def get_influx_client_kwargs():
    token = os.getenv("INFLUX_TOKEN")
    org = os.getenv("INFLUX_ORG", "Institute of Photovoltaics")
    host = os.getenv("INFLUX_HOST", "https://eu-central-1-1.aws.cloud2.influxdata.com")

    if not token:
        raise RuntimeError("INFLUX_TOKEN environment variable is not set")

    return {"url": host, "token": token, "org": org}


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/items", response_model=List[Item])
async def list_items():
    return [
        {"id": 1, "name": "Example item", "description": "A sample boilerplate item."}
    ]


@router.post("/items", response_model=Item, status_code=201)
async def create_item(item: Item):
    return item


@router.get("/influx/latest/{measurement}")
async def get_latest_influx_measurement(
    measurement: str,
    bucket: str = Query(..., description="InfluxDB bucket name"),
    sensor: Optional[str] = Query(None, description="Filter to a single sensor/simulator, e.g. 'solar_simulator_01'"),
    limit: int = Query(1, ge=1, le=20),
):
    """Return the most recent row(s) from an InfluxDB measurement as JSON for the UI."""
    try:
        client_kwargs = get_influx_client_kwargs()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    params = {"bucket": bucket, "measurement": measurement, "rowLimit": limit}
    sensor_filter = ""
    if sensor:
        params["sensor"] = sensor
        sensor_filter = "and r.sensor == sensor"

    flux_query = f"""
        from(bucket: bucket)
          |> range(start: -100y)
          |> filter(fn: (r) => r._measurement == measurement {sensor_filter})
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> group()
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: rowLimit)
    """

    try:
        async with InfluxDBClientAsync(**client_kwargs) as client:
            query_api = client.query_api()
            tables = await query_api.query(query=flux_query, params=params)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to query InfluxDB: {exc}") from exc

    rows = [
        {k: v for k, v in record.values.items() if k not in ("result", "table", "_start", "_stop")}
        for table in tables
        for record in table.records
    ]

    if not rows:
        sensor_detail = f" for sensor '{sensor}'" if sensor else ""
        raise HTTPException(status_code=404, detail=f"No data found for measurement '{measurement}'{sensor_detail} in bucket '{bucket}'")

    return {
        "measurement": measurement,
        "bucket": bucket,
        "sensor": sensor,
        "count": len(rows),
        "values": rows[0],
    }
