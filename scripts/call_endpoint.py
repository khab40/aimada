import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


SAMPLE_ALERT = {
    "bids": [{"price": 68120, "quantity": 12.4, "owner": "abuser"}],
    "asks": [{"price": 68130, "quantity": 1.8, "owner": "normal"}],
    "features": {
        "wall_size_ratio": 8.2,
        "message_rate": 21.0,
        "cancel_to_trade_ratio": 5.4,
        "depth_change_pct": 0.38,
        "imbalance": 0.72,
    },
    "scenario_hint": "spoofing",
    "tick": 12,
}

SAMPLE_REPORT = {
    "scenario_trace": {"scenario": "spoofing", "run_id": "demo"},
    "alerts": [{"detector": "spoofing_like", "confidence": 0.91}],
    "metrics": {"precision": 0.91, "recall": 0.88, "f1": 0.895, "avg_detection_latency_ms": 750},
}

def main() -> None:
    parser = argparse.ArgumentParser(description="Call Nebius Serverless AI endpoint contract.")
    parser.add_argument("--base-url", default=os.environ.get("NEBIUS_ENDPOINT_BASE_URL", "http://localhost:9000"))
    parser.add_argument("--route", choices=["orderbook-alert", "investigation-report"], default="orderbook-alert")
    parser.add_argument("--payload", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.payload.read_text(encoding="utf-8")) if args.payload else (
        SAMPLE_ALERT if args.route == "orderbook-alert" else SAMPLE_REPORT
    )
    url = f"{args.base_url.rstrip('/')}/{args.route}"
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("ENDPOINT_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urlopen(request, timeout=20) as response:
        print(json.dumps(json.loads(response.read().decode("utf-8")), indent=2))


if __name__ == "__main__":
    main()
