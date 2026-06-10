from __future__ import annotations

from typing import Any


def build_workflow_summary(settings: Any) -> dict[str, object]:
    stages = ["upload", "convert"]
    if getattr(settings, "preprocess_pages", False):
        stages.append("preprocess")
    if getattr(settings, "pipeline_mode", "hybrid") == "grounded":
        stages.append("grounded_ocr")
    else:
        stages.extend(["detect", "ocr"])
        if getattr(settings, "refine", False):
            stages.append("refine")
    if getattr(settings, "spellcheck", "none") != "none":
        stages.append("spellcheck")
    if getattr(settings, "cross_page", False):
        stages.append("cross_page")
    if getattr(settings, "document_processors", []):
        stages.append("document_processors")
    if getattr(settings, "quality_routing", False):
        stages.append("quality_routing")
    stages.extend(["metadata_artifacts", "embed"])
    return {
        "mode": str(getattr(settings, "pipeline_mode", "hybrid")),
        "stages": stages,
        "document_processors": [
            str(processor) for processor in getattr(settings, "document_processors", [])
        ],
    }
