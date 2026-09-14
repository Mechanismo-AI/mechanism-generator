"""OMTS validation is independent of solver capability and physical feasibility."""

from .validation import DocumentError, load_document, validate_document

__all__ = ["DocumentError", "load_document", "validate_document"]
