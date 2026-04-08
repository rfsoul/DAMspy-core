#!/usr/bin/env python3
"""
rpicontrol_feature_test.py

Simple LAN-side test client for damspy-rpicontrol.

What it tests:
- GET  /health
- POST /api/devices/tx/commands/start-rf with JSON payload
- POST /api/devices/tx/commands/stop-rf

Unified TX curl examples:
    curl -X POST http://10.0.1.195:8000/api/devices/tx/commands/start-rf \
      -H "Content-Type: application/json" \
      -d '{"channel": 0, "power": 10}'

    curl -X POST http://10.0.1.195:8000/api/devices/tx/commands/stop-rf \
      -H "Content-Type: application/json" \
      -d '{}'

Based on the external interface spec:
- short timeouts
- retry 502 / network timeout with exponential backoff
- do not blind-retry 503 or 422

Example:
    python rpicontrol_feature_test.py --base http://10.0.1.195:8000

Optional:
    python rpicontrol_feature_test.py --base http://10.0.1.195:8000 --dwell 1.5
"""

import argparse
import json
import sys
import time
from typing import Any, Dict, Optional, Tuple

import requests


DEFAULT_BASE = "http://10.0.1.195:8000"
DEFAULT_TIMEOUT = 5.0
DEFAULT_DWELL = 1.0
DEFAULT_RETRIES = 3
DEFAULT_BACKOFFS = [0.25, 0.5, 1.0]


class TestFailure(Exception):
    """Raised when a test step fails."""


def pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, indent=2, sort_keys=True)
    except Exception:
        return str(obj)


def response_json_or_text(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return resp.text


def request_with_policy(
    method: str,
    url: str,
    *,
    timeout: float,
    retries: int,
    json_body: Optional[Dict[str, Any]] = None,
) -> Tuple[requests.Response, Any]:
    """
    Retry only on:
    - HTTP 502
    - network timeouts / connection errors

    Do not retry:
    - 503 device unavailable
    - 422 validation errors
    - other non-2xx statuses
    """
    backoffs = DEFAULT_BACKOFFS[:max(0, retries - 1)]

    last_error = None

    for attempt in range(1, retries + 1):
        try:
            resp = requests.request(method, url, json=json_body, timeout=timeout)
            body = response_json_or_text(resp)

            if resp.status_code == 502 and attempt < retries:
                sleep_s = backoffs[min(attempt - 1, len(backoffs) - 1)] if backoffs else 0
                print(f"  -> got 502, retrying in {sleep_s:.2f}s")
                time.sleep(sleep_s)
                continue

            return resp, body

        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            if attempt < retries:
                sleep_s = backoffs[min(attempt - 1, len(backoffs) - 1)] if backoffs else 0
                print(f"  -> network error: {exc}; retrying in {sleep_s:.2f}s")
                time.sleep(sleep_s)
                continue
            raise TestFailure(f"Network failure after {retries} attempts: {exc}") from exc

    raise TestFailure(f"Request failed: {last_error}")


def expect_status(resp: requests.Response, expected: int, body: Any) -> None:
    if resp.status_code != expected:
        raise TestFailure(
            f"Expected HTTP {expected}, got {resp.status_code}\nResponse:\n{pretty(body)}"
        )


def print_step(title: str) -> None:
    print(f"\n=== {title} ===")


def test_health(base: str, timeout: float, retries: int) -> None:
    print_step("GET /health")
    url = f"{base}/health"
    resp, body = request_with_policy("GET", url, timeout=timeout, retries=retries)
    expect_status(resp, 200, body)

    print("PASS")
    print(pretty(body))


def test_start(base: str, timeout: float, retries: int) -> None:
    print_step("POST /api/devices/tx/commands/start-rf")
    url = f"{base}/api/devices/tx/commands/start-rf"
    payload = {
        "channel": 0,
        "power": 10,
    }

    print(f"Request payload:\n{pretty(payload)}")
    resp, body = request_with_policy(
        "POST",
        url,
        timeout=timeout,
        retries=retries,
        json_body=payload,
    )
    expect_status(resp, 200, body)

    print("PASS")
    print(pretty(body))


def test_stop(base: str, timeout: float, retries: int) -> None:
    print_step("POST /api/devices/tx/commands/stop-rf")
    url = f"{base}/api/devices/tx/commands/stop-rf"
    resp, body = request_with_policy("POST", url, timeout=timeout, retries=retries, json_body={})
    expect_status(resp, 200, body)

    print("PASS")
    print(pretty(body))


def run_all(base: str, timeout: float, retries: int, dwell: float) -> None:
    print(f"Base URL: {base}")
    print(f"Timeout : {timeout:.1f}s")
    print(f"Retries : {retries}")
    print(f"Dwell   : {dwell:.1f}s")

    test_health(base, timeout, retries)
    test_start(base, timeout, retries)

    if dwell > 0:
        print(f"\nWaiting {dwell:.2f}s dwell time...")
        time.sleep(dwell)

    test_stop(base, timeout, retries)

    print("\n=== ALL TESTS COMPLETED ===")
    print("PASS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test damspy-rpicontrol features over LAN.")
    parser.add_argument(
        "--base",
        default=DEFAULT_BASE,
        help=f"Base URL of the rpicontrol service (default: {DEFAULT_BASE})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Per-request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--dwell",
        type=float,
        default=DEFAULT_DWELL,
        help=f"Pause between RF start and stop, in seconds (default: {DEFAULT_DWELL})",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Max attempts for 502/network failures (default: {DEFAULT_RETRIES})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        run_all(
            base=args.base.rstrip("/"),
            timeout=args.timeout,
            retries=args.retries,
            dwell=args.dwell,
        )
        return 0
    except KeyboardInterrupt:
        print("\nAborted by user.")
        return 130
    except TestFailure as exc:
        print("\n=== TEST FAILED ===")
        print(str(exc))
        return 1
    except Exception as exc:
        print("\n=== UNEXPECTED ERROR ===")
        print(str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
