from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from PIL import Image

from local_deepl.api.services.document_exports import (
    build_document_export,
    write_document_export_atomic,
)
from local_deepl.core.document import DocumentResult
from local_deepl.core.evaluation import evaluate_document
from local_deepl.core.preprocessing import (
    LocalPagePreprocessor,
    PagePreprocessingOptions,
)
from local_deepl.core.processors import (
    LayoutEnrichmentProcessor,
    TableExtractionProcessor,
)
from local_deepl.core.routing import QualityRoutingOptions, QualityRoutingPolicy


def _image_b64() -> str:
    image = Image.new("RGB", (40, 20), "white")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_local_page_preprocessor_is_default_off():
    images = {0: _image_b64()}

    result = LocalPagePreprocessor().preprocess(images, PagePreprocessingOptions())

    assert result.images == images
    assert result.metadata == {}


def test_local_page_preprocessor_records_enabled_operations():
    result = LocalPagePreprocessor().preprocess(
        {0: _image_b64()},
        PagePreprocessingOptions(enabled=True, normalize_contrast=True),
    )

    assert result.images[0]
    assert result.metadata[0]["operations"] == ["normalize_contrast"]


async def test_layout_enrichment_and_table_extraction_metadata():
    document = DocumentResult.from_pages_data(
        {
            0: [
                ([0.1, 0.02, 0.8, 0.08], "Report Header"),
                ([0.1, 0.2, 0.3, 0.24], "Name"),
                ([0.4, 0.2, 0.6, 0.24], "Total"),
                ([0.1, 0.3, 0.3, 0.34], "A"),
                ([0.4, 0.3, 0.6, 0.34], "$1"),
            ]
        }
    )

    document = await LayoutEnrichmentProcessor().process(document)
    document = await TableExtractionProcessor().process(document)

    assert document.pages[0].blocks[0].metadata["layout"]["role"] == "header"
    assert document.pages[0].metadata["layout"]["has_headers"] is True
    assert document.pages[0].metadata["tables"][0]["row_count"] == 2


def test_quality_routing_records_decisions():
    document = DocumentResult.from_pages_data({0: [([0.1, 0.1, 0.2, 0.2], "")]})
    document.pages[0].metadata["quality"] = {
        "findings": [{"code": "empty_page", "severity": "warning"}]
    }

    routed = QualityRoutingPolicy().apply(document, QualityRoutingOptions(enabled=True))

    assert (
        routed.pages[0].metadata["routing"]["decisions"][0]["action"]
        == "retry_empty_page"
    )


def test_document_exports_and_evaluation(tmp_path: Path):
    payload = build_document_export(
        page_text={"0": ["hello", "world"]},
        metadata={"summary": {"page_count": 1}},
        export_format="markdown",
    )
    artifact_path = write_document_export_atomic(
        payload,
        directory=tmp_path,
        artifact_id="a" * 32,
        export_format="markdown",
    )
    document = DocumentResult.from_pages_data(
        {0: [([0.1, 0.1, 0.2, 0.2], "hello world")]}
    )

    assert Path(artifact_path).read_text(encoding="utf-8").startswith("## Page 1")
    assert evaluate_document(document, expected_text="hello world").text_similarity == 1
    assert json.dumps(
        build_document_export(
            page_text={"0": ["hello"]}, metadata=None, export_format="json"
        )
    )
