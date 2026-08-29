FROM ghcr.io/pnpm/pnpm:11 AS pnpm

FROM node:24-slim AS web

WORKDIR /web
RUN apt-get update \
    && apt-get install --no-install-recommends -y libatomic1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=pnpm /opt/pnpm /opt/pnpm
ENV PNPM_HOME=/pnpm PATH=/opt/pnpm:$PATH
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web ./
COPY packages /packages
RUN pnpm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY server ./server
COPY --from=web /web/dist ./apps/web/dist
RUN pip install --no-cache-dir .
RUN addgroup --system arena && adduser --system --ingroup arena arena \
    && mkdir -p /app/data && chown -R arena:arena /app
USER arena
EXPOSE 8080
CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8080"]

