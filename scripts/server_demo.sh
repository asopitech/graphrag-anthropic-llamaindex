#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
compose=(docker compose -p graphrag-search-demo -f docker/docker-compose.demo.yml)
case "${1:-run}" in
  run)
    "${compose[@]}" up --build -d --wait --wait-timeout 180
    PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}" python3 -m graphrag_anthropic_llamaindex.server_demo
    ;;
  verify)
    PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}" python3 -m graphrag_anthropic_llamaindex.server_demo --verify-only
    ;;
  restart)
    "${compose[@]}" restart alopexdb graphrag-server
    "${compose[@]}" up -d --wait --wait-timeout 180
    bash scripts/server_demo.sh verify
    ;;
  down) "${compose[@]}" down ;;
  logs) "${compose[@]}" logs --tail=100 ;;
  *) echo "Usage: bash scripts/server_demo.sh [run|verify|restart|down|logs]" >&2; exit 2 ;;
esac
