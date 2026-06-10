"""Core OCR processing modules."""

from local_deepl.core.aligner import HybridAligner
from local_deepl.core.document import DocumentBlock, DocumentPage, DocumentResult
from local_deepl.core.evaluation import EvaluationMetrics, evaluate_document
from local_deepl.core.ocr import OCRProcessor
from local_deepl.core.pdf import PDFHandler
from local_deepl.core.preprocessing import (
    LocalPagePreprocessor,
    PagePreprocessingOptions,
    PagePreprocessingResult,
)
from local_deepl.core.processors import (
    LOCAL_DOCUMENT_PROCESSOR_NAMES,
    DocumentProcessor,
    DocumentProcessorRegistry,
    LayoutEnrichmentProcessor,
    QualityAnalysisProcessor,
    ReadingOrderProcessor,
    SectionAnalysisProcessor,
    StructureAnalysisProcessor,
    TableExtractionProcessor,
    build_document_processors,
    run_document_processors,
)
from local_deepl.core.routing import QualityRoutingOptions, QualityRoutingPolicy

__all__ = (
    "PDFHandler",
    "OCRProcessor",
    "HybridAligner",
    "DocumentBlock",
    "DocumentPage",
    "DocumentResult",
    "EvaluationMetrics",
    "evaluate_document",
    "LocalPagePreprocessor",
    "PagePreprocessingOptions",
    "PagePreprocessingResult",
    "DocumentProcessor",
    "DocumentProcessorRegistry",
    "LOCAL_DOCUMENT_PROCESSOR_NAMES",
    "LayoutEnrichmentProcessor",
    "QualityAnalysisProcessor",
    "ReadingOrderProcessor",
    "SectionAnalysisProcessor",
    "StructureAnalysisProcessor",
    "TableExtractionProcessor",
    "build_document_processors",
    "run_document_processors",
    "QualityRoutingOptions",
    "QualityRoutingPolicy",
)
