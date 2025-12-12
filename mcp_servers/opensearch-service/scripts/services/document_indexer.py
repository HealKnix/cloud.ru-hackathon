"""Сервис для индексации документов в OpenSearch с семантическим чанкированием."""

from __future__ import annotations

import re
import os
from typing import Any, Dict, List

import numpy as np

from scripts.services.cloudru_service import CloudRuService
from scripts.services.opensearch_service import OpenSearchService
from scripts.opensearch_config import OpenSearchConfig


SENT_SPLIT_REGEX = re.compile(r"([.!?]+)\s+")


class DocumentIndexer:
    """Сервис для индексации документов с семантическим чанкированием."""

    def __init__(
        self,
        os_cfg: OpenSearchConfig | None = None,
        llm_service: CloudRuService | None = None,
        sim_threshold: float = 0.8,
        max_sent_per_chunk: int = 8,
    ) -> None:
        self.os_cfg = os_cfg or OpenSearchConfig()
        self.llm_service = llm_service or CloudRuService()
        self.yandex_service = self.llm_service
        self.opensearch_service = OpenSearchService(self.os_cfg)
        self.sim_threshold = sim_threshold
        self.max_sent_per_chunk = max_sent_per_chunk

    def split_into_sentences(self, text: str) -> List[str]:
        """Разбить текст на предложения."""
        text = text.strip()
        if not text:
            return []
        parts = SENT_SPLIT_REGEX.split(text)
        sentences: List[str] = []
        buf = ""
        for part in parts:
            if not part:
                continue
            if SENT_SPLIT_REGEX.match(part):
                buf += part + " "
                sentences.append(buf.strip())
                buf = ""
            else:
                buf += part + " "
        if buf.strip():
            sentences.append(buf.strip())
        return [s for s in sentences if s.strip()]

    async def get_embedding(self, text: str) -> List[float]:
        """Получить эмбеддинг текста."""
        return await self.llm_service.get_embedding(text)

    async def build_semantic_chunks(
        self, content: str, source_name: str
    ) -> List[Dict[str, Any]]:
        """Построить семантические чанки из текста."""
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        sentences: List[str] = []
        for p in paragraphs:
            sentences.extend(self.split_into_sentences(p))

        if not sentences:
            return []

        # Получаем эмбеддинги для всех предложений
        sent_embs = []
        for s in sentences:
            emb = await self.get_embedding(s)
            sent_embs.append(np.array(emb, dtype="float32"))
        sent_embs = np.stack(sent_embs, axis=0)

        # Группируем предложения в чанки по косинусному сходству
        chunk_spans: List[tuple] = []

        cur_indices: List[int] = [0]
        cur_vec = sent_embs[0].copy()

        for i in range(1, len(sentences)):
            vec = sent_embs[i]
            num = float(np.dot(cur_vec, vec))
            den = float(np.linalg.norm(cur_vec) * np.linalg.norm(vec))
            sim = num / den if den != 0.0 else 0.0

            if sim >= self.sim_threshold and len(cur_indices) < self.max_sent_per_chunk:
                cur_indices.append(i)
                cur_vec = sent_embs[cur_indices].mean(axis=0)
            else:
                start, end = cur_indices[0], cur_indices[-1]
                chunk_spans.append((start, end))
                cur_indices = [i]
                cur_vec = vec.copy()

        if cur_indices:
            start, end = cur_indices[0], cur_indices[-1]
            chunk_spans.append((start, end))

        # Объединяем маленькие чанки
        merged_spans: List[tuple] = []
        i = 0
        while i < len(chunk_spans):
            start, end = chunk_spans[i]
            sent_count = end - start + 1

            if sent_count < 3 and i + 1 < len(chunk_spans):
                next_start, next_end = chunk_spans[i + 1]
                merged_spans.append((start, next_end))
                i += 2
            else:
                merged_spans.append((start, end))
                i += 1

        if len(merged_spans) >= 2:
            last_start, last_end = merged_spans[-1]
            if (last_end - last_start + 1) < 3:
                prev_start, prev_end = merged_spans[-2]
                merged_spans[-2] = (prev_start, last_end)
                merged_spans.pop()

        # Создаем финальные чанки
        chunks: List[Dict[str, Any]] = []
        for start, end in merged_spans:
            idxs = list(range(start, end + 1))
            text = " ".join(sentences[j] for j in idxs)
            vec = sent_embs[idxs].mean(axis=0)
            chunk_id = f"{source_name}::s{start}-{end}"
            chunks.append(
                {
                    "text": text,
                    "source": source_name,
                    "chunk_id": chunk_id,
                    "text_vector": vec.tolist(),
                }
            )

        return chunks

    async def index_document(
        self, content: str, source_name: str, index_name: str | None = None
    ) -> Dict[str, Any]:
        """Индексировать документ в OpenSearch."""
        target_index = index_name or self.os_cfg.index_name

        # Создаем чанки
        chunks = await self.build_semantic_chunks(content, source_name)

        if not chunks:
            return {"indexed": 0, "chunks": 0, "message": "No chunks created"}

        # Индексируем чанки батчами
        client = self.opensearch_service.client
        indexed = 0

        for chunk in chunks:
            try:
                client.index(index=target_index, body=chunk)
                indexed += 1
            except Exception as e:
                print(f"Error indexing chunk {chunk.get('chunk_id')}: {e}")

        return {
            "indexed": indexed,
            "chunks": len(chunks),
            "source": source_name,
            "index": target_index,
        }

    def create_index_if_not_exists(self, index_name: str | None = None) -> None:
        """Создать индекс если он не существует."""
        target_index = index_name or self.os_cfg.index_name
        client = self.opensearch_service.client

        if client.indices.exists(index=target_index):
            return

        # Конфигурация индекса из ноутбука
        embedding_dim = int(os.getenv("EMBEDDING_DIM", "1024"))
        index_body: Dict[str, Any] = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "knn": True,
                    "knn.algo_param.ef_search": 100,
                    "similarity": {
                        "custom_similarity": {
                            "type": "BM25",
                            "k1": 1.2,
                            "b": 0.75,
                            "discount_overlaps": "true",
                        }
                    },
                    "analysis": {
                        "filter": {
                            "russian_stemmer": {"type": "stemmer", "language": "russian"},
                            "unique_pos": {"type": "unique", "only_on_same_position": False},
                            "my_multiplexer": {
                                "type": "multiplexer",
                                "filters": [
                                    "keyword_repeat",
                                    "russian_stemmer",
                                    "remove_duplicates",
                                ],
                            },
                        },
                        "analyzer": {
                            "search_text_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "my_multiplexer", "unique_pos"],
                                "char_filter": ["e_mapping"],
                            },
                            "text_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "russian_stemmer"],
                                "char_filter": ["e_mapping"],
                            },
                            "exact_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase"],
                                "char_filter": ["e_mapping"],
                            },
                        },
                        "char_filter": {
                            "e_mapping": {"type": "mapping", "mappings": ["e => ё"]},
                        },
                    },
                }
            },
            "mappings": {
                "properties": {
                    "text": {
                        "type": "text",
                        "analyzer": "text_analyzer",
                        "similarity": "BM25",
                    },
                    "source": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "text_vector": {
                        "type": "knn_vector",
                        "dimension": embedding_dim,
                        "method": {
                            "name": "hnsw",
                            # FAISS в OpenSearch 2.11.1 не поддерживает cosinesimil.
                            # Используем L2; для косинуса нормализуйте вектора перед записью.
                            "space_type": "l2",
                            "engine": "faiss",
                            "parameters": {"ef_construction": 512, "m": 64},
                        },
                    },
                }
            },
        }

        client.indices.create(index=target_index, body=index_body)
        print(f"Created index: {target_index}")
