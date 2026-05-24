FROM python:3.13-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini ./
ENV PYTHONPATH=/app/src
CMD [".venv/bin/python", "src/main.py"]
