# Replay website (src/service/app.py): recorded demo runs only. No model, no GPU, no API call, no secret.
#
#   docker compose -f deploy/docker-compose.yml up -d --build      (build context = the repo root)
#
# The base image is multi-arch: built on the Oracle A1 VM it is linux/arm64, on a laptop linux/amd64. Nothing below
# depends on the architecture, and pip may only install wheels (no compiler in the image).
# Only the paths the replay site reads are copied; deploy/Dockerfile.dockerignore keeps everything else, .env and
# ops/ included, out of the build context.
FROM python:3.12-slim-bookworm

ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp \
    LIVE_MODE=off

RUN groupadd --gid "${APP_GID}" app \
 && useradd --uid "${APP_UID}" --gid app --no-create-home --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

COPY requirements-server.txt ./
RUN pip install --only-binary=:all: -r requirements-server.txt

COPY src/ src/
COPY lma_agent/ lma_agent/
COPY outputs/live/demo/ outputs/live/demo/
COPY docs/reports/final_results_v2.json docs/reports/
COPY report/final_submission.pdf report/
COPY PROGRESS.md ./

# numeric, so a runtime can verify that the container is not root
USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

# 0.0.0.0 inside the container only: the compose file publishes the port on the VM's loopback, and Caddy is the one
# public door. --no-proxy-headers: the app reads X-Forwarded-For itself (client_address in src/service/app.py).
CMD ["python", "-m", "uvicorn", "src.service.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
