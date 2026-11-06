import html
import re
import time
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional

import requests

RAPI_BASE = "https://mail.rapinasional.or.id/"
IKRAP_BASE = "https://iar-ikrap.postel.go.id/"
IKRAP_SEARCH = "https://iar-ikrap.postel.go.id/registrant/searchDataIar/"


@dataclass
class CallsignRecord:
    callsign: str
    source: str
    found: bool
    nama_lengkap: str = ""
    provinsi: str = ""
    kota_kabupaten: str = ""
    no_ikrap: str = ""
    masa_berlaku: str = ""
    status: str = ""
    raw: str = field(default="", repr=False)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("raw", None)
        return d


def _clean(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value)).strip()


def _clean_callsign(value: str) -> str:
    return value.strip().upper()


def parse_rapi_html(callsign: str, text: str) -> CallsignRecord:
    def label(key: str) -> str:
        pat = re.compile(re.escape(key) + r"\s*:</label>\s*(?:<br>\s*)?(.*?)(?:<br>|</span>|</div|$)", re.S)
        for m in pat.finditer(text):
            value = _clean(m.group(1))
            if value:
                return value
        return ""

    masa = ""
    mm = re.search(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|Mei|Jun|Jul|Agu|Sep|Okt|Nov|Des)\s+\d{4}\b", text)
    if mm:
        masa = mm.group(0)

    return CallsignRecord(
        callsign=label("Callsign") or callsign,
        source="rapi",
        found="tidak ditemukan" not in text,
        nama_lengkap=label("Nama Lengkap"),
        provinsi=label("Provinsi"),
        kota_kabupaten=label("Kota/Kabupaten"),
        no_ikrap=label("No IKRAP"),
        masa_berlaku=masa,
        status="AKTIF" if "tidak ditemukan" not in text else "TIDAK DITEMUKAN",
        raw=text[:10000],
    )


def parse_ikrap_html(callsign: str, text: str) -> CallsignRecord:
    found = "none-style" in text and "not-found.png" not in text

    def pick(label: str) -> str:
        pat = re.compile(re.escape(label) + r".*?<div class=\"meta-details\">(.*?)</div>", re.S)
        m = pat.search(text)
        return _clean(m.group(1)) if m else ""

    return CallsignRecord(
        callsign=pick("Tanda Panggilan (Callsign)") or pick("Tanda Panggilan") or callsign,
        source="ikrap",
        found=found,
        nama_lengkap=pick("Nama Pemilik (Full name)") or pick("Nama Pemilik"),
        provinsi=pick("Provinsi (Province)") or pick("Provinsi"),
        masa_berlaku=pick("Masa Laku (Date of expiration)") or pick("Masa Laku"),
        status=pick("Status") or ("AKTIF" if found else "TIDAK DITEMUKAN"),
        raw=text[:5000],
    )


class RapiCallsignClient:
    def __init__(self, source: str = "rapi", delay: float = 0.8, timeout: int = 30, max_retries: int = 5):
        if source not in {"rapi", "ikrap"}:
            raise ValueError("source must be 'rapi' or 'ikrap'")
        self.source = source
        self.delay = max(0.0, delay)
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self._rapi_token: Optional[str] = None
        self._last_request_at = 0.0

    def set_source(self, source: str) -> None:
        if source not in {"rapi", "ikrap"}:
            raise ValueError("source must be 'rapi' or 'ikrap'")
        self.source = source

    def _rate_limit(self) -> None:
        now = time.time()
        remaining = self.delay - (now - self._last_request_at)
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_at = time.time()

    def _ensure_rapi_token(self) -> None:
        if self._rapi_token is not None:
            return
        r = self.session.get(RAPI_BASE, timeout=self.timeout)
        r.raise_for_status()
        m = re.search(r'value="([A-Za-z0-9]{30,})"', r.text)
        if not m:
            raise RuntimeError("Could not extract RAPI CSRF token")
        self._rapi_token = m.group(1)

    def _fetch_rapi(self, callsign: str) -> str:
        self._ensure_rapi_token()
        for attempt in range(1, self.max_retries + 1):
            self._rate_limit()
            try:
                r = self.session.post(
                    RAPI_BASE,
                    data={"_token": self._rapi_token, "callsign": callsign},
                    timeout=self.timeout,
                )
            except requests.RequestException:
                if attempt == self.max_retries:
                    raise
                self._rapi_token = None
                self._ensure_rapi_token()
                continue

            if r.status_code == 429:
                if attempt == self.max_retries:
                    raise RuntimeError("RAPI rate-limited (HTTP 429)")
                time.sleep(self.delay * (2 ** attempt) * 5)
                self._rapi_token = None
                self._ensure_rapi_token()
                continue
            if r.status_code in (403, 419) or "kedaluwarsa" in r.text:
                if attempt == self.max_retries:
                    raise RuntimeError(f"RAPI returned HTTP {r.status_code}")
                time.sleep(self.delay * (attempt + 1))
                self._rapi_token = None
                self._ensure_rapi_token()
                continue
            return r.text
        raise RuntimeError("RAPI fetch failed")

    def _fetch_ikrap(self, callsign: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": IKRAP_BASE,
            "X-Requested-With": "XMLHttpRequest",
        }
        self._rate_limit()
        r = self.session.get(IKRAP_SEARCH, params={"callsign": callsign}, headers=headers, timeout=self.timeout)
        if r.status_code != 200:
            raise RuntimeError(f"Official IKRAP endpoint returned HTTP {r.status_code}")
        try:
            return r.json()
        except ValueError:
            return r.text

    def get(self, callsign: str, source: Optional[str] = None, validate: bool = False) -> CallsignRecord:
        cs = _clean_callsign(callsign)
        if not cs:
            raise ValueError("callsign is required")
        if validate and not re.fullmatch(r"[A-Z0-9]{4,8}", cs):
            raise ValueError("callsign format is invalid")

        selected_source = source or self.source
        if selected_source == "rapi":
            text = self._fetch_rapi(cs)
            return parse_rapi_html(cs, text)
        if selected_source == "ikrap":
            text = self._fetch_ikrap(cs)
            return parse_ikrap_html(cs, text)
        raise ValueError("source must be 'rapi' or 'ikrap'")