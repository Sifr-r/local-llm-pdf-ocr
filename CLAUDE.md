# CLAUDE.md

Repository guidance for Claude Code. Read `AGENTS.md` first; it contains the shared contributor rules. `README.md` is the user-facing source of truth for installation, Web UI behavior, environment variables, and HTTP routes.

## Common Commands

```bash
uv sync
uv sync --extra web
uv run local-deepl-server --port 8000

uv run pytest -m "not slow"
uv run ruff check src tests
uv run mypy src
```

## Web/API Workflow

- LocalDeepL is Web UI/API-first. Do not add or restore a user-facing CLI OCR workflow.
- Default hybrid path is `convert -> optional preprocess -> detect -> OCR -> align -> refine -> post-process -> DocumentResult -> processors -> embed`.
- Grounded path is `grounded OCR -> post-process -> DocumentResult -> processors -> embed`; grounded backends own their initial rasterization.
- Bounding boxes stay normalized as `[x0, y0, x1, y1]` until PDF embedding.
- Local model pre-flight checks call `GET /v1/models`; set `OCR_VERIFY_MODEL=0` for local web-server runs that need to skip this.

## Web/API Settings

The web workspace and FastAPI request schemas expose advanced settings:

- `self_correction`
- `binarize`
- `dual_engine`
- `spellcheck`
- `cross_page`
- `preprocess_pages`, `orientation_detection`, `deskew`, `denoise`, `normalize_contrast`, `crop_cleanup`
- `quality_routing`
- `document_processors` (`reading_order`, `quality_analysis`, `structure_analysis`, `section_analysis`, `layout_enrichment`, `table_extraction`)

Document new user workflow features as Web UI/API features.

## Translation Paths

There are two translation implementations:

- Synchronous browser/API translation routes in `api/routers/ocr.py`.
- Optional async translation in `core/translation.py`, `api/tasks.py`, and `api/celery_app.py` behind the `async-translation` extra.

LangGraph belongs at orchestration level only. Processor internals should remain plain Python and deterministic.

## Gotchas

- Do not move `tqdm_patch.apply()` before `from surya.detection import DetectionPredictor`.
- Preserve the Pillow override in `pyproject.toml`; Pillow 11.3 or newer provides AVIF decoding.
- Keep SSRF behavior explicit at API endpoints. `ALLOW_SSRF_LOCAL=true` intentionally permits local model servers during development.
- Windows launcher scripts start Redis, Celery, and Uvicorn. Ordinary manual web-server startup only needs the `web` extra.
