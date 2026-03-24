# Kindle K3W — Battery-Powered Wall Weather Display

A Kindle Keyboard (K3W, 3rd gen Wi-Fi) running as an autonomous wall weather dashboard.
Renders weather data from Open-Meteo onto the 600×800 e-ink screen every 3 hours.
Runs entirely on battery — no USB power required.

---

## How it works

```
Ubuntu (server)                        Kindle K3W (wall display)
───────────────                        ─────────────────────────
Fetch Open-Meteo API                   Boot → run weather_flip.sh
Render 600×800 PNG (Pillow)            Enable Wi-Fi
Save to ~/kindle-weather/weather.png   SCP pull weather.png from Ubuntu
Wait 3 hours → repeat          <───   Display via eips
                                       Disable Wi-Fi
                                       Set RTC alarm (+3 hours)
                                       Suspend to RAM  <── zero draw
                                       [RTC fires] → wake → repeat
```

The Kindle **pulls** from Ubuntu (not the other way around). Ubuntu doesn't need to know
when the Kindle is awake. Each wake the Kindle grabs the latest pre-rendered PNG, displays
it, and goes back to sleep.

---

## Hardware

- **Kindle Keyboard Wi-Fi (K3W)** — 600×800 e-ink, ARMv6 (ARM1136), Linux 2.6.26-rt-lab126, BusyBox v1.7.2
- **Ubuntu server** on the same LAN — runs Python 3 + Pillow, serves PNG via SCP

---

## Prerequisites

### Kindle side
- [USBNetwork hack](https://www.mobileread.com/forums/showthread.php?t=88004) installed — provides SSH over Wi-Fi, `scp`, `ssh`, `ssh-keygen` under `/mnt/us/usbnet/bin/`
- Python 2.7 at `/mnt/us/python/bin/python2.7` (from MobileRead NiLuJe packages)

### Ubuntu side
```bash
sudo apt install python3-pil curl
```

---

## Setup

### 1. Ubuntu — render daemon

```bash
git clone https://github.com/am71-git-hub/kindle.git
cd kindle/ubuntu
```

Edit `kindle_weather_daemon.sh` — set your latitude, longitude, and timezone.
Edit `render_weather_png.py` — set your `--location` label.

Run as a systemd user service (create `~/.config/systemd/user/kindle-weather.service`):

```ini
[Unit]
Description=Kindle Weather Renderer

[Service]
ExecStart=/bin/bash %h/kindle-weather/kindle_weather_daemon.sh
Restart=always
StandardOutput=append:%h/kindle-weather/daemon.log
StandardError=append:%h/kindle-weather/daemon.log

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now kindle-weather
```

The daemon fetches Open-Meteo every 3 hours and writes `weather.png` to the project directory.

### 2. Kindle — SSH key (Kindle → Ubuntu)

SSH into the Kindle from Ubuntu, then on the Kindle:

```sh
mkdir -p /root/.ssh && chmod 700 /root/.ssh
/mnt/us/usbnet/bin/ssh-keygen -t ed25519 -N '' -f /root/.ssh/id_ed25519
cat /root/.ssh/id_ed25519.pub
```

Copy the printed public key into `~/.ssh/authorized_keys` on Ubuntu.

Add Ubuntu's host key to the Kindle's known_hosts:
```sh
ssh-keyscan -H <your-ubuntu-ip> >> /root/.ssh/known_hosts
```

> **Note:** The Kindle ships with OpenSSH 7.0p1. Ubuntu 22.04+ disables `ssh-rsa` (SHA-1).
> Use `ed25519` — it works on both ends without any server config changes.

### 3. Kindle — deploy scripts

From Ubuntu:
```bash
scp kindle/rtcwake.py kindle/weather_flip.sh kindle:/mnt/us/weather/
```

Edit `UBUNTU_IP` and `UBUNTU_USER` in `weather_flip.sh` to match your server.

### 4. Kindle — auto-start on boot

```sh
# SSH into Kindle:
mntroot rw
cp /mnt/us/weather/init_kindle_weather /etc/init.d/kindle-weather
chmod +x /etc/init.d/kindle-weather
ln -sf /etc/init.d/kindle-weather /etc/rc5.d/S99kindle-weather
mntroot ro
```

---

## Files

```
ubuntu/
  kindle_weather_daemon.sh   Fetches weather API, renders PNG every 3h
  render_weather_png.py      Python 3 + Pillow renderer (600x800, 16-gray dithered)

kindle/
  weather_flip.sh            Main loop: pull PNG -> display -> sleep -> repeat
  rtcwake.py                 Sets RTC wake alarm via ioctl and suspends
  init_kindle_weather        SysV init script for /etc/init.d/
```

---

## Key technical notes

### RTC wake alarm — the hard part

The Kindle K3W's i.MX35 RTC has a broken sysfs interface:

```sh
echo 1234567890 > /sys/class/rtc/rtc0/wakealarm  # exits 0
cat /sys/class/rtc/rtc0/wakealarm                 # prints nothing — alarm NOT set
```

The fix is to use the `RTC_WKALM_SET` ioctl directly, bypassing sysfs entirely.
`rtcwake.py` does this via Python 2.7's `fcntl.ioctl`:

```python
RTC_WKALM_SET = 0x4028700f  # _IOW('p', 0x0f, struct rtc_wkalrm) on ARM 32-bit LE
fcntl.ioctl(fd, RTC_WKALM_SET, alarm)
```

This reliably wakes the Kindle from `mem` suspend after the specified interval.
Confirmed working on K3W with Linux 2.6.26-rt-lab126.

### `sleep` vs wall clock

BusyBox `sleep` on Linux 2.6.26 uses `CLOCK_MONOTONIC`, which **pauses** during CPU suspend.
A `sleep 300` after a 6-day suspension appears to complete immediately — no real time passes.

All timed loops use wall-clock comparisons instead:
```sh
TARGET=$(( $(date +%s) + INTERVAL ))
while [ "$(date +%s)" -lt "$TARGET" ]; do sleep 5; done
```

`date +%s` reads `CLOCK_REALTIME`, which is synced from the RTC on resume and advances correctly.
Same issue applies to `crond` — cron jobs don't fire during suspend.

### Wi-Fi must be off before suspend

The ar6000 Wi-Fi driver rejects suspend while Wi-Fi is active:
```
ar6000_suspend: This should never be called! error -16
```

Sequence before suspend:
```sh
lipc-set-prop com.lab126.wifid enable 0
sleep 3
kill -STOP $(pidof powerd)   # powerd fights manual suspend
python rtcwake.py 10800 mem  # blocks until RTC fires
kill -CONT $(pidof powerd)
```

### Battery monitoring

Battery level is at a non-standard sysfs path on K3W:
```
/sys/devices/system/luigi_battery/luigi_battery0/battery_capacity
```
`/sys/class/power_supply/*/capacity` does not exist on this device.

If battery drops below 15%, `weather_flip.sh` overlays a warning via `eips` text mode
and shortens the sleep interval to 30 minutes.

### eips display

`/usr/sbin/eips` (built-in Kindle binary) accepts PNG files directly:
```sh
eips -g /mnt/us/weather/weather.png
```
The PNG must be 600×800. The renderer outputs a 16-shade grayscale palette PNG
with Floyd-Steinberg dithering, which looks good on the K3W screen.

---

## What we tried that didn't work

| Approach | Problem |
|---|---|
| `echo timestamp > /sys/class/rtc/rtc0/wakealarm` | Exits 0 but reads back blank — alarm not set (i.MX35 driver bug) |
| Cross-compiled C `rtcwake` (`arm-linux-gnueabihf-gcc -static`) | Segfaults — gnueabihf targets ARMv7, Kindle is ARMv6 |
| `sleep $INTERVAL` for scheduling | CLOCK_MONOTONIC pauses during suspend |
| `crond` for 3-hour schedule | Also pauses during suspend — jobs never fire |
| Push from Ubuntu to Kindle | Ubuntu can't know when Kindle is awake |
| `lipc-send-event com.lab126.powerd userSleep` | "Failed to open LIPC" from SSH context |
| `ssh-rsa` keys for Kindle → Ubuntu | Ubuntu 22.04+ rejects ssh-rsa; use ed25519 |
| `dropbearkey` to generate SSH keys | Generates dropbear format; Kindle uses OpenSSH 7.0 which needs OpenSSH format |

---

## Battery life estimate

E-ink holds the last image at zero power during suspend. Active periods per update cycle:
- ~15s Wi-Fi association
- ~2s SCP file transfer
- ~1s eips screen refresh

Three updates/day = ~54 seconds active per day.
On a stock K3W battery at ~50% charge, expect several weeks between charges.
