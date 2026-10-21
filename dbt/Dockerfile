# Small image with a pinned dbt toolchain for local runs and (later) CI/deploy jobs.
# Build from the repo root:  docker build -t dq-gate-dbt -f dbt/Dockerfile .
FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DBT_PROFILES_DIR=/workspace/dbt

COPY dbt/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

# The repo is mounted at /workspace at run time; nothing from it is baked into the image.
WORKDIR /workspace/dbt/dq_gate
ENTRYPOINT ["dbt"]
CMD ["--version"]
