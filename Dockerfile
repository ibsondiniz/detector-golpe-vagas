FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY detector_golpe ./detector_golpe
COPY streamlit_app.py ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000 8501
CMD ["uvicorn", "detector_golpe.api:app", "--host", "0.0.0.0", "--port", "8000"]
