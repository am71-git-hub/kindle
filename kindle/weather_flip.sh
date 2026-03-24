#!/bin/sh
# weather_flip.sh - pull weather PNG from Ubuntu, display, sleep, repeat
# Runs on boot via /etc/init.d/kindle-weather -> /etc/rc5.d/S99kindle-weather
# Loops forever: each RTC wake exec's itself at the bottom.

LOG=/mnt/us/weather/flip.log
UBUNTU_USER=andrew
UBUNTU_IP=10.45.69.117          # <-- change to your Ubuntu machine's IP
REMOTE_PNG=/home/andrew/kindle-weather/weather.png
LOCAL_PNG=/mnt/us/weather/weather.png
BATTERY=/sys/devices/system/luigi_battery/luigi_battery0/battery_capacity
SCP="/mnt/us/usbnet/bin/scp -i /root/.ssh/id_ed25519"
PYTHON=/mnt/us/python/bin/python2.7
SLEEP_SECS=10800  # 3 hours

log() { echo "$(date): $*" >> "$LOG"; }

log "=== weather_flip start ==="

# ---- Battery check ----
BAT=$(cat "$BATTERY" 2>/dev/null || echo 100)
log "Battery: ${BAT}%"
if [ "$BAT" -lt 15 ]; then
  log "Battery LOW - reducing sleep to 30 min"
  SLEEP_SECS=1800
fi

# ---- Enable Wi-Fi and wait for connection ----
lipc-set-prop com.lab126.wifid enable 1 2>/dev/null
log "Wi-Fi enable sent, waiting for connection..."
WIFI_DEADLINE=$(( $(date +%s) + 45 ))
CONNECTED=0
while [ "$(date +%s)" -lt "$WIFI_DEADLINE" ]; do
  if ping -c1 -W2 "$UBUNTU_IP" >/dev/null 2>&1; then
    log "Wi-Fi connected"
    CONNECTED=1
    break
  fi
  sleep 3
done
if [ "$CONNECTED" -eq 0 ]; then
  log "Wi-Fi did not connect in time, will use cached PNG if available"
fi

# ---- Pull weather PNG from Ubuntu ----
if [ "$CONNECTED" -eq 1 ]; then
  if $SCP -o StrictHostKeyChecking=no -o ConnectTimeout=15 \
       "${UBUNTU_USER}@${UBUNTU_IP}:${REMOTE_PNG}" "${LOCAL_PNG}.new" 2>>"$LOG"; then
    if [ -s "${LOCAL_PNG}.new" ]; then
      mv "${LOCAL_PNG}.new" "$LOCAL_PNG"
      log "PNG updated from Ubuntu"
    else
      rm -f "${LOCAL_PNG}.new"
      log "SCP returned empty file"
    fi
  else
    rm -f "${LOCAL_PNG}.new"
    log "SCP failed, using cached PNG"
  fi
fi

# ---- Display on e-ink via eips ----
if [ -f "$LOCAL_PNG" ]; then
  /usr/sbin/eips -g "$LOCAL_PNG" 2>>"$LOG" \
    && log "Display updated" \
    || log "Display update failed"
else
  log "No PNG available to display"
fi

# ---- Battery warning overlay ----
if [ "$BAT" -lt 15 ]; then
  /usr/sbin/eips 1 1 "!! BATTERY LOW ${BAT}% - PLEASE CHARGE !!"
  log "Battery warning shown on screen"
fi

# ---- Disable Wi-Fi ----
lipc-set-prop com.lab126.wifid enable 0 2>/dev/null
sleep 3

# ---- Sleep via RTC alarm ----
log "Suspending for ${SLEEP_SECS}s via RTC alarm..."
kill -STOP $(pidof powerd) 2>/dev/null
$PYTHON /mnt/us/weather/rtcwake.py "$SLEEP_SECS" mem >>"$LOG" 2>&1
kill -CONT $(pidof powerd) 2>/dev/null

log "RTC wake: resumed"

# ---- Loop ----
exec /bin/sh /mnt/us/weather/weather_flip.sh
