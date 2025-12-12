## Обзор

## MCP сервер

MCP сервер реализован на FastMCP (stdio по умолчанию).

- Точка входа: `server.py` (совместимый wrapper: `mcp_server.py`)
- Инструменты: `upload_document`, `search_documents`, `ask_question`
- Документация: `MCP_GUIDE.md`, `DOCS.md`
- Описание окружения/инструментов: `env_options.json`, `mcp_tools.json`

Этот проект — RAG‑система для семантического поиска и индексации документов с использованием OpenSearch и Cloud.ru Foundation Models.

Стек:

- **OpenSearch** — хранилище базы знаний и гибридный поиск (BM25 + kNN + ColBERT‑реранкинг).
- **Cloud.ru Foundation Models** — эмбеддинги и генерация текста (OpenAI‑совместимое API).
- **FastAPI** — HTTP‑API с несколькими эндпоинтами (`/search`, `/rag/answer`, `/llm/answer`).
- **Jupyter Notebooks** — для индексации и оценки качества поиска.

Ниже — пошаговая инструкция, как:

1. Настроить окружение и переменные.
2. Проиндексировать базу знаний в OpenSearch.
3. Запустить API на порту `8000`.
4. Делать запросы ко всем эндпоинтам.

---

## 1. Предварительные условия

- **Python 3.8+** с установленными пакетами (см. раздел 1.1).
- **OpenSearch** должен быть запущен и доступен по HTTPS.
- **Файлы проекта**:
  - `opensearch_index_makar_cloud_semantic.ipynb` — ноутбук для семантической индексации.
  - `opensearch_eval_colbert.ipynb` — ноутбук для оценки качества поиска.
  - Markdown документы для индексации (указываются в ноутбуке).

### 1.1. Установка зависимостей

Установите необходимые пакеты:

```bash
pip install fastapi uvicorn[standard] opensearch-py httpx pandas scikit-learn pydantic python-dotenv numpy tqdm requests
```

Для работы с ноутбуками также потребуется Jupyter:

```bash
pip install jupyter notebook
```

---

## 2. Переменные окружения

Проект использует переменные окружения для подключения к OpenSearch и Cloud.ru API. Все секретные данные должны храниться в файле `.env`.

### 2.1. Настройка переменных окружения

Создайте файл `.env` в корне проекта на основе примера `env.example`:

```bash
cp env.example .env
```

Затем отредактируйте `.env` и укажите ваши реальные значения:

```bash
# OpenSearch Configuration
OPENSEARCH_URL=https://localhost:9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=your_actual_password

# Alternative OpenSearch Configuration (for eval notebook)
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200

# OpenSearch Index (optional, has default)
OPENSEARCH_INDEX=makar_cloud_semantic

# Cloud.ru Foundation Models (OpenAI-compatible) Configuration
# Укажите один из ключей (предпочтительно CLOUDRU_API_KEY; поддерживается и API_KEY)
CLOUDRU_API_KEY=your_actual_api_key
# API_KEY=your_actual_api_key

CLOUDRU_BASE_URL=https://foundation-models.api.cloud.ru/v1
CLOUDRU_EMBEDDING_MODEL=BAAI/bge-m3
CLOUDRU_CHAT_MODEL=zai-org/GLM-4.6
CLOUDRU_TEMPERATURE=0.5
EMBEDDING_DIM=1024

# Semantic Chunking Configuration (optional)
SEMANTIC_SIM_THRESHOLD=0.8
MAX_SENT_PER_CHUNK=8
```

**Важно:**

- Файл `.env` не должен попадать в систему контроля версий (уже добавлен в `.gitignore`).
- Все секретные данные (пароли, API ключи) должны быть только в `.env`, не в коде.

### 2.2. Загрузка переменных окружения

Ноутбуки автоматически загружают переменные из `.env` файла через `python-dotenv`:

```python
from dotenv import load_dotenv
load_dotenv()
```

Эта строка уже добавлена в начало всех ноутбуков.

---

## 3. Индексация базы знаний в OpenSearch

Индексация реализована в ноутбуке `opensearch_index_makar_cloud_semantic.ipynb`.

### 3.1. Описание ноутбука

Ноутбук выполняет:

- Семантическое чанкирование markdown‑документов:
  - Разбивает документы на предложения.
  - Объединяет предложения в чанки по косинусному сходству эмбеддингов.
  - Использует порог сходства (`SEMANTIC_SIM_THRESHOLD`) и максимальное количество предложений в чанке (`MAX_SENT_PER_CHUNK`).
- Создание индекса `makar_cloud_semantic`:
  - Кастомные русские анализаторы.
- Поле `knn_vector` для эмбеддингов (размерность `EMBEDDING_DIM`, HNSW+FAISS).
  - BM25 similarity для текстового поиска.
- Получение эмбеддингов через Cloud.ru API.
- Индексация всех чанков в OpenSearch.

### 3.2. Как запустить индексацию

1. Убедитесь, что OpenSearch запущен и переменные окружения настроены (см. раздел 2).
2. Откройте ноутбук:

   ```bash
   jupyter notebook opensearch_index_makar_cloud_semantic.ipynb
   ```

3. В интерфейсе Jupyter:
   - Выберите ядро с установленными зависимостями.
   - Последовательно выполните все ячейки сверху вниз:
     - Загрузка переменных окружения.
     - Создание клиента OpenSearch.
     - Создание индекса `makar_cloud_semantic`.
     - Семантическое чанкирование документов.
     - Получение эмбеддингов через Cloud.ru API.
     - Батч‑индексация документов в OpenSearch.
     - (Опционально) Генерация синтетических тестовых запросов.

4. В конце вы должны увидеть сообщения о количестве проиндексированных чанков.

### 3.3. Структура индекса

Индекс создаётся с параметрами:

- **settings.index**:
  - `number_of_shards: 1`
  - `number_of_replicas: 0`
  - `knn: true`
  - `knn.algo_param.ef_search: 100`
  - `similarity.custom_similarity: { type: "BM25", k1: 1.2, b: 0.75 }`
- **analysis**:
  - Фильтры: `russian_stemmer`, `unique_pos`, `my_multiplexer`
  - Анализаторы: `text_analyzer`, `search_text_analyzer`, `ru_international_translit_analyzer`, `exact_analyzer`
- **mappings.properties**:
  - `text: { type: "text", analyzer: "text_analyzer", similarity: "BM25" }`
  - `source: { type: "keyword" }`
  - `chunk_id: { type: "keyword" }`
  - `text_vector: { type: "knn_vector", dimension: 256, method: { name: "hnsw", space_type: "l2", engine: "faiss" } }` _(для косинуса нормализуйте вектора перед записью)_

---

## 4. Оценка качества поиска

Ноутбук `opensearch_eval_colbert.ipynb` позволяет оценить качество поиска:

- Берёт тестовые запросы из JSON файлов (`test_queries_bank_docs.json`, `test_queries_semantic.json`).
- Для каждого запроса вызывает HTTP‑эндпоинт `POST http://127.0.0.1:8000/search`.
- Сортирует документы по полю `_colbert_score`.
- Считает метрики `precision@k`, `recall@k` и `nDCG@k` на уровне чанка и файла.

### 4.1. Запуск оценки

1. Убедитесь, что API сервис запущен (см. раздел 5).
2. Откройте ноутбук:

   ```bash
   jupyter notebook opensearch_eval_colbert.ipynb
   ```

3. Выполните ячейки для оценки качества поиска.

---

## 5. Запуск FastAPI‑сервиса

Приложение находится в `scripts/api/main.py` и поднимается через `uvicorn`.

### 5.1. Команда запуска

Убедитесь, что переменные окружения загружены из `.env` файла (или установлены в системе):

```bash
uvicorn scripts.api.main:app --host 0.0.0.0 --port 8000
```

Или с указанием конкретного интерпретатора:

```bash
python -m uvicorn scripts.api.main:app --host 0.0.0.0 --port 8000
```

После старта API будет доступен по адресу:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## 6. Форматы запросов ко всем эндпоинтам

Все эндпоинты — `POST` с JSON‑телом.

### 6.1. `/search` — гибридный поиск по OpenSearch

- **URL**: `POST http://127.0.0.1:8000/search`
- **Тело запроса** (`SearchRequest`):

```json
{
  "query": "ваш поисковый запрос",
  "size": 10,
  "index_name": "makar_cloud_semantic",
  "use_hyde": false,
  "use_colbert": true
}
```

- **Ответ** (`SearchResponse`):

```json
{
  "query": "ваш поисковый запрос",
  "total_documents": 10,
  "documents": [
    {
      "text": "текст найденного фрагмента",
      "source": "имя_файла.md",
      "chunk_id": "имя_файла.md::s0-5",
      "_score": 6.29,
      "_colbert_score": 0.83
    }
  ]
}
```

### 6.2. `/rag/answer` — RAG‑ответ (поиск + генерация)

- **URL**: `POST http://127.0.0.1:8000/rag/answer`
- **Тело запроса** (`QARequest`):

```json
{
  "query": "Как работает система?",
  "size": 5,
  "index_name": "makar_cloud_semantic",
  "use_hyde": false,
  "use_colbert": true
}
```

- **Ответ** (`QAResponse`):

```json
{
  "query": "Как работает система?",
  "answer": "сгенерированный по найденным фрагментам текст",
  "total_documents": 5,
  "documents": [
    {
      "text": "...",
      "source": "...",
      "chunk_id": "...",
      "_score": 6.29
    }
  ]
}
```

### 6.3. `/llm/answer` — прямой запрос к LLM

- **URL**: `POST http://127.0.0.1:8000/llm/answer`
- **Тело запроса** (`LLMRequest`):

```json
{
  "query": "Объясни кратко концепцию RAG",
  "max_tokens": 300,
  "index_name": null
}
```

Если `index_name` указан, выполняется RAG‑режим (поиск + генерация). Если `null` — прямой вызов LLM без контекста.

- **Ответ** (`LLMResponse`):

```json
{
  "query": "Объясни кратко концепцию RAG",
  "answer": "ответ от LLM"
}
```

---

## 7. Примеры запросов через `curl`

### 7.1. Пример `/search`

```bash
curl -X POST "http://127.0.0.1:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ваш поисковый запрос",
    "size": 5,
    "index_name": "makar_cloud_semantic",
    "use_hyde": false,
    "use_colbert": true
  }'
```

### 7.2. Пример `/rag/answer`

```bash
curl -X POST "http://127.0.0.1:8000/rag/answer" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Как работает система?",
    "size": 5,
    "index_name": "makar_cloud_semantic",
    "use_hyde": false,
    "use_colbert": true
  }'
```

---

## 8. Структура проекта

```
.
├── scripts/
│   ├── api/
│   │   ├── main.py              # FastAPI приложение
│   │   └── schemas.py            # Pydantic схемы
│   ├── services/
│   │   ├── opensearch_service.py # Сервис для работы с OpenSearch
│   │   ├── search_service.py     # Основной сервис поиска
│   │   ├── cloudru_service.py    # Cloud.ru LLM / embeddings (OpenAI-совместимое API)
│   │   ├── colbert_reranker.py   # ColBERT реранкер
│   │   └── hyde_service.py        # HyDE сервис
│   └── opensearch_config.py      # Конфигурация OpenSearch
├── opensearch_index_makar_cloud_semantic.ipynb  # Ноутбук для индексации
├── opensearch_eval_colbert.ipynb                # Ноутбук для оценки
├── env.example                                   # Пример .env файла
├── .env                                          # Ваши секреты (не в Git)
└── README.md                                     # Этот файл
```

---

## 9. Безопасность

- Все секретные данные (API ключи, пароли) хранятся только в файле `.env`.
- Файл `.env` добавлен в `.gitignore` и не попадает в систему контроля версий.
- В коде нет хардкоженных секретов.
- Ноутбуки автоматически загружают переменные из `.env` через `python-dotenv`.

---

## 10. Дополнительная информация

- Для экспериментов с поиском используйте ноутбук `opensearch_eval_colbert.ipynb`.
- Все параметры поиска (HyDE, ColBERT) можно включать/выключать через параметры запросов.
- Индекс можно пересоздать, запустив ноутбук индексации заново (старый индекс будет удалён).
