from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from app.data_ingestion.models import ImportAccepted, ImportedDataset, ImportWindowRequest, LobsterCandidate

router = APIRouter(prefix="/api/data-ingestion", tags=["data-ingestion"])


@router.get("/lobster/candidates", response_model=list[LobsterCandidate])
def list_lobster_candidates(request: Request) -> list[LobsterCandidate]:
    return request.app.state.data_ingestion.candidates()


@router.post(
    "/lobster/candidates/{candidate_id}/import",
    response_model=ImportAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def import_lobster_candidate(
    candidate_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    import_window: ImportWindowRequest,
) -> ImportAccepted:
    try:
        accepted, started = request.app.state.data_ingestion.begin_import(
            candidate_id,
            start_time_ms=import_window.start_time_ms,
            end_time_ms=import_window.end_time_ms,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="unknown candidate") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if started:
        background_tasks.add_task(
            request.app.state.data_ingestion.execute_import,
            candidate_id,
            import_window.start_time_ms,
            import_window.end_time_ms,
        )
    return accepted


@router.get("/datasets", response_model=list[ImportedDataset])
def list_datasets(request: Request) -> list[ImportedDataset]:
    return request.app.state.data_ingestion.datasets()


@router.get("/datasets/{dataset_id}", response_model=ImportedDataset)
def get_dataset(dataset_id: str, request: Request) -> ImportedDataset:
    dataset = request.app.state.data_ingestion.dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="unknown dataset")
    return dataset
