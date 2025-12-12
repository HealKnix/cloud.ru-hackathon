from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from thefuzz import fuzz, process


@dataclass
class Candidate:
    entity: str
    name: str
    synonym: str
    type: str
    score: int
    fields: List[str] = field(default_factory=list)
    field_types: Dict[str, str] = field(default_factory=dict)


def choose_candidates(index: List[Dict[str, Any]], query: str, limit: int = 10) -> List[Candidate]:
    """Pick top metadata candidates using fuzzy search."""
    if not index:
        return []

    choices = [(item.get("search_text", ""), item) for item in index]
    search_strings = [c[0] for c in choices if c[0]]
    search_map = {text: item for text, item in choices if text}

    matches = process.extract(
        query,
        search_strings,
        limit=limit,
        scorer=fuzz.WRatio,
    )

    candidates: List[Candidate] = []
    for text, score in matches:
        item = search_map.get(text)
        if not item:
            continue
        entity = f"{item.get('type')}_{item.get('name')}"
        candidates.append(
            Candidate(
                entity=entity,
                name=item.get("name", "") or "",
                synonym=item.get("synonym", "") or "",
                type=item.get("type", "") or "",
                score=score,
                fields=item.get("fields") or [],
                field_types=item.get("field_types") or {},
            )
        )

    return candidates
