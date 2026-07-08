"""
Klien API eksternal gratis (tanpa API key) untuk C3MR:

- Nominatim (OpenStreetMap) — geocoding alamat target ke koordinat.
  Kebijakan pemakaian: maksimal 1 request/detik dan wajib User-Agent yang jelas.
- Open-Meteo — prakiraan cuaca harian per koordinat.
- Nager.Date — kalender hari libur nasional Indonesia.

Semua hasil di-cache di memori supaya hemat kuota dan sopan terhadap rate limit.
Setiap fungsi mengembalikan None/list kosong saat API gagal — pemanggil tidak
boleh ikut gagal hanya karena layanan pihak ketiga sedang bermasalah.
"""
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

# Nominatim mewajibkan User-Agent yang bisa dihubungi (bukan UA generik).
USER_AGENT = "C3MR-capstone/1.0 (auzasn11@gmail.com)"
TIMEOUT = 10
WIB = timezone(timedelta(hours=7))

# ── Nominatim (geocoding) ────────────────────────────────────────────

_nominatim_lock = threading.Lock()
_nominatim_last_call = 0.0
_geocode_cache: dict[str, tuple[float, float] | None] = {}


def geocode_address(address: str) -> tuple[float, float] | None:
    """Alamat bebas → (lat, lon), atau None bila tidak ditemukan/gagal."""
    if not address or not address.strip():
        return None
    key = address.strip().lower()
    if key in _geocode_cache:
        return _geocode_cache[key]

    global _nominatim_last_call
    with _nominatim_lock:  # serialisasi + jeda 1 detik antar panggilan (kebijakan Nominatim)
        wait = 1.1 - (time.monotonic() - _nominatim_last_call)
        if wait > 0:
            time.sleep(wait)
        try:
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "countrycodes": "id", "limit": 1},
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            )
            _nominatim_last_call = time.monotonic()
            r.raise_for_status()
            rows = r.json()
            coords = (float(rows[0]["lat"]), float(rows[0]["lon"])) if rows else None
        except Exception as e:
            _nominatim_last_call = time.monotonic()
            logger.warning(f"Geocoding gagal untuk '{address[:60]}': {e}")
            return None  # kegagalan jaringan tidak di-cache agar bisa dicoba lagi

    _geocode_cache[key] = coords
    return coords


def geocode_targets(target_ids: list[str]) -> int:
    """Geocode target yang belum punya koordinat (dipakai sebagai background task
    setelah unggah CSV). Mencoba alamat lengkap dulu, lalu nama area saja.
    Mengembalikan jumlah target yang berhasil diberi koordinat."""
    from .database import SessionLocal
    from .models import DbTarget

    db = SessionLocal()
    done = 0
    try:
        rows = (
            db.query(DbTarget)
            .filter(DbTarget.id.in_(target_ids), DbTarget.latitude.is_(None))
            .all()
        )
        for t in rows:
            coords = geocode_address(t.address)
            if not coords:
                from .agent_tools import extract_area  # impor lokal: hindari impor melingkar
                area = extract_area(t.address)
                if area and area != "Lainnya":
                    coords = geocode_address(area)
            if coords:
                t.latitude, t.longitude = coords
                done += 1
        db.commit()
        if rows:
            logger.info(f"Geocoding selesai: {done}/{len(rows)} target diberi koordinat")
    except Exception:
        db.rollback()
        logger.exception("Geocoding background gagal")
    finally:
        db.close()
    return done


# ── Open-Meteo (cuaca) ───────────────────────────────────────────────

def get_weather(lat: float, lon: float, days: int = 3) -> dict | None:
    """Prakiraan harian: tanggal, suhu maksimum (°C), peluang hujan maksimum (%)."""
    for attempt in (1, 2):  # sekali retry — Open-Meteo kadang lambat sesaat
        try:
            r = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "temperature_2m_max,precipitation_probability_max",
                    "timezone": "Asia/Jakarta",
                    "forecast_days": max(1, min(int(days), 7)),
                },
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            d = r.json().get("daily", {})
            return {
                "dates": d.get("time", []),
                "t_max": d.get("temperature_2m_max", []),
                "rain_prob": d.get("precipitation_probability_max", []),
            }
        except Exception as e:
            if attempt == 2:
                logger.warning(f"Open-Meteo gagal ({lat},{lon}): {e}")
    return None


# ── Nager.Date (hari libur nasional Indonesia) ───────────────────────

_holiday_cache: dict[int, list[dict]] = {}


def get_holidays(year: int) -> list[dict]:
    """Libur nasional Indonesia untuk satu tahun: [{"date": "YYYY-MM-DD", "name": ...}]."""
    if year in _holiday_cache:
        return _holiday_cache[year]
    try:
        r = requests.get(f"https://date.nager.at/api/v3/PublicHolidays/{year}/ID", timeout=TIMEOUT)
        r.raise_for_status()
        holidays = [{"date": h["date"], "name": h.get("localName") or h.get("name")} for h in r.json()]
        _holiday_cache[year] = holidays
        return holidays
    except Exception as e:
        logger.warning(f"Nager.Date gagal untuk {year}: {e}")
        return []


_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def upcoming_holidays(days: int = 14) -> list[dict]:
    """Libur nasional dalam `days` hari ke depan (waktu WIB), bisa melewati pergantian tahun."""
    days = max(1, min(int(days or 14), 366))
    today = datetime.now(WIB).date()
    end = today + timedelta(days=days)
    holidays = get_holidays(today.year)
    if end.year != today.year:
        holidays = holidays + get_holidays(end.year)
    result = []
    for h in holidays:
        d = datetime.strptime(h["date"], "%Y-%m-%d").date()
        if today <= d <= end:
            result.append({**h, "day": _HARI[d.weekday()], "in_days": (d - today).days})
    return sorted(result, key=lambda h: h["date"])
