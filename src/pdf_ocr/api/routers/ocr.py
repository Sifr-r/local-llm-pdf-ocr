import asyncio
import logging
import os
import tempfile
import time
import uuid
from typing import Any, cast

from fastapi import APIRouter, File, Form, Header, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError
from starlette.background import BackgroundTask

from pdf_ocr import (
    HybridAligner,
    OCRPipeline,
    OCRProcessor,
    PDFHandler,
    PromptedGroundedOCR,
)
from pdf_ocr.api.schemas import ProcessSettings
from pdf_ocr.api.services.artifacts import (
    ArtifactAccessDeniedError,
    ArtifactNotFoundError,
    InvalidArtifactReferenceError,
    PageText,
    TextArtifactStore,
)
from pdf_ocr.api.services.jobs import JobHistory, JobStatus
from pdf_ocr.api.services.progress import ProgressService
from pdf_ocr.api.services.security import (
    SAFE_API_BASE_ERROR,
    SERVER_ERROR_MESSAGE,
    UploadValidationError,
    cleanup_files,
    save_validated_upload,
)
from pdf_ocr.utils import is_ssrf_target

from .config import _config
from .websocket import manager

router = APIRouter()
logger = logging.getLogger(__name__)
_text_artifacts = TextArtifactStore()
_job_history = JobHistory()
_progress_service = ProgressService()


def _cleanup(*paths):
    cleanup_files(*paths)


def _validation_error_response(exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid request parameters.",
            "detail": exc.errors(include_context=False),
        },
    )


def _stable_server_error(status_code: int = 500) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": SERVER_ERROR_MESSAGE}
    )


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _path_exists(path: str) -> bool:
    return os.path.exists(path)


# ---------------------------------------------------------------------------
# In-memory job history – capped at 50 entries (FIFO)
# ---------------------------------------------------------------------------
def stage_to_percent(stage: str, current: int, total: int) -> int:
    """Map a pipeline stage + sub-progress into a 0-100 overall percent."""
    return _progress_service.stage_to_percent(stage, current, total)


def _record_job(
    job_id: str,
    filename: str,
    model: str,
    pipeline_mode: str,
    pages: str | None,
    duration_s: float,
    status: JobStatus,
) -> None:
    """Append a validated job record to the capped in-memory history."""
    _job_history.record(
        job_id=job_id,
        filename=filename,
        model=model,
        pipeline_mode=pipeline_mode,
        pages=pages,
        duration_s=duration_s,
        status=status,
    )


# ---- Job history ----------------------------------------------------------


@router.get("/api/jobs")
async def get_jobs():
    """Return the recent job history (newest first)."""
    return _job_history.list()


@router.delete("/api/jobs")
async def clear_jobs():
    """Clear recent job history and current text artifacts."""
    await asyncio.to_thread(_text_artifacts.clear)
    _job_history.clear()
    return {"status": "ok"}


# ---- PDF / image processing ----------------------------------------------


@router.post("/process")
async def process_pdf(
    file: UploadFile = File(...),
    client_id: str | None = Form(None),
    progress_channel: str | None = Form(None),
    progress_token: str | None = Form(None),
    api_base: str | None = Form(None),
    api_key: str | None = Form(None),
    model: str | None = Form(None),
    pipeline_mode: str | None = Form(None),
    dpi: str | None = Form(None),
    concurrency: str | None = Form(None),
    dense_mode: str | None = Form(None),
    dense_threshold: str | None = Form(None),
    pages: str | None = Form(None),
    refine: str | None = Form(None),
    max_image_dim: str | None = Form(None),
    self_correction: str | None = Form(None),
    binarize: str | None = Form(None),
    dual_engine: str | None = Form(None),
    spellcheck: str | None = Form(None),
    cross_page: str | None = Form(None),
):
    """
    Process a PDF or image file through the OCR pipeline.

    Every optional parameter falls back to the in-memory config store when
    not supplied by the caller.
    """
    try:
        settings = ProcessSettings.model_validate(
            {
                "api_base": api_base if api_base is not None else _config["api_base"],
                "api_key": api_key if api_key is not None else _config["api_key"],
                "model": model if model is not None else _config["model"],
                "pipeline_mode": pipeline_mode
                if pipeline_mode is not None
                else _config["pipeline_mode"],
                "dpi": dpi if dpi is not None else _config["dpi"],
                "concurrency": concurrency
                if concurrency is not None
                else _config["concurrency"],
                "dense_mode": dense_mode
                if dense_mode is not None
                else _config["dense_mode"],
                "dense_threshold": dense_threshold
                if dense_threshold is not None
                else _config["dense_threshold"],
                "pages": pages,
                "refine": refine if refine is not None else _config["refine"],
                "max_image_dim": max_image_dim
                if max_image_dim is not None
                else _config["max_image_dim"],
                "self_correction": self_correction
                if self_correction is not None
                else _config["self_correction"],
                "binarize": binarize if binarize is not None else _config["binarize"],
                "dual_engine": dual_engine
                if dual_engine is not None
                else _config["dual_engine"],
                "spellcheck": spellcheck
                if spellcheck is not None
                else _config["spellcheck"],
                "cross_page": cross_page
                if cross_page is not None
                else _config["cross_page"],
            }
        )
    except ValidationError as exc:
        return _validation_error_response(exc)

    if is_ssrf_target(settings.api_base):
        return JSONResponse(status_code=403, content={"error": SAFE_API_BASE_ERROR})

    try:
        upload = await save_validated_upload(file)
    except UploadValidationError as exc:
        return JSONResponse(status_code=exc.status_code, content={"error": str(exc)})

    input_path = upload.path
    progress_target = (
        progress_channel
        if manager.is_authorized(progress_channel, progress_token)
        else None
    )
    output_path = os.path.join(tempfile.gettempdir(), f"output_{uuid.uuid4()}.pdf")
    text_path: str | None = None
    job_id = uuid.uuid4().hex
    t_start = time.monotonic()

    try:
        await manager.send_progress(progress_target, "Initializing...", 5, stage="init")

        # -- Build the pipeline based on the selected mode -------------------
        backend: Any
        if settings.pipeline_mode == "grounded":
            backend = PromptedGroundedOCR(
                api_base=settings.api_base,
                api_key=settings.api_key,
                model=settings.model,
                max_image_dim=settings.max_image_dim,
                concurrency=settings.concurrency,
            )
            pipeline = OCRPipeline(
                aligner=HybridAligner(),
                ocr_processor=OCRProcessor(
                    api_base=settings.api_base,
                    api_key=settings.api_key,
                    model=settings.model,
                ),
                pdf_handler=PDFHandler(),
                grounded_backend=backend,
            )
        else:
            # Default: hybrid mode
            backend = OCRProcessor(
                api_base=settings.api_base,
                api_key=settings.api_key,
                model=settings.model,
            )
            pipeline = OCRPipeline(
                aligner=HybridAligner(),
                ocr_processor=backend,
                pdf_handler=PDFHandler(),
            )

        # Verify model
        verify = _config.get("verify_model", True)

        # Automatically skip verification for cloud models since /v1/models is an LM Studio/Ollama extension
        # LiteLLM prefixes or known cloud hosts indicate it's not a local server.
        is_cloud = (
            any(
                settings.model.startswith(prefix)
                for prefix in (
                    "openai/",
                    "anthropic/",
                    "gemini/",
                    "deepseek/",
                    "groq/",
                    "vertex_ai/",
                )
            )
            or "api.openai.com" in settings.api_base
        )
        if is_cloud:
            verify = False

        if verify:
            await backend.ensure_model_loaded()

        # -- Progress callback -----------------------------------------------
        async def on_progress(stage, current, total, message):
            await manager.send_progress(
                progress_target,
                message,
                stage_to_percent(stage, current, total),
                stage=stage,
            )

        # -- Run the pipeline ------------------------------------------------
        pages_text = await pipeline.run(
            input_path,
            output_path,
            dpi=settings.dpi,
            pages=settings.pages,
            concurrency=settings.concurrency,
            refine=settings.refine,
            max_image_dim=settings.max_image_dim,
            dense_threshold=settings.dense_threshold,
            dense_mode=settings.dense_mode,
            self_correction=settings.self_correction,
            binarize=settings.binarize,
            dual_engine=settings.dual_engine,
            spellcheck=settings.spellcheck,
            cross_page=settings.cross_page,
            progress=on_progress,
        )

        # -- Persist extracted text for token-bound later retrieval ----------
        artifact_handle = await asyncio.to_thread(
            _text_artifacts.create, cast(PageText, pages_text)
        )
        text_path = artifact_handle.path
        job_id = artifact_handle.artifact_id

        duration_s = time.monotonic() - t_start
        _record_job(
            job_id=job_id,
            filename=file.filename or "unknown",
            model=settings.model,
            pipeline_mode=settings.pipeline_mode,
            pages=settings.pages,
            duration_s=duration_s,
            status="complete",
        )

        await manager.send_progress(
            progress_target, "Done! Preparing download...", 100, stage="complete"
        )

        response = FileResponse(
            output_path,
            media_type="application/pdf",
            filename=f"ocr_{file.filename}",
            background=BackgroundTask(_cleanup, input_path, output_path),
        )
        response.headers["X-Text-Artifact-Id"] = artifact_handle.artifact_id
        response.headers["X-Text-Artifact-Token"] = artifact_handle.token
        return response

    except ValueError as ve:
        duration_s = time.monotonic() - t_start
        _record_job(
            job_id=job_id,
            filename=file.filename or "unknown",
            model=settings.model,
            pipeline_mode=settings.pipeline_mode,
            pages=settings.pages,
            duration_s=duration_s,
            status="error",
        )
        logger.warning("OCR processing rejected invalid input: %s", ve)
        await manager.send_progress(progress_target, "Invalid input.", 0, stage="error")
        _cleanup(input_path, output_path, text_path)
        return JSONResponse(status_code=400, content={"error": "Invalid input."})

    except Exception:
        duration_s = time.monotonic() - t_start
        _record_job(
            job_id=job_id,
            filename=file.filename or "unknown",
            model=settings.model,
            pipeline_mode=settings.pipeline_mode,
            pages=settings.pages,
            duration_s=duration_s,
            status="error",
        )
        logger.exception("OCR processing failed")
        await manager.send_progress(
            progress_target, "Processing failed.", 0, stage="error"
        )
        _cleanup(input_path, output_path, text_path)
        return _stable_server_error()


# ---- Text retrieval -------------------------------------------------------


@router.get("/text/{artifact_id}")
async def get_text(
    artifact_id: str,
    token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
):
    access_token = _extract_bearer_token(authorization) or token
    if not access_token:
        return JSONResponse(status_code=403, content={"error": "Text access denied"})

    try:
        text_path = _text_artifacts.get(artifact_id, access_token)
    except (InvalidArtifactReferenceError, ArtifactNotFoundError):
        return JSONResponse(status_code=404, content={"error": "Text not found"})
    except ArtifactAccessDeniedError:
        return JSONResponse(status_code=403, content={"error": "Text access denied"})

    exists = await asyncio.to_thread(_path_exists, text_path)
    if exists:
        return FileResponse(
            text_path,
            media_type="application/json",
        )
    return JSONResponse(status_code=404, content={"error": "Text not found"})
