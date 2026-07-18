import argparse
import filecmp
import sys
import tempfile
from pathlib import Path

from grpc_tools import protoc

ROOT = Path(__file__).resolve().parents[1]
PROTO_ROOT = ROOT / "contracts" / "proto"
PROTO_FILE = PROTO_ROOT / "lob" / "exchange" / "v1" / "exchange.proto"
OUTPUT_ROOT = ROOT / "backend" / "app" / "contracts" / "generated"
GENERATED_FILES = (
    Path("lob/exchange/v1/exchange_pb2.py"),
    Path("lob/exchange/v1/exchange_pb2.pyi"),
)


def generate(output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    result = protoc.main(
        [
            "grpc_tools.protoc",
            f"-I{PROTO_ROOT}",
            f"--python_out={output_root}",
            f"--pyi_out={output_root}",
            str(PROTO_FILE),
        ]
    )
    if result != 0:
        raise RuntimeError(f"protoc failed with exit code {result}")


def check_generated() -> bool:
    with tempfile.TemporaryDirectory(prefix="lob-arena-proto-") as temp_dir:
        candidate_root = Path(temp_dir)
        generate(candidate_root)
        return all(
            (OUTPUT_ROOT / relative_path).is_file()
            and filecmp.cmp(OUTPUT_ROOT / relative_path, candidate_root / relative_path, shallow=False)
            for relative_path in GENERATED_FILES
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or validate Python Protobuf bindings.")
    parser.add_argument("--check", action="store_true", help="Fail if checked-in bindings are stale.")
    args = parser.parse_args()
    if args.check:
        if check_generated():
            print("Protobuf bindings are current.")
            return 0
        print("Protobuf bindings are stale; run scripts/generate_protos.py.", file=sys.stderr)
        return 1
    generate(OUTPUT_ROOT)
    print(f"Generated Python bindings under {OUTPUT_ROOT.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
