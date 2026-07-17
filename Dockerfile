# SOC Executive Dashboard — multi-stage build.
# Stage 1 builds the React frontend; stage 2 is the FastAPI backend, which
# serves the built frontend as static files from the same process/port (see
# 02_SOLUTION_ARCHITECTURE_TEMPLATE.md for the "one process, logically 4
# services" rationale).

FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS backend
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /frontend/dist ./frontend_dist

ENV FRONTEND_DIST=/app/frontend_dist \
    DB_PATH=/data/app.db \
    FLOW_LOG_PATH=/logs/flow.log \
    TESTCASES_DIR=/testcases

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
