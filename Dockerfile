FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY server ./server
RUN pip install --no-cache-dir .
RUN addgroup --system arena && adduser --system --ingroup arena arena \
    && mkdir -p /app/data && chown -R arena:arena /app
USER arena
EXPOSE 8080
CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8080"]

