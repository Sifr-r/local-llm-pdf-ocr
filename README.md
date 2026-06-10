# LocalDeepL

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Web_UI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)](LICENSE)

LocalDeepL turns scanned PDFs and images into searchable, selectable PDFs using local vision language models. The supported product workflow is the FastAPI Web UI and API; the previous command-line OCR entrypoint has been removed so advanced document intelligence can stay centered on the easier browser experience.

## Features

- **Format Support**: PDFs and images, including JPEG, PNG, BMP, WebP, TIFF, and AVIF.
- **Searchable Output**: Sandwich PDFs with the original page image plus hidden searchable text.
- **Hybrid OCR**: Surya layout detection, VLM OCR, DP alignment, optional refine, and searchable PDF embedding.
- **Grounded OCR**: Bbox-native VLM path for models that return positioned text directly.
- **Local Document Intelligence**: Optional web/API processors for preprocessing, reading order, quality analysis, structure, sections, layout enrichment, table extraction, quality routing, metadata reports, and structured exports.
- **Web Workspace**: Page selection, WebSocket progress, preview, translation, extraction, export artifacts, and job history.

## Installation

```bash
git clone https://github.com/Sifr-r/LocalDeepL.git
cd LocalDeepL
uv sync --extra web
```

For asynchronous translation:

```bash
uv sync --extra web --extra async-translation
```

Real OCR requires an OpenAI-compatible VLM endpoint. The local-development default is LM Studio at `http://localhost:1234/v1`.

## Web Workspace

```bash
uv run local-deepl-server --port 8000
```

Open `http://localhost:8000`. The browser interface is the supported user workflow. Advanced document intelligence is exposed through Web UI controls and FastAPI request fields, not through a CLI.

The Advanced Configuration panel includes:

- **Preprocess Pages** with orientation detection, deskew, denoise, contrast normalization, and crop cleanup.
- **Reading Order** for deterministic top-to-bottom, left-to-right block ordering.
- **Quality Analysis** for page-level density, block counts, and advisory findings.
- **Structure Analysis** for headings, paragraphs, list items, key-values, table candidates, and empty blocks.
- **Section Analysis** for grouping content under detected headings across pages.
- **Layout Enrichment** for headers, footers, captions, page numbers, figures, title blocks, and body regions.
- **Table Extraction** for deterministic table reconstruction from OCR boxes.
- **Quality Routing** for recording local routing recommendations from quality findings.

OCR responses include token-bound text artifact headers. When processor metadata exists, responses also include `X-Document-Metadata-Artifact-Id` and `X-Document-Metadata-Artifact-Token`; fetch `GET /metadata/{artifact_id}` with the token to retrieve compact page/block metadata. Use `POST /api/export/document` to create token-bound JSON, Markdown, plain text, Docling-compatible, or MinerU-compatible export artifacts.

## Async Translation

```bash
docker run -d --name redis-local-ocr -p 6379:6379 redis
uv run celery -A local_deepl.api.tasks worker --loglevel=info --pool=solo
uv run local-deepl-server --port 8000
```

## Validation

```bash
uv run pytest
uv run pytest -m "not slow"
uv run pytest -m slow
uv run ruff check src tests
uv run ruff format src tests --check
uv run mypy src
```

Slow tests load Surya and may download its model on the first run.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for pipeline details, extension points, and staged document-intelligence notes.
