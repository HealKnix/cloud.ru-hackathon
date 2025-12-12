from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.opensearch_config import OpenSearchConfig
    from scripts.services.document_indexer import DocumentIndexer
    from scripts.services.search_service import SearchService


_os_cfg: OpenSearchConfig | None = None
_search_service: SearchService | None = None
_document_indexer: DocumentIndexer | None = None


def _parse_float(value: str | None, default: float, min_value: float = 0.0) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
        if parsed < min_value:
            return default
        return parsed
    except (TypeError, ValueError):
        return default


def _parse_int(value: str | None, default: int, min_value: int = 1) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
        if parsed < min_value:
            return default
        return parsed
    except (TypeError, ValueError):
        return default


def get_services() -> tuple[OpenSearchConfig, SearchService, DocumentIndexer]:
    """Создать сервисы при первом вызове."""
    global _os_cfg, _search_service, _document_indexer
    if _os_cfg is None:
        from scripts.opensearch_config import OpenSearchConfig
        from scripts.services.document_indexer import DocumentIndexer
        from scripts.services.search_service import SearchService

        _os_cfg = OpenSearchConfig()
        _search_service = SearchService(os_cfg=_os_cfg)

        sim_threshold = _parse_float(os.getenv("SEMANTIC_SIM_THRESHOLD"), default=0.8, min_value=0.0)
        max_sent_per_chunk = _parse_int(os.getenv("MAX_SENT_PER_CHUNK"), default=8, min_value=1)
        _document_indexer = DocumentIndexer(
            os_cfg=_os_cfg,
            llm_service=_search_service.llm_service,
            sim_threshold=sim_threshold,
            max_sent_per_chunk=max_sent_per_chunk,
        )
    return _os_cfg, _search_service, _document_indexer
