#!/usr/bin/env python3
"""
Conservative fallback HTTP benchmark tool for safe-api-performance-auditor.

Examples:
  python scripts/benchmark.py --url http://127.0.0.1:3000/api/health
  python scripts/benchmark.py --url http://127.0.0.1:3000/api/items --concurrency 10 --duration 30
  python scripts/benchmark.py --url http://127.0.0.1:3000/api/items --header "Authorization: Bearer TEST_TOKEN"
"""

import argparse
import asyncio
import json
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


def percentile(values, pct):
    if not values:
        return 0
    ordered = sorted(values)
    index = int(round((pct / 100) * (len(ordered) - 1)))
    return ordered[index]


def parse_headers(items):
    headers = {}
    for item in items or []:
        if ":" not in item:
            raise ValueError(f"Header must be 'Name: value': {item}")
        key, value = item.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers


def load_body(args):
    if args.body_file:
        return Path(args.body_file).read_text(encoding="utf-8")
    return args.body


def sync_request(url, method, headers, body, timeout, success_below):
    data = body.encode("utf-8") if body else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            status = response.status
            error = None
    except urllib.error.HTTPError as exc:
        status = exc.code
        error = "http_error"
    except TimeoutError:
        status = "timeout"
        error = "timeout"
    except Exception as exc:
        status = "request_error"
        error = exc.__class__.__name__

    latency_ms = (time.perf_counter() - start) * 1000
    ok = isinstance(status, int) and status < success_below
    return {
        "latency_ms": latency_ms,
        "status": status,
        "ok": ok,
        "error": error,
    }


async def run_phase(args, duration):
    loop = asyncio.get_running_loop()
    results = []
    deadline = time.perf_counter() + duration

    async def worker():
        while time.perf_counter() < deadline:
            result = await loop.run_in_executor(
                None,
                sync_request,
                args.url,
                args.method,
                args.headers,
                args.body,
                args.timeout,
                args.success_below,
            )
            results.append(result)

    start = time.perf_counter()
    tasks = [asyncio.create_task(worker()) for _ in range(args.concurrency)]
    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start
    return summarize(args, results, elapsed)


def summarize(args, results, elapsed):
    latencies = [row["latency_ms"] for row in results]
    statuses = Counter(str(row["status"]) for row in results)
    errors = Counter(str(row["error"]) for row in results if row["error"])
    total = len(results)
    failures = sum(1 for row in results if not row["ok"])

    return {
        "url": args.url,
        "method": args.method.upper(),
        "duration_s": round(elapsed, 3),
        "concurrency": args.concurrency,
        "timeout_s": args.timeout,
        "success_below": args.success_below,
        "total_requests": total,
        "successful_requests": total - failures,
        "failed_requests": failures,
        "timeout_count": statuses.get("timeout", 0),
        "error_rate_pct": round((failures / total * 100) if total else 0, 3),
        "rps": round(total / elapsed if elapsed else 0, 3),
        "latency_ms": {
            "avg": round(statistics.mean(latencies), 3) if latencies else 0,
            "p50": round(percentile(latencies, 50), 3),
            "p95": round(percentile(latencies, 95), 3),
            "p99": round(percentile(latencies, 99), 3),
            "max": round(max(latencies), 3) if latencies else 0,
        },
        "status_codes": dict(statuses),
        "errors": dict(errors),
    }


async def main():
    parser = argparse.ArgumentParser(description="Conservative fallback HTTP benchmark tool.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--method", default="GET")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--success-below", type=int, default=400)
    parser.add_argument("--header", action="append", default=[])
    parser.add_argument("--body", default=None)
    parser.add_argument("--body-file", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    args.headers = parse_headers(args.header)
    args.body = load_body(args)

    if args.body and not any(key.lower() == "content-type" for key in args.headers):
        args.headers["Content-Type"] = "application/json"

    if args.warmup > 0:
        await run_phase(args, args.warmup)

    report = await run_phase(args, args.duration)
    output = json.dumps(report, indent=2)
    print(output)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
