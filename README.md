# RAPI Callsign

Unofficial Python package, CLI, and scraper for Indonesian radio callsign data.

Supported data sources:

- `rapi`: RAPI NUSANTARA public callsign search, richer data.
- `ikrap`: official IAR-IKRAP public AJAX endpoint, status and validity.

## Repository name

Use this folder as a GitHub repository named, for example:

```text
rapi-callsign
```

or any name you prefer, for example:

```text
indonesia-callsign-tools
```

## Features

- Python client: `RapiCallsignClient`
- CLI: `rapi-callsign`
- Bulk enumeration: `rapi-callsign bulk`
- CSV export and checkpoint/resume
- Supports both RAPI and official IAR-IKRAP sources
- Installable via pip from source, wheel, or sdist

## Requirements

- Python 3.9 or newer
- `requests>=2.28.0`

## Installation

### Option 1 - Install from a source checkout

```bash
git clone https://github.com/your-username/rapi-callsign.git
cd rapi-callsign
pip install .
```

### Option 2 - Development/editable install

```bash
cd rapi-callsign
pip install -e .
```

### Option 3 - Install from wheel

If you already have a built wheel file:

```bash
pip install rapi_callsign-0.1.0-py3-none-any.whl
```

### Option 4 - Install from sdist

```bash
pip install rapi_callsign-0.1.0.tar.gz
```

### Option 5 - Install directly from GitHub

After pushing to GitHub, users can install with:

```bash
pip install "git+https://github.com/your-username/rapi-callsign.git"
```

## Basic Python usage

```python
from rapi_callsign import RapiCallsignClient

client = RapiCallsignClient(source="ikrap", delay=0.8)
record = client.get("JZ13AIV")
print(record.to_dict())
```

Example output:

```python
{
    "callsign": "JZ13AIV",
    "source": "ikrap",
    "found": True,
    "nama_lengkap": "SARJONO",
    "provinsi": "JAWA TIMUR",
    "kota_kabupaten": "",
    "no_ikrap": "",
    "masa_berlaku": "NOPEMBER 2030",
    "status": "AKTIF (Active)"
}
```

Use the RAPI source for richer data:

```python
client = RapiCallsignClient(source="rapi", delay=0.8)
record = client.get("JZ13AIV")
print(record.to_dict())
```

## CLI usage

Look up one callsign:

```bash
rapi-callsign JZ13AIV --source ikrap
rapi-callsign JZ13AIV --source rapi --json
```

Bulk enumeration:

```bash
rapi-callsign bulk \
  --regions 01-99 \
  --source rapi \
  --delay 0.5 \
  --out rapi_callsigns.csv \
  --tested rapi_tested.txt
```

Bulk data schema:

```text
callsign, source, found, nama_lengkap, provinsi, kota_kabupaten, no_ikrap, masa_berlaku, status
```

## Method and endpoints

### RAPI NUSANTARA

Form endpoint:

```text
POST https://mail.rapinasional.or.id/
```

Body:

```text
_token=<csrf_token>
callsign=JZ13AIV
```

The parser extracts:

- Nama Lengkap
- Callsign
- Provinsi
- Kota/Kabupaten
- No IKRAP
- masa berlaku

### Official IAR-IKRAP

Private AJAX endpoint (unofficial use, subject to change):

```text
GET https://iar-ikrap.postel.go.id/registrant/searchDataIar/?callsign=JZ13AIV
```

Headers:

```text
User-Agent: Mozilla/5.0
Referer: https://iar-ikrap.postel.go.id/
X-Requested-With: XMLHttpRequest
```

The response is JSON containing an HTML string. The parser extracts:

- Nama Pemilik
- Provinsi
- Tanda Panggilan
- Masa Laku
- Status

## Bulk enumeration design

The package can enumerate candidate callsigns:

```text
JZ + region code (01-99) + 3 uppercase letters
```

Total candidates:

```text
99 * 26 * 26 * 26 = 1,740,064
```

Checkpoint behavior:

- `rapi_tested.txt` stores tested callsigns
- Existing output CSV is not duplicated on resume
- Run can be stopped and resumed

At `0.5` seconds per request, a full run for one region takes many hours and the total full set can take days. Use small batches.

## Publishing a wheel

To build locally:

```bash
python -m pip install build
python -m build
```

Artifacts will be created in:

```text
dist/
```

## GitHub setup

```bash
cd rapi-callsign
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/rapi-callsign.git
git push -u origin main
```

## Notes and limitations

- These endpoints are unofficial or internal.
- Field labels, HTML, and behavior may change without notice.
- Respect each website's terms and applicable privacy law.
- Do not send high-volume traffic without throttling.
- Data includes personal information; handle it securely and responsibly.