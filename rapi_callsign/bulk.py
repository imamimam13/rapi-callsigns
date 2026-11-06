import csv
import os
import time
from typing import Callable, List, Optional

from .client import CallsignRecord, RapiCallsignClient


def parse_regions(spec: str) -> List[str]:
    out: List[str] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part and len(part.split("-")) == 2:
            a, b = [int(x) for x in part.split("-")]
            for n in range(a, b + 1):
                out.append(f"{n:02d}")
        elif part:
            out.append(part)
    return out


def bulk_fetch(
    regions: List[str],
    source: str = "rapi",
    delay: float = 0.5,
    output_csv: Optional[str] = None,
    tested_file: Optional[str] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> tuple:
    tested = set()
    if tested_file and os.path.exists(tested_file):
        with open(tested_file, encoding="utf-8") as f:
            tested = {line.strip().upper() for line in f if line.strip()}

    already = set()
    write_header = False
    if output_csv and os.path.exists(output_csv):
        with open(output_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                already.add(row["callsign"].strip().upper())
    else:
        write_header = True

    outf = None
    writer = None
    if output_csv:
        outf = open(output_csv, "a", newline="", encoding="utf-8")
        writer = csv.DictWriter(
            outf,
            fieldnames=[
                "callsign", "source", "found", "nama_lengkap", "provinsi",
                "kota_kabupaten", "no_ikrap", "masa_berlaku", "status",
            ],
        )
        if write_header:
            writer.writeheader()

    tested_out = open(tested_file, "a", encoding="utf-8") if tested_file else None

    client = RapiCallsignClient(source=source, delay=delay)

    tested_count = 0
    found_count = 0
    for region in regions:
        for a in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            for b in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    cs = f"JZ{region}{a}{b}{c}"
                    if cs in tested:
                        continue
                    record: CallsignRecord = client.get(cs, source=source)
                    tested.add(cs)
                    if tested_out:
                        tested_out.write(cs + "\n")
                        tested_out.flush()

                    tested_count += 1
                    if record.found:
                        found_count += 1
                        if writer and cs not in already:
                            writer.writerow(
                                {
                                    "callsign": record.callsign,
                                    "source": record.source,
                                    "found": record.found,
                                    "nama_lengkap": record.nama_lengkap,
                                    "provinsi": record.provinsi,
                                    "kota_kabupaten": record.kota_kabupaten,
                                    "no_ikrap": record.no_ikrap,
                                    "masa_berlaku": record.masa_berlaku,
                                    "status": record.status,
                                }
                            )
                            outf.flush()
                            already.add(cs)

                    if on_progress and tested_count % 100 == 0:
                        on_progress(tested_count, found_count, cs)

    if tested_out:
        tested_out.close()
    if outf:
        outf.close()
    return tested_count, found_count