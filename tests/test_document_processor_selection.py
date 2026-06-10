from __future__ import annotations

import pytest
from pydantic import ValidationError

from local_deepl.api.schemas import ConfigUpdate, ProcessSettings
from local_deepl.core.processors import (
    LayoutEnrichmentProcessor,
    QualityAnalysisProcessor,
    ReadingOrderProcessor,
    SectionAnalysisProcessor,
    StructureAnalysisProcessor,
    TableExtractionProcessor,
    build_document_processors,
)


def _process_settings(**overrides):
    values = {
        "api_base": "http://localhost:1234/v1",
        "api_key": "local",
        "model": "local-model",
        "pipeline_mode": "hybrid",
        "dpi": 200,
        "concurrency": 1,
        "dense_mode": "auto",
        "dense_threshold": 60,
        "pages": None,
        "refine": True,
        "max_image_dim": 1024,
        "self_correction": False,
        "binarize": False,
        "dual_engine": False,
        "spellcheck": "none",
        "cross_page": False,
        "preprocess_pages": False,
        "orientation_detection": False,
        "deskew": False,
        "denoise": False,
        "normalize_contrast": False,
        "crop_cleanup": False,
        "quality_routing": False,
    }
    values.update(overrides)
    return ProcessSettings.model_validate(values)


def test_process_settings_accepts_comma_separated_document_processors():
    settings = _process_settings(
        document_processors=(
            "reading_order, quality_analysis, structure_analysis, section_analysis, "
            "layout_enrichment, table_extraction"
        )
    )

    assert [name.value for name in settings.document_processors] == [
        "reading_order",
        "quality_analysis",
        "structure_analysis",
        "section_analysis",
        "layout_enrichment",
        "table_extraction",
    ]


def test_config_update_accepts_document_processor_list():
    update = ConfigUpdate.model_validate({"document_processors": ["quality_analysis"]})

    assert [name.value for name in update.document_processors or []] == [
        "quality_analysis"
    ]


def test_process_settings_rejects_unknown_document_processor():
    with pytest.raises(ValidationError):
        _process_settings(document_processors="cloud_magic")


def test_build_document_processors_maps_allowed_names():
    processors = build_document_processors(
        [
            "reading_order",
            "quality_analysis",
            "structure_analysis",
            "section_analysis",
            "layout_enrichment",
            "table_extraction",
        ]
    )

    assert isinstance(processors[0], ReadingOrderProcessor)
    assert isinstance(processors[1], QualityAnalysisProcessor)
    assert isinstance(processors[2], StructureAnalysisProcessor)
    assert isinstance(processors[3], SectionAnalysisProcessor)
    assert isinstance(processors[4], LayoutEnrichmentProcessor)
    assert isinstance(processors[5], TableExtractionProcessor)
