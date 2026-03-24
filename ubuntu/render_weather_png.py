#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import zoneinfo
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


def wmo_bucket(code: Any) -> str:
    try:
        c = int(code)
    except Exception:
        return "unknown"
    if c == 0:
        return "clear"
    if c in (1, 2):
        return "partly_cloudy"
    if c == 3:
        return "cloudy"
    if c in (45, 48):
        return "fog"
    if 51 <= c <= 67:
        return "rain"
    if 71 <= c <= 77:
        return "snow"
    if 80 <= c <= 82:
        return "rain"
    if c in (95, 96, 99):
        return "thunder"
    return "unknown"


def wmo_text(code: Any) -> str:
    return {
        "clear": "Clear",
        "partly_cloudy": "Partly cloudy",
        "cloudy": "Cloudy",
        "fog": "Fog",
        "rain": "Rain",
        "snow": "Snow",
        "thunder": "Thunder",
        "unknown": "Unknown",
    }.get(wmo_bucket(code), "Unknown")


def draw_icon(draw: ImageDraw.ImageDraw, kind: str, box: Tuple[int, int, int, int], fill: int = 0) -> None:
    x0, y0, x1, y1 = box
    w = x1 - x0
    h = y1 - y0

    def oval(rx0, ry0, rx1, ry1):
        draw.ellipse((x0 + rx0, y0 + ry0, x0 + rx1, y0 + ry1), fill=fill)

    def rect(rx0, ry0, rx1, ry1):
        draw.rectangle((x0 + rx0, y0 + ry0, x0 + rx1, y0 + ry1), fill=fill)

    def poly(points):
        draw.polygon([(x0 + px, y0 + py) for px, py in points], fill=fill)

    kind = kind or "unknown"

    if kind in ("cloudy", "partly_cloudy", "rain", "snow", "thunder"):
        oval(w*0.12, h*0.35, w*0.52, h*0.75)
        oval(w*0.35, h*0.20, w*0.78, h*0.70)
        oval(w*0.58, h*0.35, w*0.90, h*0.75)
        rect(w*0.18, h*0.55, w*0.88, h*0.80)

        if kind == "partly_cloudy":
            oval(w*0.05, h*0.05, w*0.40, h*0.40)

        if kind == "rain":
            for i in range(3):
                cx = w*(0.30 + i*0.18)
                poly([(cx, h*0.82), (cx - w*0.04, h*0.95), (cx + w*0.04, h*0.95)])

        if kind == "snow":
            for i in range(3):
                cx = w*(0.30 + i*0.18)
                oval(cx - w*0.03, h*0.86, cx + w*0.03, h*0.92)
                oval(cx - w*0.03, h*0.93, cx + w*0.03, h*0.99)

        if kind == "thunder":
            poly([(w*0.52, h*0.78), (w*0.40, h*0.98), (w*0.55, h*0.98),
                  (w*0.45, h*1.15), (w*0.70, h*0.90), (w*0.55, h*0.90)])
        return

    if kind == "clear":
        oval(w*0.20, h*0.20, w*0.80, h*0.80)
        return

    if kind == "fog":
        oval(w*0.12, h*0.30, w*0.52, h*0.70)
        oval(w*0.35, h*0.15, w*0.78, h*0.65)
        oval(w*0.58, h*0.30, w*0.90, h*0.70)
        rect(w*0.18, h*0.50, w*0.88, h*0.75)
        for yy in (0.78, 0.86, 0.94):
            draw.rectangle((x0 + w*0.15, y0 + h*yy, x0 + w*0.90, y0 + h*(yy+0.03)), fill=fill)
        return

    rect(w*0.30, h*0.25, w*0.70, h*0.35)
    rect(w*0.60, h*0.35, w*0.70, h*0.55)
    rect(w*0.45, h*0.55, w*0.55, h*0.70)
    rect(w*0.45, h*0.78, w*0.55, h*0.88)


@dataclass
class Theme:
    bg: int = 255
    fg: int = 0


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    # Ubuntu usually has DejaVuSans installed.
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in candidates:
        fp = Path(p)
        if fp.exists():
            return ImageFont.truetype(str(fp), size=size)
    return ImageFont.load_default()


def safe_num(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def fmt_temp_c(x: Any) -> str:
    v = safe_num(x)
    return "?" if v is None else f"{int(round(v))}°"


def fmt_mm(x: Any) -> str:
    v = safe_num(x)
    return "?" if v is None else f"{v:.1f}mm"


def fmt_pct(x: Any) -> str:
    v = safe_num(x)
    return "?" if v is None else f"{int(round(v))}%"


def dither_to_16_gray(im_l: Image.Image) -> Image.Image:
    pal = []
    for i in range(16):
        g = int(round(i * 255 / 15))
        pal.extend([g, g, g])
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(pal * 16)
    return im_l.convert("RGB").quantize(palette=pal_img, dither=Image.FLOYDSTEINBERG)


def render(weather: Dict[str, Any], out_path: Path, location: str) -> None:
    W, H = 600, 800
    theme = Theme()
    im = Image.new("L", (W, H), color=theme.bg)
    draw = ImageDraw.Draw(im)

    font_reg = load_font(22, bold=False)
    font_small = load_font(18, bold=False)
    font_big = load_font(92, bold=True)
    font_med = load_font(32, bold=True)
    font_bold = load_font(24, bold=True)

    cur = weather.get("current") or {}
    daily = weather.get("daily") or {}
    hourly = weather.get("hourly") or {}

    pad = 18
    header_h = 80
    updated = dt.datetime.now(zoneinfo.ZoneInfo("America/Toronto")).strftime("%a %b %d %-I:%M %p")
    draw.text((pad, 16), f"Last update: {updated}", fill=theme.fg, font=font_reg)

    r_w = draw.textlength(location, font=font_reg)
    draw.text((W - pad - r_w, 16), location, fill=theme.fg, font=font_reg)
    draw.line((pad, header_h - 10, W - pad, header_h - 10), fill=0, width=2)

    now_top = header_h
    temp = fmt_temp_c(cur.get("temperature_2m"))
    feels = fmt_temp_c(cur.get("apparent_temperature"))
    code = cur.get("weather_code")
    cond = wmo_text(code)
    icon_kind = wmo_bucket(code)

    draw.text((pad, now_top + 10), temp, fill=theme.fg, font=font_big)
    draw.text((pad, now_top + 130), cond, fill=theme.fg, font=font_med)

    icon_box = (W - pad - 120, now_top + 18, W - pad, now_top + 138)
    draw_icon(draw, icon_kind, icon_box, fill=theme.fg)

    wind = cur.get("wind_speed_10m")
    hum = cur.get("relative_humidity_2m")

    pop0 = (hourly.get("precipitation_probability") or [None])[0]
    pr0 = (hourly.get("precipitation") or [None])[0]

    line1 = f"Feels {feels}   Wind {wind if wind is not None else '?'} km/h   Hum {fmt_pct(hum)}"
    line2 = f"Precip {fmt_mm(pr0)}   PoP {fmt_pct(pop0)}"
    draw.text((pad, now_top + 170), line1, fill=theme.fg, font=font_small)
    draw.text((pad, now_top + 194), line2, fill=theme.fg, font=font_small)

    now_bottom = now_top + 220
    draw.line((pad, now_bottom + 8, W - pad, now_bottom + 8), fill=0, width=2)

    fc_top = now_bottom + 18
    draw.text((pad, fc_top), "5-DAY", fill=theme.fg, font=font_bold)

    rows_top = fc_top + 34
    rows = 5
    row_h = int((H - rows_top - 18) / rows)

    times = daily.get("time") or []
    code_d = daily.get("weather_code") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    psum = daily.get("precipitation_sum") or []
    ppmax = daily.get("precipitation_probability_max") or []

    for i in range(min(rows, len(times))):
        y = rows_top + i * row_h
        if i > 0:
            draw.line((pad, y, W - pad, y), fill=200, width=1)

        try:
            d = dt.datetime.strptime(times[i], "%Y-%m-%d")
            day = d.strftime("%a")
        except Exception:
            day = str(times[i])[:3]

        draw.text((pad, y + 18), day, fill=theme.fg, font=font_med)
        draw_icon(draw, wmo_bucket(code_d[i] if i < len(code_d) else None),
                  (pad + 90, y + 10, pad + 90 + 52, y + 10 + 52), fill=theme.fg)

        hi = fmt_temp_c(tmax[i] if i < len(tmax) else None)
        lo = fmt_temp_c(tmin[i] if i < len(tmin) else None)
        draw.text((pad + 160, y + 16), f"Hi {hi}  Lo {lo}", fill=theme.fg, font=font_reg)

        mm = fmt_mm(psum[i] if i < len(psum) else None)
        pop = fmt_pct(ppmax[i] if i < len(ppmax) else None)
        right = f"{mm}  {pop}"
        r_w = draw.textlength(right, font=font_reg)
        draw.text((W - pad - r_w, y + 16), right, fill=theme.fg, font=font_reg)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pal_im = dither_to_16_gray(im)
    pal_im.save(out_path, format="PNG", optimize=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--location", default="Etobicoke")
    args = ap.parse_args()

    weather = json.loads(Path(args.json).read_text(encoding="utf-8"))
    render(weather, Path(args.out), args.location)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
