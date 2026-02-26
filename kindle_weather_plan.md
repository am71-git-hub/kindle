# Kindle Keyboard K3W — Wall Weather Dashboard
## Implementation Plan

**Device:** Kindle Keyboard Wi-Fi (K3W, 600×800 e-ink, 16 shades of gray)  
**Location:** Etobicoke, ON (lat: 43.6532, lon: -79.5657)  
**Goal:** Always-on wall display. Updates 3×/day. Battery-optimised.

---

## 🔍 Discovered Tools (NiLuJe ecosystem)

### Already on your Kindle (via USBNetwork 0.57.N-k3)
| Tool | Binary location | Purpose in this project |
|------|----------------|------------------------|
| **fbink** | `/mnt/us/usbnet/bin/fbink` | Render PNG image to e-ink screen |
| **fbdepth** | `/mnt/us/usbnet/bin/fbdepth` | Set framebuffer to optimal 8bpp grayscale mode |
| **curl** | `/mnt/us/usbnet/bin/curl` | Fetch weather API |
| **jq** | `/mnt/us/usbnet/bin/jq` | Parse JSON response |
| **busybox** | `/mnt/us/usbnet/bin/busybox` | Shell utilities (cron-like loops, date, sleep, etc.) |
| **kindletool** | `/mnt/us/usbnet/bin/kindletool` | Read device info / serial |
| **eips** | `/usr/sbin/eips` | Built-in Kindle screen printer (fallback) |

### New tools to install (from MobileRead NiLuJe snapshot thread)
| Tool | Download | Purpose |
|------|---------|---------|
| **Python 3.9** | `kindle-python-0.14.N-r18833.tar.xz` (Legacy thread) | Full Python 3 on device: requests, Pillow, image generation |
| **Screensaver Hack** | `kindle-ss-0.47.N-r18980.tar.xz` (Legacy thread) | Replace sleep screensavers with custom PNG — shows weather while Kindle is "off" |

> **The Screensaver Hack is the key to low-power wall display:**  
> If we write our weather PNG into the screensaver folder, the Kindle shows fresh weather data  
> whenever it sleeps — which is normally. E-ink holds the image at **zero power draw**.

---

## 🏗 Architecture

### Full On-Device Stack (no server needed)

```
[Kindle boots / wakes from sleep loop]
        │
        ├── Read battery → /sys/class/power_supply/bq27200-0/capacity
        │       └── ≤ 5% → render "Battery Critical" screen → sleep 3600s → repeat
        │
        ├── lipc-set-prop com.lab126.wifid enable 1    ← Wi-Fi ON
        ├── sleep 25                                   ← wait for DHCP
        │
        ├── Python 3.9:
        │       ├── urllib / requests → Open-Meteo API
        │       ├── json.loads → parse response
        │       └── Pillow (PIL) → generate 600×800 grayscale PNG
        │               ├── TOP THIRD    (0–266px)   current conditions
        │               ├── MIDDLE THIRD (267–533px)  7-day forecast
        │               └── BOTTOM THIRD (534–800px)  hourly (7–12h)
        │
        ├── fbdepth -d 8                               ← optimal e-ink depth
        ├── fbink -g /mnt/us/weather/weather.png       ← display on screen
        ├── cp weather.png /mnt/us/linkss/weather.png  ← update screensaver
        │
        ├── lipc-set-prop com.lab126.wifid enable 0    ← Wi-Fi OFF
        └── sleep 28800 (8 hours)                     ← repeat
```

---

## 📐 Screen Layout (600×800 px)

```
┌──────────────────────────────────────────────┐  ← y=0
│  📅 Wednesday, Feb 26            🔋 73%      │
│                                               │
│         ☁ Overcast                           │  TOP THIRD
│         -3°C  Feels like -9°C                │  (current day)
│         💨 NW 22 km/h   💧 Humidity 81%     │
│         Sunset: 6:02 PM                      │
├───────────────────────────────────────────────┤  ← y=267
│  7-DAY FORECAST                              │
│  Thu   🌧  Hi -1°  Lo -7°  💧 2.1mm  80%   │
│  Fri   🌤  Hi  4°  Lo -2°  💧 0.0mm   5%   │  MIDDLE THIRD
│  Sat   🌨  Hi  1°  Lo -4°  💧 1.4mm  60%   │  (7-day)
│  Sun   ⛅  Hi  3°  Lo -1°  💧 0.2mm  20%   │
│  Mon   ☀   Hi  6°  Lo  1°  💧 0.0mm   0%   │
│  Tue   🌧  Hi  2°  Lo -2°  💧 3.0mm  90%   │
├───────────────────────────────────────────────┤  ← y=534
│  HOURLY (next 12h)                           │
│  3PM  ☁  -2°  30%  0.4mm  💨 18 km/h       │
│  5PM  🌧 -3°  55%  0.9mm  💨 22 km/h       │  BOTTOM THIRD
│  7PM  🌧 -4°  70%  1.2mm  💨 26 km/h       │  (hourly)
│  9PM  ⛅ -5°  20%  0.1mm  💨 15 km/h       │
│  11PM ☁  -6°  15%  0.0mm  💨 12 km/h       │
└──────────────────────────────────────────────┘  ← y=800
```

---

## 📡 Data Source — Open-Meteo API

Free. No API key. No account.

**Single API call fetches everything:**
```
https://api.open-meteo.com/v1/forecast
  ?latitude=43.6532
  &longitude=-79.5657
  &current=temperature_2m,apparent_temperature,weather_code,
           wind_speed_10m,wind_direction_10m,relative_humidity_2m
  &hourly=temperature_2m,precipitation_probability,precipitation,
          wind_speed_10m,weather_code
  &daily=weather_code,temperature_2m_max,temperature_2m_min,
         precipitation_sum,precipitation_probability_max,
         wind_speed_10m_max,sunset,sunrise
  &timezone=America%2FToronto
  &forecast_days=7
```

**WMO weather codes** (returned by API) map to icons/text:
- `0` = Clear sky ☀
- `1–3` = Partly cloudy ⛅
- `45,48` = Fog 🌫
- `51–67` = Drizzle/Rain 🌧
- `71–77` = Snow ❄
- `80–82` = Rain showers 🌦
- `95` = Thunderstorm ⛈

---

## 🔋 Battery Management

```python
# Read battery from kernel sysfs
with open("/sys/class/power_supply/bq27200-0/capacity") as f:
    batt_pct = int(f.read().strip())

if batt_pct <= 5:
    render_battery_warning_screen(batt_pct)  # shows large warning
    time.sleep(3600)     # retry in 1 hour
    sys.exit(0)
```

**Battery %-indicator** shown in every screen update (top-right corner).  
**Critical screen** shown at ≤5%: large battery icon, percentage, "Please charge".

---

## 📁 File Structure on Kindle

```
/mnt/us/
  weather/
    weather.sh          ← main launcher shell script
    weather.py          ← Python 3 image generator
    weather.png         ← last generated image
    icons/
      clear.png         ← weather condition icons (50×50px, grayscale)
      cloudy.png
      rain.png
      snow.png
      foggy.png
      storm.png
      battery_low.png
    fonts/
      weather_font.ttf  ← TrueType font for Pillow rendering
  linkss/               ← screensaver hack folder (symlinked images)
    weather.png         ← copy of current weather image = sleep screensaver
  usbnet/               ← existing USBNetwork folder
    auto                ← (optional) auto-start file
```

---

## 🛠 Step-by-Step Implementation

### Phase 1 — Install Additional Tools
1. Download `kindle-python-0.14.N-r18833.tar.xz` from MobileRead snapshot thread
2. Copy `Update_python_0.14.N_k3_install.bin` to Kindle root
3. Run "Update Your Kindle" — installs Python 2.7 + 3.9
4. Download `kindle-ss-0.47.N-r18980.tar.xz`
5. Copy screensaver installer [.bin](file:///C:/Users/am71/Desktop/Antigravity/kindle/jailbreak/Update_jailbreak_0.13.N_dx_install.bin) to Kindle root
6. Run "Update Your Kindle" — installs screensaver hack, creates `/mnt/us/linkss/`

### Phase 2 — Write the Python Script (on Ubuntu server)
File: `weather.py`
- Uses `urllib.request` (stdlib, no install needed) to fetch Open-Meteo
- Uses `json` to parse response
- Uses `Pillow` to generate PNG:
  - Load TTF font(s) from `/mnt/us/weather/fonts/`
  - Draw 3-section layout
  - Paste weather icon PNGs
  - Save as 8-bit grayscale PNG (e-ink optimal)
- Reads battery from `/sys/class/power_supply/bq27200-0/capacity`

### Phase 3 — Write the Shell Launcher (weather.sh)
```sh
#!/bin/sh
# Kindle Weather Dashboard launcher
WEATHER_DIR="/mnt/us/weather"
PYTHON="/mnt/us/python3/bin/python3"

# Battery check
BATT=$(cat /sys/class/power_supply/bq27200-0/capacity)

# Wi-Fi on
lipc-set-prop com.lab126.wifid enable 1
sleep 25

# Fetch + render
$PYTHON $WEATHER_DIR/weather.py

# Display
/mnt/us/usbnet/bin/fbdepth -d 8
/mnt/us/usbnet/bin/fbink -g $WEATHER_DIR/weather.png

# Update screensaver
cp $WEATHER_DIR/weather.png /mnt/us/linkss/weather.png

# Wi-Fi off
lipc-set-prop com.lab126.wifid enable 0
```

### Phase 4 — Auto-start at Boot
```sh
# Drop blank 'auto' file in usbnet folder (while USB-mounted):
touch D:\usbnet\auto
# → Kindle will auto-start SSH at boot (needed so server can push updates or for debugging)
```

### Phase 5 — Schedule Updates (loop on Kindle)
```sh
# Add to weather.sh end:
sleep 28800 && /mnt/us/weather/weather.sh &
```

Or: launch from Kindle's startup via `/etc/upstart/` custom job.

### Phase 6 — SCP Scripts to Kindle (from Ubuntu server)
```bash
scp -o PubkeyAcceptedKeyTypes=ssh-rsa \
    weather.py weather.sh fonts/ icons/ \
    root@10.45.69.239:/mnt/us/weather/
chmod +x /mnt/us/weather/weather.sh
```

---

## ❓ Customization Questions

Before writing the actual code, please answer:

1. **Temperature?** Celsius or Fahrenheit?
2. **Time format?** 12-hour (3:00 PM) or 24-hour (15:00)?
3. **Wind speed?** km/h or m/s?
4. **Icons?** PNG weather icons, OR text emoji-style (▲ ≈ ◆), OR Unicode rendered via font?
5. **Font style?** Clean/minimal (think dashboard) or slightly decorative?
6. **Always-on?** Should the screen stay lit at all times on the wall, or let it sleep (screensaver = weather)?  
   *(Sleeping = far better battery life + same visual result with screensaver hack)*
7. **Update times?** e.g. 7am / 1pm / 7pm — or every 8 hours from boot?
8. **Do you want a "last updated" timestamp** shown on screen?

---

## 🔗 Key Resources

- [Open-Meteo API docs](https://open-meteo.com/en/docs)
- [FBInk GitHub](https://github.com/NiLuJe/FBInk)
- [NiLuJe MobileRead snapshot thread](https://www.mobileread.com/forums/showthread.php?t=225030)
- [Legacy Kindle Hacks thread](https://www.mobileread.com/forums/showthread.php?t=88004)
- [Pillow (PIL) docs](https://pillow.readthedocs.io/)
