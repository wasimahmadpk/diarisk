"""Persist /predict rows so admin monitoring can compute live drift."""

from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from data import FEATURE_COLUMNS

TABLE = os.environ.get("DIARISK_DRIFT_TABLE", "")
REGION = os.environ.get("AWS_REGION", "eu-north-1")
BACKEND = os.environ.get("DIARISK_DRIFT_BACKEND", "dynamo" if TABLE else "memory")
TTL_DAYS = int(os.environ.get("DIARISK_DRIFT_TTL_DAYS", "7"))

_lock = threading.Lock()
_memory: list[dict[str, Any]] = []


def reset_memory() -> None:
    with _lock:
        _memory.clear()


def record_observation(features: dict[str, Any], prediction: int, probability: float) -> None:
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "features": {k: float(features[k]) for k in FEATURE_COLUMNS if k in features},
        "prediction": int(prediction),
        "probability": float(probability),
    }
    try:
        if BACKEND == "memory" or not TABLE:
            with _lock:
                _memory.append(row)
            return
        _put_dynamo(row)
    except Exception:
        # Scoring must not fail because monitoring storage failed.
        return


def recent_observations(hours: int = 72) -> list[dict[str, Any]]:
    start = datetime.now(timezone.utc) - timedelta(hours=max(1, hours))
    if BACKEND == "memory" or not TABLE:
        with _lock:
            rows = list(_memory)
        return [r for r in rows if _parse_ts(r.get("ts")) >= start]
    return _query_dynamo(start)


def _parse_ts(value: str | None) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _put_dynamo(row: dict[str, Any]) -> None:
    import boto3

    expires = int((datetime.now(timezone.utc) + timedelta(days=TTL_DAYS)).timestamp())
    item = {
        "pk": "live",
        "sk": f"{row['ts']}#{uuid.uuid4().hex[:8]}",
        "prediction": row["prediction"],
        "probability": Decimal(str(round(row["probability"], 4))),
        "expires_at": expires,
    }
    for key, val in row["features"].items():
        item[key] = Decimal(str(val))
    boto3.resource("dynamodb", region_name=REGION).Table(TABLE).put_item(Item=item)


def _query_dynamo(start: datetime) -> list[dict[str, Any]]:
    import boto3
    from boto3.dynamodb.conditions import Key

    table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE)
    rows: list[dict[str, Any]] = []
    kwargs: dict[str, Any] = {
        "KeyConditionExpression": Key("pk").eq("live") & Key("sk").gte(start.isoformat()),
    }
    while True:
        resp = table.query(**kwargs)
        for item in resp.get("Items", []):
            rows.append(
                {
                    "ts": str(item.get("sk", "")).split("#", 1)[0],
                    "prediction": int(item["prediction"]),
                    "probability": float(item["probability"]),
                    "features": {k: float(item[k]) for k in FEATURE_COLUMNS if k in item},
                }
            )
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return rows
