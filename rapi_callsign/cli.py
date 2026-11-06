import argparse
import json
import sys

from .bulk import bulk_fetch, parse_regions
from .client import RapiCallsignClient


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] == "bulk":
        parser = argparse.ArgumentParser(prog="rapi-callsign bulk")
        parser.add_argument("--regions", default="01-99")
        parser.add_argument("--source", default="rapi", choices=["rapi", "ikrap"])
        parser.add_argument("--delay", type=float, default=0.5)
        parser.add_argument("--out", default="rapi_callsigns.csv")
        parser.add_argument("--tested", default="rapi_tested.txt")
        args = parser.parse_args(argv[1:])

        def progress(tested, found, last):
            print(f"tested={tested} found={found} last={last}", flush=True)

        tested, found = bulk_fetch(
            parse_regions(args.regions),
            source=args.source,
            delay=args.delay,
            output_csv=args.out,
            tested_file=args.tested,
            on_progress=progress,
        )
        print(f"FINISHED: tested={tested} found={found}")
        return 0

    parser = argparse.ArgumentParser(prog="rapi-callsign")
    parser.add_argument("callsign", nargs="?", help="Callsign to look up, e.g. JZ13AIV")
    parser.add_argument("--source", default="rapi", choices=["rapi", "ikrap"])
    parser.add_argument("--delay", type=float, default=0.8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.callsign:
        parser.print_help()
        return 2

    client = RapiCallsignClient(source=args.source, delay=args.delay)
    record = client.get(args.callsign, source=args.source)
    if args.json:
        print(json.dumps(record.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"callsign: {record.callsign}")
        print(f"found: {record.found}")
        print(f"source: {record.source}")
        print(f"nama_lengkap: {record.nama_lengkap}")
        print(f"provinsi: {record.provinsi}")
        print(f"kota_kabupaten: {record.kota_kabupaten}")
        print(f"no_ikrap: {record.no_ikrap}")
        print(f"masa_berlaku: {record.masa_berlaku}")
        print(f"status: {record.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())