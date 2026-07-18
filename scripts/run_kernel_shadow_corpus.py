import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
DEFAULT_CORPUS = ROOT / "contracts" / "golden" / "parity-v1"
sys.path.insert(0, str(BACKEND_ROOT))

from app.contracts.generated.lob.exchange.v1 import exchange_pb2  # noqa: E402
from app.contracts.python_reference import PythonReferenceKernel  # noqa: E402
from app.contracts.shadow import GrpcKernelRunner, OfflineShadowKernel  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay the golden corpus through Python and a Java gRPC candidate.")
    parser.add_argument("--target", default="127.0.0.1:50051", help="Java kernel gRPC host:port")
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, help="Optional JSONL report destination")
    args = parser.parse_args()

    manifest = json.loads((args.corpus / "manifest.json").read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    with GrpcKernelRunner(args.target, timeout_seconds=args.timeout_seconds) as candidate:
        shadow = OfflineShadowKernel(PythonReferenceKernel().run, candidate)
        for case in manifest["cases"]:
            request = exchange_pb2.SimulationRequest.FromString(
                (args.corpus / case["request_file"]).read_bytes()
            )
            row = {"case_id": case["case_id"], **shadow.run(request).outcome.to_dict()}
            rows.append(row)
            print(json.dumps(row, sort_keys=True))

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("".join(f"{json.dumps(row, sort_keys=True)}\n" for row in rows), encoding="utf-8")
    return 0 if all(row["status"] == "match" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
