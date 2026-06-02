FROM python:3.12-slim

RUN pip install uv --no-cache-dir

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --frozen

COPY langgraph.json ./
COPY src/ ./src/
COPY main.py ./

EXPOSE 2024

CMD ["uv", "run", "langgraph", "dev", "--host", "0.0.0.0", "--port", "2024", "--no-browser"]
