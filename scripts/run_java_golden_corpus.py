import argparse
import hashlib
import json
import sys
from pathlib import Path

import grpc

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
DEFAULT_CORPUS = ROOT / "contracts" / "golden" / "parity-v1"
sys.path.insert(0, str(BACKEND_ROOT))

from app.contracts.generated.lob.exchange.v1 import exchange_pb2, exchange_pb2_grpc  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay the immutable golden corpus through the Java kernel.")
    parser.add_argument("--target", default="127.0.0.1:50051", help="Java kernel gRPC host:port")
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, help="Optional JSONL report destination")
    args = parser.parse_args()

    manifest = json.loads((args.corpus / "manifest.json").read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    with grpc.insecure_channel(args.target) as channel:
        stub = exchange_pb2_grpc.SimulationKernelStub(channel)
        for case in manifest["cases"]:
            request_bytes = (args.corpus / case["request_file"]).read_bytes()
            expected_bytes = (args.corpus / case["expected_result_file"]).read_bytes()
            request = exchange_pb2.SimulationRequest.FromString(request_bytes)
            actual = stub.RunSimulation(request, timeout=args.timeout_seconds)
            actual_bytes = actual.SerializeToString(deterministic=True)
            matches = actual_bytes == expected_bytes
            row = {
                "case_id": case["case_id"],
                "status": "match" if matches else "mismatch",
                "expected_sha256": hashlib.sha256(expected_bytes).hexdigest(),
                "actual_sha256": hashlib.sha256(actual_bytes).hexdigest(),
                "event_count": len(actual.events),
                "event_stream_hash": actual.event_stream_hash.hex(),
                "final_book_hash": actual.final_book_hash.hex(),
            }
            rows.append(row)
            print(json.dumps(row, sort_keys=True))

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            "".join(f"{json.dumps(row, sort_keys=True)}\n" for row in rows),
            encoding="utf-8",
        )
    return 0 if all(row["status"] == "match" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
