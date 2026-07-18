import argparse
import hashlib
import json
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
OUTPUT_ROOT = ROOT / "contracts" / "golden" / "parity-v1"
sys.path.insert(0, str(BACKEND_ROOT))

from app.contracts.generated.lob.exchange.v1 import exchange_pb2  # noqa: E402
from app.contracts.python_reference import PythonReferenceKernel  # noqa: E402


@dataclass(frozen=True)
class CorpusCase:
    case_id: str
    scenario_name: str
    seed: int
    max_ticks: int
    normal_agent_count: int = 3
    baseline_liquidity_levels: int = 12


CASES = (
    CorpusCase("normal-market-seed-42", "normal_market", 42, 6),
    CorpusCase(
        "empty-book-seed-7",
        "normal_market",
        7,
        3,
        normal_agent_count=0,
        baseline_liquidity_levels=0,
    ),
    CorpusCase("spoofing-like-wall-seed-42", "spoofing_like_wall", 42, 10),
    CorpusCase("layering-like-seed-43", "layering_like", 43, 12),
    CorpusCase("quote-stuffing-seed-44", "quote_stuffing", 44, 10),
    CorpusCase("liquidity-evaporation-seed-45", "liquidity_evaporation", 45, 10),
)


def build_request(case: CorpusCase) -> exchange_pb2.SimulationRequest:
    return exchange_pb2.SimulationRequest(
        contract_version=1,
        run_id=f"GOLDEN-{case.case_id.upper()}",
        scenario=exchange_pb2.ScenarioInput(
            scenario_id=f"golden-{case.case_id}",
            scenario_name=case.scenario_name,
            scenario_family=case.scenario_name,
            seed=case.seed,
            max_ticks=case.max_ticks,
        ),
        config=exchange_pb2.SimulationConfig(
            symbol="BTCUSDT",
            venue="GOLDEN-SIM",
            price_tick_size_nanos=1_000_000_000,
            quantity_lot_size_nanos=1_000_000,
            snapshot_depth=12,
            max_events=250_000,
            reference_price_ticks=68_125,
            baseline_liquidity_levels=case.baseline_liquidity_levels,
            baseline_liquidity_base_lots=1_500,
            tick_interval_ns=500_000_000,
            normal_agent_count=case.normal_agent_count,
            baseline_liquidity_tick_size_ticks=1,
            max_agent_quote_lots=25_000,
        ),
    )


def generate(output_root: Path) -> None:
    cases_root = output_root / "cases"
    cases_root.mkdir(parents=True, exist_ok=True)
    kernel = PythonReferenceKernel()
    manifest_cases: list[dict[str, object]] = []
    expected_relative_files: set[Path] = {Path("manifest.json")}

    for case in CASES:
        request = build_request(case)
        result = kernel.run(request)
        request_bytes = request.SerializeToString(deterministic=True)
        result_bytes = result.SerializeToString(deterministic=True)
        case_root = cases_root / case.case_id
        case_root.mkdir(parents=True, exist_ok=True)
        request_path = case_root / "request.pb"
        result_path = case_root / "expected-result.pb"
        request_path.write_bytes(request_bytes)
        result_path.write_bytes(result_bytes)
        request_relative = request_path.relative_to(output_root)
        result_relative = result_path.relative_to(output_root)
        expected_relative_files.update((request_relative, result_relative))
        payload_counts = Counter(event.WhichOneof("payload") for event in result.events)
        manifest_cases.append(
            {
                "case_id": case.case_id,
                "scenario_name": case.scenario_name,
                "seed": case.seed,
                "max_ticks": case.max_ticks,
                "request_file": request_relative.as_posix(),
                "expected_result_file": result_relative.as_posix(),
                "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
                "expected_result_sha256": hashlib.sha256(result_bytes).hexdigest(),
                "event_stream_hash": result.event_stream_hash.hex(),
                "final_book_hash": result.final_book_hash.hex(),
                "event_count": len(result.events),
                "event_type_counts": dict(sorted(payload_counts.items())),
                "metric_count": len(result.metrics),
            }
        )

    manifest = {
        "corpus_version": 1,
        "contract_version": 1,
        "encoding": "deterministic-protobuf-binary",
        "canonical_hash": "sha256-v1",
        "cases": manifest_cases,
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    unexpected = {
        path.relative_to(output_root)
        for path in output_root.rglob("*")
        if path.is_file() and path.relative_to(output_root) not in expected_relative_files
    }
    if unexpected:
        joined = ", ".join(sorted(path.as_posix() for path in unexpected))
        raise RuntimeError(f"unexpected files in parity corpus: {joined}")


def check_generated() -> bool:
    if not OUTPUT_ROOT.is_dir():
        return False
    with tempfile.TemporaryDirectory(prefix="lob-arena-parity-") as temp_dir:
        candidate_root = Path(temp_dir) / "parity-v1"
        generate(candidate_root)
        expected = _file_digests(candidate_root)
        actual = _file_digests(OUTPUT_ROOT)
        return actual == expected


def _file_digests(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or validate the version 1 golden parity corpus.")
    parser.add_argument("--check", action="store_true", help="Fail if checked-in corpus files are stale.")
    args = parser.parse_args()
    if args.check:
        if check_generated():
            print("Golden parity corpus is current.")
            return 0
        print(
            "Golden parity corpus is stale; run scripts/generate_golden_parity_corpus.py.",
            file=sys.stderr,
        )
        return 1
    generate(OUTPUT_ROOT)
    print(f"Generated golden parity corpus under {OUTPUT_ROOT.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
