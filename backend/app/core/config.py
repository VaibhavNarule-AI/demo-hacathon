import os
from pathlib import Path

DB_TYPE = os.environ.get("DB_TYPE", "sqlite")
DB_PATH = os.environ.get("DB_PATH", "./data/app.db")

Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

JWT_SECRET = os.environ.get("JWT_SECRET", "hackathon-demo-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 480  # 8h -- a SOC analyst's shift, not a 1h generic default

FLOW_LOG_PATH = os.environ.get("FLOW_LOG_PATH", "../logs/flow.log")

FRONTEND_DIST = os.environ.get("FRONTEND_DIST", "../frontend/dist")

# Both default to paths relative to backend/ (correct for local runs). In the
# container these are overridden to absolute paths backed by volume mounts,
# so /flow and /test-report keep reading the same host-visible logs/testcases
# directories docker-compose.yml mounts in.
TESTCASES_DIR = os.environ.get("TESTCASES_DIR", "../testcases")
