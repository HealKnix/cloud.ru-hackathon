FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt pyproject.toml README.md ./
COPY mcp_instance.py server.py mcp_tools.json mcp-server-catalog.yaml env_options.json ./
COPY tools ./tools
COPY odata_tool ./odata_tool

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["python", "server.py"]
