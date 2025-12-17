#!/usr/bin/env bash
set -x
set -eo pipefail

if ! [ -x "$(command -v sqlx)" ]; then
  echo >&2 "Error: sqlx is not installed"
  echo >&2 "Use:"
  echo >&2"     cargo install --version='~0.8' sqlx-cli --no-default-features --features rustls,postgres"
  echo >&2 "to install it."
  exit 1
fi

DB_PORT="${POSTGRES_PORT:=5432}"
SUPERUSER="${SUPERUSER:=postgres}"
SUPERUSER_PWD="${SUPERUSER_PWD:=password}"

APP_USER="${APP_USER:=app}"
APP_USER_PWD="${APP_USER_PWD:=secret}"
APP_DB_NAME="${APP_DB_NAME:=newsletter}"

if [[ -z "${SKIP_PODMAN}" ]]
then
  # Launch postgres using Podman
  CONTAINER_NAME="postgres"
  podman run \
    --rm \
    --env POSTGRES_USER=${SUPERUSER} \
    --env POSTGRES_PASSWORD=${SUPERUSER_PWD} \
    --publish "${DB_PORT}":5432 \
    --detach \
    --name "${CONTAINER_NAME}" \
    postgres -N 1000

  until [ "$(podman inspect -f "{{.State.Status}}" ${CONTAINER_NAME})" == "running" ]; do
    >&2 echo "Container is still starting - sleeping"
    sleep 2
  done

  # Then check if Postgres is actually ready to accept connections
  until podman exec -it "${CONTAINER_NAME}" pg_isready -U "${SUPERUSER}" > /dev/null 2>&1; do
    >&2 echo "Postgres is still unavailable - sleeping"
    sleep 2
  done

  >&2 echo "Postgres is up and running on port ${DB_PORT}!"

  CREATE_QUERY="CREATE USER ${APP_USER} WITH PASSWORD '${APP_USER_PWD}';"
  podman exec -it "${CONTAINER_NAME}" psql -U "${SUPERUSER}" -c "${CREATE_QUERY}"

  GRANT_QUERY="ALTER USER ${APP_USER} CREATEDB;"
  podman exec -it "${CONTAINER_NAME}" psql -U "${SUPERUSER}" -c "${GRANT_QUERY}"
fi

DATABASE_URL=postgres://${APP_USER}:${APP_USER_PWD}@localhost:${DB_PORT}/${APP_DB_NAME}
export DATABASE_URL
sqlx database create
sqlx migrate run

>&2 echo "Postgres has been migrated, ready to go!"