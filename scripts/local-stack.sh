#!/bin/sh
# Runtime services stay in Docker; this wrapper only prepares private local config.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
STATE="$ROOT/.agent-kernel/docker-local"
ACTION=${1:-up}
if [ "$#" -gt 0 ]; then shift; fi
case "$ACTION" in
  init|up|build|stop|down|ps|logs|config|exec) ;;
  *) printf 'Usage: sh scripts/local-stack.sh {init|up|build|stop|down|ps|logs|config|exec}\n' >&2; exit 2 ;;
esac
if [ "$ACTION" = down ] && [ "$#" -ne 0 ]; then
  printf 'down preserves data; volume deletion is deliberately not supported here.\n' >&2
  exit 2
fi

umask 077
for path in "$ROOT/.agent-kernel" "$STATE" "$STATE/config.env" \
  "$STATE/monitoring-token" "$STATE/grafana-password" "$STATE/smtp-password"; do
  if [ -L "$path" ]; then
    printf 'Refusing symlink in private runtime configuration.\n' >&2
    exit 1
  fi
done
mkdir -p "$STATE"
chmod 700 "$STATE"
for name in monitoring-token grafana-password; do
  if [ ! -f "$STATE/$name" ]; then
    openssl rand -hex 32 > "$STATE/$name"
  fi
done
if [ ! -f "$STATE/smtp-password" ]; then : > "$STATE/smtp-password"; fi
if [ ! -f "$STATE/config.env" ]; then
  {
    printf 'AGENT_KERNEL_MONITORING_TOKEN=%s\n' "$(cat "$STATE/monitoring-token")"
    printf 'AGENT_KERNEL_GRAFANA_ADMIN_PASSWORD=%s\n' "$(cat "$STATE/grafana-password")"
  } > "$STATE/config.env"
fi
chmod 600 "$STATE/config.env" "$STATE/grafana-password"
# Non-root containers read bind-mounted files; the host parent remains owner-only.
chmod 644 "$STATE/monitoring-token" "$STATE/smtp-password"

compose() {
  # Ignore direnv/root .env and host provider keys. Docker client settings survive.
  env -i PATH="$PATH" HOME="$HOME" \
    DOCKER_CONFIG="${DOCKER_CONFIG:-$HOME/.docker}" \
    DOCKER_HOST="${DOCKER_HOST:-}" DOCKER_CONTEXT="${DOCKER_CONTEXT:-}" \
    AGENT_KERNEL_MONITORING_TOKEN_FILE="$STATE/monitoring-token" \
    AGENT_KERNEL_ALERTMANAGER_CONFIG_FILE="$ROOT/deploy/observability/alertmanager.local.json" \
    AGENT_KERNEL_SMTP_PASSWORD_FILE="$STATE/smtp-password" \
    docker compose --project-directory "$ROOT" --project-name agent-kernel-local \
      --env-file "$STATE/config.env" \
      -f "$ROOT/docker-compose.yml" \
      -f "$ROOT/deploy/observability/docker-compose.yml" \
      -f "$ROOT/deploy/observability/full-stack.compose.yml" \
      -f "$ROOT/deploy/observability/local-mail.compose.yml" \
      -f "$ROOT/deploy/local.compose.yml" --profile observability "$@"
}

case "$ACTION" in
  init)
    printf 'Private config: %s\nGrafana user: admin; password file: %s\n' \
      "$STATE/config.env" "$STATE/grafana-password"
    ;;
  up)
    compose config --quiet
    compose up --build --detach --wait --wait-timeout 240 "$@"
    compose ps
    printf 'All runtime services use Docker. See docs/docker-local.md for URLs and commands.\n'
    ;;
  config) compose config --quiet ;;
  logs) compose logs --tail 100 "$@" ;;
  down) compose down ;;
  *) compose "$ACTION" "$@" ;;
esac
