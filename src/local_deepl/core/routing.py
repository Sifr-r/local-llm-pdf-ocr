from __future__ import annotations

from dataclasses import dataclass

from local_deepl.core.document import DocumentResult


@dataclass(frozen=True, slots=True)
class QualityRoutingOptions:
    enabled: bool = False


class QualityRoutingPolicy:
    """Deterministic quality-to-routing decision recorder."""

    def apply(
        self, document: DocumentResult, options: QualityRoutingOptions
    ) -> DocumentResult:
        if not options.enabled:
            return document

        for page in document.pages:
            quality = page.metadata.get("quality")
            findings = quality.get("findings", []) if isinstance(quality, dict) else []
            decisions: list[dict[str, object]] = []
            for finding in findings:
                if not isinstance(finding, dict):
                    continue
                code = finding.get("code")
                if code == "empty_page":
                    decisions.append(
                        {
                            "action": "retry_empty_page",
                            "status": "recommended",
                            "reason": code,
                        }
                    )
                elif code == "sparse_text":
                    decisions.append(
                        {
                            "action": "switch_dense_mode",
                            "status": "recommended",
                            "reason": code,
                        }
                    )
                elif code == "empty_large_block":
                    decisions.append(
                        {
                            "action": "retry_block_or_grounded",
                            "status": "recommended",
                            "reason": code,
                            "block_index": finding.get("block_index"),
                        }
                    )

            page.metadata["routing"] = {
                "enabled": True,
                "decision_count": len(decisions),
                "decisions": decisions,
            }
        return document
