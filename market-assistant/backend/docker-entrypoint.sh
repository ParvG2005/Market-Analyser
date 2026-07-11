#!/usr/bin/env bash
# Phase 12 Task 2: dispatch to web / worker / all by $PROCESS_TYPE.
set -e

case "$PROCESS_TYPE" in
  web)
    alembic upgrade head
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
    ;;
  worker)
    exec arq app.worker.WorkerSettings
    ;;
  all)
    # Single-container hosts (e.g. Hugging Face Spaces) run web + worker together.
    # Migrate, start the worker in the background, then run the web server in the
    # foreground. If either exits, the container exits (host restarts it).
    alembic upgrade head
    arq app.worker.WorkerSettings &
    WORKER_PID=$!
    trap 'kill "$WORKER_PID" 2>/dev/null' EXIT INT TERM
    uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}" &
    WEB_PID=$!
    # Exit as soon as either process dies so the host's restart policy kicks in.
    wait -n "$WORKER_PID" "$WEB_PID"
    ;;
  *)
    echo "Unknown PROCESS_TYPE: ${PROCESS_TYPE}" >&2
    exit 1
    ;;
esac
