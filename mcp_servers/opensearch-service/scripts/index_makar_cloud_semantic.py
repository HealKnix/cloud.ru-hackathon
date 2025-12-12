#!/usr/bin/env python3
"""
Индексация документов в OpenSearch: семантическое чанкирование + embeddings Cloud.ru.

Это «скриптовая» версия логики из ноутбука индексации, но для индекса
`makar_cloud_semantic`.

Переменные окружения (из .env):
  - MD_DIR: путь к директории с документами (.md/.txt)
  - INDEX_NAME: имя индекса (по умолчанию makar_cloud_semantic)
  - OPENSEARCH_HOST, OPENSEARCH_PORT, OPENSEARCH_USER, OPENSEARCH_PASSWORD
  - CLOUDRU_API_KEY (или API_KEY), CLOUDRU_EMBEDDING_MODEL, CLOUDRU_BASE_URL, EMBEDDING_DIM
  - SEMANTIC_SIM_THRESHOLD, MAX_SENT_PER_CHUNK
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

from scripts.opensearch_config import OpenSearchConfig
from scripts.services.document_indexer import DocumentIndexer
from scripts.services.cloudru_service import CloudRuService


def _iter_doc_files(md_dir: Path) -> Iterable[Path]:
    for p in md_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() in {".md", ".txt"}:
            yield p


async def _run(md_dir: Path, index_name: str) -> None:
    os_cfg = OpenSearchConfig()

    sim_threshold = float(os.getenv("SEMANTIC_SIM_THRESHOLD", "0.8"))
    max_sent_per_chunk = int(os.getenv("MAX_SENT_PER_CHUNK", "8"))

    cloudru = CloudRuService()
    if not cloudru.enabled:
        raise RuntimeError(
            "Cloud.ru API не настроен. Проверьте CLOUDRU_API_KEY (или API_KEY) в .env",
        )

    indexer = DocumentIndexer(
        os_cfg=os_cfg,
        llm_service=cloudru,
        sim_threshold=sim_threshold,
        max_sent_per_chunk=max_sent_per_chunk,
    )

    indexer.create_index_if_not_exists(index_name=index_name)

    files = list(_iter_doc_files(md_dir))
    if not files:
        print(f"MD_DIR пуст или не содержит .md/.txt: {md_dir}")
        return

    total_chunks = 0
    total_indexed = 0

    print(f"OpenSearch index: {index_name}")
    print(f"Docs dir: {md_dir}")
    print(f"Files found: {len(files)}")
    print(f"Semantic threshold: {sim_threshold}, max sent/chunk: {max_sent_per_chunk}")

    for i, fp in enumerate(files, 1):
        rel_name = fp.relative_to(md_dir).as_posix()
        content = fp.read_text(encoding="utf-8", errors="ignore")
        res = await indexer.index_document(
            content=content,
            source_name=rel_name,
            index_name=index_name,
        )
        total_chunks += int(res.get("chunks", 0))
        total_indexed += int(res.get("indexed", 0))
        print(f"[{i}/{len(files)}] {rel_name}: chunks={res.get('chunks')} indexed={res.get('indexed')}")

    print("Done.")
    print(f"Total chunks: {total_chunks}")
    print(f"Total indexed: {total_indexed}")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Index documents into OpenSearch (makar_cloud_semantic).")
    parser.add_argument(
        "--md-dir",
        default=os.getenv("MD_DIR", ""),
        help="Path to directory with documents (.md/.txt). Defaults to env MD_DIR.",
    )
    parser.add_argument(
        "--index-name",
        default=os.getenv("INDEX_NAME") or os.getenv("OPENSEARCH_INDEX") or "makar_cloud_semantic",
        help="OpenSearch index name. Defaults to env INDEX_NAME/OPENSEARCH_INDEX or makar_cloud_semantic.",
    )
    args = parser.parse_args()

    if not args.md_dir:
        raise SystemExit("MD_DIR не задан. Укажите --md-dir или переменную окружения MD_DIR.")

    md_dir = Path(args.md_dir).expanduser()
    if not md_dir.exists():
        raise SystemExit(f"MD_DIR не существует: {md_dir}")

    asyncio.run(_run(md_dir=md_dir, index_name=args.index_name))


if __name__ == "__main__":
    main()

