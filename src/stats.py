"""Read CloudWatch operational metrics for the live DiaRisk service."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

FUNCTION_NAME = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "diarisk-api")
API_ID = os.environ.get("DIARISK_HTTP_API_ID", "b2je1touwh")
REGION = os.environ.get("AWS_REGION", "eu-north-1")


def _series(result: dict[str, Any]) -> list[dict[str, float | str]]:
    timestamps = result.get("Timestamps") or []
    values = result.get("Values") or []
    pairs = sorted(zip(timestamps, values), key=lambda p: p[0])
    return [
        {"t": ts.astimezone(timezone.utc).isoformat(), "v": round(float(val), 2)}
        for ts, val in pairs
    ]


def _sum(points: list[dict[str, float | str]]) -> float:
    return round(sum(float(p["v"]) for p in points), 2)


def _avg(points: list[dict[str, float | str]]) -> float | None:
    if not points:
        return None
    return round(sum(float(p["v"]) for p in points) / len(points), 2)


def _max(points: list[dict[str, float | str]]) -> float | None:
    if not points:
        return None
    return round(max(float(p["v"]) for p in points), 2)


def collect_stats(hours: int = 24) -> dict[str, Any]:
    import boto3

    hours = max(1, min(hours, 72))
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    period = 3600 if hours >= 12 else 300

    client = boto3.client("cloudwatch", region_name=REGION)
    fn_dim = [{"Name": "FunctionName", "Value": FUNCTION_NAME}]
    api_dim = [{"Name": "ApiId", "Value": API_ID}]

    queries = [
        ("invocations", "AWS/Lambda", "Invocations", fn_dim, "Sum"),
        ("errors", "AWS/Lambda", "Errors", fn_dim, "Sum"),
        ("throttles", "AWS/Lambda", "Throttles", fn_dim, "Sum"),
        ("duration_avg", "AWS/Lambda", "Duration", fn_dim, "Average"),
        ("duration_p50", "AWS/Lambda", "Duration", fn_dim, "p50"),
        ("duration_p95", "AWS/Lambda", "Duration", fn_dim, "p95"),
        ("concurrent_max", "AWS/Lambda", "ConcurrentExecutions", fn_dim, "Maximum"),
        ("api_count", "AWS/ApiGateway", "Count", api_dim, "Sum"),
        ("api_4xx", "AWS/ApiGateway", "4xx", api_dim, "Sum"),
        ("api_5xx", "AWS/ApiGateway", "5xx", api_dim, "Sum"),
        ("api_latency", "AWS/ApiGateway", "Latency", api_dim, "Average"),
    ]

    response = client.get_metric_data(
        MetricDataQueries=[
            {
                "Id": key,
                "MetricStat": {
                    "Metric": {
                        "Namespace": namespace,
                        "MetricName": metric,
                        "Dimensions": dims,
                    },
                    "Period": period,
                    "Stat": stat,
                },
                "ReturnData": True,
            }
            for key, namespace, metric, dims, stat in queries
        ],
        StartTime=start,
        EndTime=end,
        ScanBy="TimestampAscending",
    )

    by_id = {item["Id"]: _series(item) for item in response.get("MetricDataResults", [])}
    invocations = _sum(by_id.get("invocations", []))
    errors = _sum(by_id.get("errors", []))
    api_count = _sum(by_id.get("api_count", []))
    api_5xx = _sum(by_id.get("api_5xx", []))

    return {
        "window_hours": hours,
        "region": REGION,
        "function_name": FUNCTION_NAME,
        "generated_at": end.isoformat(),
        "lambda": {
            "invocations": invocations,
            "errors": errors,
            "throttles": _sum(by_id.get("throttles", [])),
            "error_rate_pct": round(100 * errors / invocations, 2) if invocations else 0.0,
            "duration_avg_ms": _avg(by_id.get("duration_avg", [])),
            "duration_p50_ms": _avg(by_id.get("duration_p50", [])),
            "duration_p95_ms": _avg(by_id.get("duration_p95", [])),
            "concurrent_max": _max(by_id.get("concurrent_max", [])),
        },
        "api": {
            "requests": api_count,
            "status_4xx": _sum(by_id.get("api_4xx", [])),
            "status_5xx": api_5xx,
            "error_rate_5xx_pct": round(100 * api_5xx / api_count, 2) if api_count else 0.0,
            "latency_avg_ms": _avg(by_id.get("api_latency", [])),
        },
        "series": {
            "invocations": by_id.get("invocations", []),
            "errors": by_id.get("errors", []),
            "duration_avg": by_id.get("duration_avg", []),
            "api_requests": by_id.get("api_count", []),
        },
    }
