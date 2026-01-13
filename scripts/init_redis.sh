#!/usr/bin/env bash
set -x
set -eo pipefail

# if a redis container is running, print instructions to kill it and exit
RUNNING_CONTAINER=$(podman ps --filter 'name=redis' --format '{{.ID}}')
if [[ -n $RUNNING_CONTAINER ]]; then
  echo >&2 "there is a container already running, kill it with"
  echo >&2 " podman kill ${RUNNING_CONTAINER}"
  exit 1
fi

CACHE_PORT="${REDIS_PORT:=6379}"
LOG_LEVEL="--loglevel verbose"

# Launch Redis using Podman
CONTAINER_NAME="redis"
podman run --rm \
  --publish "${CACHE_PORT}":6379 \
  --detach \
  --name "${CONTAINER_NAME}" \
  redis:7 ${LOG_LEVEL}

>&2 echo "Redis is ready to go!"