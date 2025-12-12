import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class OpenSearchConfig:
    """
    Базовая конфигурация для подключения к OpenSearch.

    Переменные окружения:
      OPENSEARCH_HOST, OPENSEARCH_PORT, OPENSEARCH_USE_SSL
      OPENSEARCH_USER, OPENSEARCH_PASSWORD (опционально)
    """

    host: str = os.getenv("OPENSEARCH_HOST", "localhost")
    port: str = os.getenv("OPENSEARCH_PORT", "9200")
    user: Optional[str] = os.getenv("OPENSEARCH_USER") or None
    password: Optional[str] = os.getenv("OPENSEARCH_PASSWORD") or None
    use_ssl: bool = os.getenv("OPENSEARCH_USE_SSL", "false").lower() in ("true", "1", "yes")
    index_name: str = os.getenv("OPENSEARCH_INDEX", "makar_cloud_semantic")
    search_pipeline: Optional[str] = os.getenv("OPENSEARCH_SEARCH_PIPELINE")

    def __post_init__(self):
        if not self.host:
            raise ValueError("OPENSEARCH_HOST must be set in environment variables")
        if not self.port:
            raise ValueError("OPENSEARCH_PORT must be set in environment variables")
        try:
            self.port = int(self.port)
        except ValueError:
            raise ValueError(f"OPENSEARCH_PORT must be a valid integer, got: {self.port}")

    @property
    def url(self) -> str:
        """
        Полный URL до OpenSearch.
        Пример: http://localhost:9200 или https://localhost:9200
        """
        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.host}:{self.port}"


@dataclass
class YandexConfig:
    provider: str = os.getenv("LLM_PROVIDER", "yandex")
    api_key: Optional[str] = os.getenv("YANDEX_API_KEY")
    folder_id: Optional[str] = os.getenv("YANDEX_FOLDER_ID")
    model: str = os.getenv("YANDEX_LLM_MODEL", "yandexgpt-lite")
    embedding_model: str = os.getenv("YANDEX_EMBEDDING_MODEL", "text-search-doc")
    completion_url: str = os.getenv(
        "YANDEX_COMPLETION_URL",
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
    )

    def model_uri(self) -> str:
        if not self.folder_id:
            raise ValueError("YANDEX_FOLDER_ID is required")
        return f"gpt://{self.folder_id}/{self.model}"


