FROM python:3.12-slim

RUN pip install uv --no-cache-dir

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --frozen

COPY src/ ./src/

EXPOSE 9000

CMD ["uv", "run", "fastmcp", "run", "src/main.py:mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "9000"]
