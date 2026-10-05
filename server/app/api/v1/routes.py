import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from typing import List, Optional

from app.schemas import Item

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


async def _fetch_latest_rows(measurement: str, bucket: str, sensor: Optional[str], limit: int) -> list[dict]:
    """Query InfluxDB and return the most recent `limit` rows for a measurement (optionally filtered by sensor)."""
    client_kwargs = get_influx_client_kwargs()

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

    async with InfluxDBClientAsync(**client_kwargs) as client:
        query_api = client.query_api()
        tables = await query_api.query(query=flux_query, params=params)

    return [
        {k: v for k, v in record.values.items() if k not in ("result", "table", "_start", "_stop")}
        for table in tables
        for record in table.records
    ]


@router.get("/influx/latest/{measurement}")
async def get_latest_influx_measurement(
    measurement: str,
    bucket: str = Query(..., description="InfluxDB bucket name"),
    sensor: Optional[str] = Query(None, description="Filter to a single sensor/simulator, e.g. 'solar_simulator_01'"),
    limit: int = Query(1, ge=1, le=20),
):
    """Return the most recent row(s) from an InfluxDB measurement as JSON for the UI."""
    try:
        rows = await _fetch_latest_rows(measurement, bucket, sensor, limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to query InfluxDB: {exc}") from exc

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


@router.get("/influx/stream/{measurement}")
async def stream_latest_influx_measurement(
    request: Request,
    measurement: str,
    bucket: str = Query(..., description="InfluxDB bucket name"),
    sensor: Optional[str] = Query(None, description="Filter to a single sensor/simulator, e.g. 'solar_simulator_01'"),
    interval_seconds: int = Query(30, ge=5, le=3600, description="Polling interval in seconds"),
):
    """Server-Sent Events stream: pushes the latest measurement row every `interval_seconds`."""

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break

            try:
                rows = await _fetch_latest_rows(measurement, bucket, sensor, 1)
                if rows:
                    payload = {
                        "measurement": measurement,
                        "bucket": bucket,
                        "sensor": sensor,
                        "values": rows[0],
                    }
                else:
                    payload = {"error": f"No data found for measurement '{measurement}' in bucket '{bucket}'"}
            except RuntimeError as exc:
                payload = {"error": str(exc)}
            except Exception as exc:
                payload = {"error": f"Failed to query InfluxDB: {exc}"}

            yield f"data: {json.dumps(payload, default=str)}\n\n"
            await asyncio.sleep(interval_seconds)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


async def _fetch_field_history(
    measurement: str,
    bucket: str,
    sensor: Optional[str],
    influx_field: str,
    response_key: str,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """Query InfluxDB for a single field's time series between start and end (optionally filtered by sensor)."""
    client_kwargs = get_influx_client_kwargs()

    params = {
        "bucket": bucket,
        "measurement": measurement,
        "field": influx_field,
        "start": start,
        "end": end,
    }
    sensor_filter = ""
    if sensor:
        params["sensor"] = sensor
        sensor_filter = "and r.sensor == sensor"

    flux_query = f"""
        from(bucket: bucket)
          |> range(start: start, stop: end)
          |> filter(fn: (r) => r._measurement == measurement and r._field == field {sensor_filter})
          |> sort(columns: ["_time"])
    """

    async with InfluxDBClientAsync(**client_kwargs) as client:
        query_api = client.query_api()
        tables = await query_api.query(query=flux_query, params=params)

    return [
        {
            "timestamp": record.get_time(),
            response_key: record.get_value(),
            "sensor": record.values.get("sensor"),
        }
        for table in tables
        for record in table.records
    ]


def _default_history_range(start: Optional[datetime], end: Optional[datetime]) -> tuple[datetime, datetime]:
    range_end = end or datetime.now(timezone.utc)
    range_start = start or (range_end - timedelta(hours=24))
    return range_start, range_end


@router.get("/influx/measurement/history/temperature")
async def get_temperature_history(
    measurement: str = Query(..., description="InfluxDB measurement name"),
    bucket: str = Query(..., description="InfluxDB bucket name"),
    sensor: Optional[str] = Query(None, description="Filter to a single sensor/simulator, e.g. 'solar_simulator_01'"),
    start: Optional[datetime] = Query(None, description="Range start (ISO 8601). Defaults to 24h before `end`."),
    end: Optional[datetime] = Query(None, description="Range end (ISO 8601). Defaults to now."),
):
    """Return a temperature time series (timestamp + sensor + temperature) for graphing."""
    range_start, range_end = _default_history_range(start, end)

    try:
        rows = await _fetch_field_history(measurement, bucket, sensor, "temperature", "temperature", range_start, range_end)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to query InfluxDB: {exc}") from exc

    return {"measurements": rows}


@router.get("/influx/measurement/history/intensity")
async def get_intensity_history(
    measurement: str = Query(..., description="InfluxDB measurement name"),
    bucket: str = Query(..., description="InfluxDB bucket name"),
    sensor: Optional[str] = Query(None, description="Filter to a single sensor/simulator, e.g. 'solar_simulator_01'"),
    start: Optional[datetime] = Query(None, description="Range start (ISO 8601). Defaults to 24h before `end`."),
    end: Optional[datetime] = Query(None, description="Range end (ISO 8601). Defaults to now."),
):
    """Return a measured-light-intensity time series (timestamp + sensor + measured_intensity) for graphing."""
    range_start, range_end = _default_history_range(start, end)

    try:
        rows = await _fetch_field_history(
            measurement, bucket, sensor, "measured_light_intensity", "measured_intensity", range_start, range_end
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to query InfluxDB: {exc}") from exc

    return {"measurements": rows}
