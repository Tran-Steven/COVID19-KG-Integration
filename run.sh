#!/usr/bin/env bash

set -euo pipefail

ROOT="$(
    cd "$(
        dirname "${BASH_SOURCE[0]}"
    )"
    pwd
)"

cd "$ROOT"

REFRESH_DATA=0
STOP=0

log() {
    printf "\n==> %s\n" "$1"
}

fail() {
    printf "\nERROR: %s\n" "$1" >&2
    exit 1
}

files_exist() {
    for path in "$@"; do
        if [[ ! -s "$path" ]]; then
            return 1
        fi
    done

    return 0
}

usage() {
    cat <<'EOF'
Usage:
  ./run.sh
  ./run.sh --refresh-data
  ./run.sh --stop
  ./run.sh --help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --refresh-data)
            REFRESH_DATA=1
            shift
            ;;
        --stop)
            STOP=1
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            fail "Unknown argument: $1"
            ;;
    esac
done

command -v docker >/dev/null 2>&1 \
    || fail "Docker is not installed."

docker compose version >/dev/null 2>&1 \
    || fail "Docker Compose is not available."

docker info >/dev/null 2>&1 \
    || fail "Docker is installed but is not running."

if [[ "$STOP" -eq 1 ]]; then
    log "Stopping services"
    docker compose down
    exit 0
fi

if [[ "$REFRESH_DATA" -eq 1 ]]; then
    log "Removing generated knowledge-graph data"

    for directory in \
        resources/monarch-kg \
        resources/monarch-covid \
        resources/chembl-covid \
        resources/who-covid-timeline \
        resources/who-covid-history \
        resources/who-covid-kg \
        resources/covid-kg
    do
        mkdir -p "$directory"

        find "$directory" \
            -mindepth 1 \
            ! -name ".gitkeep" \
            -delete
    done
fi

if files_exist \
    resources/covid-kg/nodes.tsv \
    resources/covid-kg/edges.tsv
then
    log "Using existing merged COVID-19 knowledge graph"
else
    command -v python3 >/dev/null 2>&1 \
        || fail "Python 3 is required to build the knowledge graph."

    python3 - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit(
        "Python 3.10 or newer is required."
    )
PY

    if [[ ! -x ".venv/bin/python" ]]; then
        log "Creating Python environment"
        python3 -m venv .venv
    fi

    PYTHON="$ROOT/.venv/bin/python"

    log "Installing data-build dependencies"

    "$PYTHON" -m pip install \
        --disable-pip-version-check \
        --quiet \
        -r requirements-data.txt

    if ! files_exist \
        resources/monarch-kg/nodes.tsv \
        resources/monarch-kg/edges.tsv
    then
        log "Downloading Monarch Knowledge Graph"
        "$PYTHON" scripts/download_kg.py
    else
        log "Monarch Knowledge Graph already exists"
    fi

    if ! files_exist \
        resources/monarch-covid/nodes.tsv \
        resources/monarch-covid/edges.tsv
    then
        log "Extracting Monarch COVID-19 subgraph"
        "$PYTHON" scripts/extract_covid_subgraph.py
    else
        log "Monarch COVID-19 subgraph already exists"
    fi

    if ! files_exist \
        resources/chembl-covid/nodes.tsv \
        resources/chembl-covid/edges.tsv
    then
        log "Building ChEMBL COVID-19 graph"
        "$PYTHON" scripts/download_chembl_covid.py
    else
        log "ChEMBL COVID-19 graph already exists"
    fi

    if ! files_exist \
        resources/who-covid-timeline/timeline.html \
        resources/who-covid-timeline/source.json
    then
        log "Downloading WHO COVID-19 timeline"
        "$PYTHON" scripts/download_who_covid_timeline.py
    else
        log "WHO COVID-19 timeline already exists"
    fi

    if ! files_exist \
        resources/who-covid-timeline/events.tsv \
        resources/who-covid-timeline/transform.json
    then
        log "Transforming WHO COVID-19 timeline"
        "$PYTHON" scripts/transform_who_covid_timeline.py
    else
        log "WHO timeline transformation already exists"
    fi

    if ! files_exist \
        resources/who-covid-history/nodes.tsv \
        resources/who-covid-history/edges.tsv
    then
        log "Building WHO historical graph"
        "$PYTHON" scripts/build_who_covid_history.py
    else
        log "WHO historical graph already exists"
    fi

    if ! files_exist \
        resources/who-covid-kg/nodes.tsv \
        resources/who-covid-kg/edges.tsv \
        resources/who-covid-kg/evidence.tsv
    then
        log "Building WHO COVID-19 graph"
        "$PYTHON" scripts/build_who_covid_kg.py
    else
        log "WHO COVID-19 graph already exists"
    fi

    log "Merging COVID-19 knowledge graph"
    "$PYTHON" scripts/merge_covid_kg.py

    files_exist \
        resources/covid-kg/nodes.tsv \
        resources/covid-kg/edges.tsv \
        || fail "Merged knowledge graph was not generated."
fi

log "Starting Neo4j"

docker compose up -d neo4j

log "Waiting for Neo4j"

NEO4J_READY=0

for _ in $(seq 1 60); do
    if docker compose exec -T neo4j \
        cypher-shell \
        -u neo4j \
        -p cvkgdemo \
        "RETURN 1;" \
        >/dev/null 2>&1
    then
        NEO4J_READY=1
        break
    fi

    sleep 2
done

if [[ "$NEO4J_READY" -ne 1 ]]; then
    fail "Neo4j did not become ready."
fi

docker compose stop api \
    >/dev/null 2>&1 \
    || true

log "Building API"

docker compose build api

log "Importing knowledge graph"

docker compose run --rm api \
    python import_kg.py \
    --nodes /data/covid-kg/nodes.tsv \
    --edges /data/covid-kg/edges.tsv \
    --clear

log "Starting API"

docker compose up -d api

log "Waiting for API"

API_READY=0

for _ in $(seq 1 90); do
    if curl \
        --silent \
        --fail \
        http://localhost:8000/health \
        >/dev/null 2>&1
    then
        API_READY=1
        break
    fi

    sleep 2
done

if [[ "$API_READY" -ne 1 ]]; then
    docker compose logs api
    fail "API did not become ready."
fi

printf "\n"
printf "COVID-19 KG Integration is running.\n\n"
printf "API:        http://localhost:8000\n"
printf "API docs:   http://localhost:8000/docs\n"
printf "Neo4j:      http://localhost:7474\n"
printf "\n"
printf "Chrome extension:\n"
printf "  1. Open chrome://extensions\n"
printf "  2. Enable Developer mode\n"
printf "  3. Select Load unpacked\n"
printf "  4. Select %s\n" "$ROOT"
printf "\n"
printf "Stop the system with:\n"
printf "  ./run.sh --stop\n"
printf "\n"