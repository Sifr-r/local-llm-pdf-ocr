from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from local_deepl.api.services.artifacts import (
    InvalidArtifactPayloadError,
    InvalidArtifactReferenceError,
    is_opaque_artifact_id,
)

DocumentExportFormat = Literal["json", "markdown", "text", "docling", "mineru"]
EXPORT_MEDIA_TYPES: dict[str, str] = {
    "json": "application/json",
    "markdown": "text/markdown; charset=utf-8",
    "text": "text/plain; charset=utf-8",
    "docling": "application/json",
    "mineru": "application/json",
}


def build_document_export(
    *,
    page_text: Mapping[str, list[str]],
    metadata: Mapping[str, Any] | None,
    export_format: DocumentExportFormat,
) -> str | dict[str, Any]:
    if export_format == "text":
        return _plain_text(page_text)
    if export_format == "markdown":
        return _markdown(page_text)
    if export_format == "json":
        return {"pages": _pages_json(page_text), "metadata": metadata}
    if export_format == "docling":
        return {
            "schema": "docling_compatible",
            "document": _pages_json(page_text),
            "metadata": metadata,
        }
    if export_format == "mineru":
        return {
            "schema": "mineru_compatible",
            "pages": _pages_json(page_text),
            "metadata": metadata,
        }
    raise InvalidArtifactPayloadError(f"Unsupported export format: {export_format}")


def write_document_export_atomic(
    payload: str | Mapping[str, Any],
    *,
    directory: str | os.PathLike[str] | None = None,
    artifact_id: str,
    export_format: DocumentExportFormat,
) -> str:
    if not is_opaque_artifact_id(artifact_id):
        raise InvalidArtifactReferenceError(
            "Artifact ID must be a 32-character hex string."
        )

    artifact_dir = Path(directory or tempfile.gettempdir()).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    suffix = (
        "md"
        if export_format == "markdown"
        else "txt"
        if export_format == "text"
        else "json"
    )
    target = artifact_dir / f"export_{artifact_id}.{suffix}"
    tmp_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=artifact_dir,
            prefix=f".export_{artifact_id}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp_path = tmp.name
            if isinstance(payload, str):
                tmp.write(payload)
            else:
                json.dump(payload, tmp, ensure_ascii=False, sort_keys=True)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_path, target)
    except Exception:
        if tmp_path is not None:
            Path(tmp_path).unlink(missing_ok=True)
        raise

    return str(target)


def load_json_file(path: str) -> Any:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def _pages_json(page_text: Mapping[str, list[str]]) -> list[dict[str, Any]]:
    return [
        {"page_index": int(page), "lines": list(lines), "text": "\n".join(lines)}
        for page, lines in sorted(page_text.items(), key=lambda item: int(item[0]))
    ]


def _plain_text(page_text: Mapping[str, list[str]]) -> str:
    return "\n\n".join(
        "\n".join(lines)
        for _page, lines in sorted(page_text.items(), key=lambda item: int(item[0]))
    )


def _markdown(page_text: Mapping[str, list[str]]) -> str:
    chunks = []
    for page, lines in sorted(page_text.items(), key=lambda item: int(item[0])):
        chunks.append(f"## Page {int(page) + 1}\n\n" + "\n".join(lines))
    return "\n\n".join(chunks).strip() + "\n"
