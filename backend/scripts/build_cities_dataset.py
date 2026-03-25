"""
Build a compact cities dataset from GeoNames cities1000.zip.

Usage:
  cd backend
  python scripts/build_cities_dataset.py
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from urllib.request import urlopen

GEONAMES_URL = "https://download.geonames.org/export/dump/cities1000.zip"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "cities.json"


def parse_geonames_rows(raw_text: str) -> list[dict]:
    rows: list[dict] = []
    for line in raw_text.splitlines():
        if not line.strip():
            continue

        parts = line.split("\t")
        if len(parts) < 15:
            continue

        # GeoNames schema: http://download.geonames.org/export/dump/readme.txt
        # 1=name, 4=lat, 5=lon, 8=country code, 10=admin1, 14=population.
        name = parts[1].strip()
        lat = parts[4].strip()
        lon = parts[5].strip()
        country_code = parts[8].strip().upper()
        admin1 = parts[10].strip()
        population = parts[14].strip() or "0"

        if not name or not lat or not lon:
            continue

        try:
            row = {
                "name": name,
                "lat": float(lat),
                "lon": float(lon),
                "country_code": country_code,
                "admin1": admin1,
                "population": int(population),
                "country": "",  # Optional enrichment can be added later.
            }
        except ValueError:
            continue

        rows.append(row)

    rows.sort(key=lambda x: (x["country_code"], -x["population"], x["name"]))
    return rows


def main() -> None:
    print(f"Downloading {GEONAMES_URL} ...")
    response = urlopen(GEONAMES_URL, timeout=60)
    payload = response.read()

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        text = archive.read("cities1000.txt").decode("utf-8")

    rows = parse_geonames_rows(text)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")

    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Wrote {len(rows)} cities to {OUTPUT_PATH} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
