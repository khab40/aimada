from fastapi import APIRouter

from app.reports.benchmark_report import build_benchmark_report

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.get("/summary")
def benchmark_summary() -> dict[str, object]:
    return build_benchmark_report(
        run_count=0,
        detections=[],
        labels=[],
    )
