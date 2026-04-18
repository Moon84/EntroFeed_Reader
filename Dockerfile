FROM node:22-slim AS frontend-build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS backend

RUN pip install uv
WORKDIR /app
COPY pyproject.toml .
RUN uv venv
RUN uv pip install .

FROM nikolaik/python-nodejs:python3.11-nodejs22-slim AS web

LABEL org.opencontainers.image.title="EntroFeed"
LABEL org.opencontainers.image.authors="wuyuezhang1984@gmail.com"
LABEL org.opencontainers.image.source="https://github.com/Moon84/EntroFeed_Reader"
LABEL org.opencontainers.image.url="https://github.com/Moon84/EntroFeed_Reader"
LABEL org.opencontainers.image.description="An extensible self-hosted AI-enabled RSS reader with a focus on notifications and support for theming"
LABEL org.opencontainers.image.licenses=AGPL-3.0

WORKDIR /app
ENV IS_DOCKER=True

COPY --from=backend /app/.venv /app/.venv
COPY src ./src/
COPY --from=frontend-build /app/dist ./frontend/dist
ENV PATH /app/.venv/bin:$PATH
RUN playwright install --with-deps chromium

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "80"]
HEALTHCHECK --interval=10s --timeout=10s --retries=5 CMD curl --include --request GET "http://localhost:80/health" || exit 1

EXPOSE 80
