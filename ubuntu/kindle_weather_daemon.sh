#!/usr/bin/env bash
set -euo pipefail

LAT="43.6532"
LON="-79.5657"
TZ="America%2FToronto"
LOCATION_LABEL="Etobicoke"

# Re-render every 3 hours; Kindle pulls via SCP on its own schedule
RENDER_INTERVAL=$((3 * 60 * 60))

SCRIPT_DIR="$(dirname "$0")"
OUT_PNG="${SCRIPT_DIR}/weather.png"

URL="https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,relative_humidity_2m&hourly=temperature_2m,precipitation_probability,precipitation,wind_speed_10m,weather_code&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,sunset,sunrise&timezone=${TZ}&forecast_days=7"

log() { echo "[$(date -Is)] $*"; }

render_weather() {
  local tmp json
  tmp="$(mktemp -d)"
  json="$tmp/weather.json"

  log "Fetching Open-Meteo..."
  curl -fsSL "$URL" -o "$json"

  log "Rendering PNG..."
  python3 "${SCRIPT_DIR}/render_weather_png.py" --json "$json" --out "${OUT_PNG}.new" --location "$LOCATION_LABEL"

  mv "${OUT_PNG}.new" "$OUT_PNG"
  rm -rf "$tmp"
  log "Render done -> ${OUT_PNG}"
}

log "Kindle weather daemon starting (render every ${RENDER_INTERVAL}s, Kindle pulls via SCP)."

while true; do
  render_weather || log "Render failed, will retry next cycle."
  sleep "$RENDER_INTERVAL"
done
