"""Command line.

  python -m vibewatch waveform capture.csv --fs 3200
      one acceleration column (m/s^2) -> velocity RMS, acceleration RMS, peak frequency, zone

  python -m vibewatch report readings.csv --group 2 --mounting rigid
      rows of asset_id,timestamp,velocity_rms_mm_s -> one status line per asset, worst first
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime

from .severity import zone
from .signal import features
from .trend import Reading, assess

STATUS_ORDER = {"alarm": 0, "alert": 1, "watch": 2, "ok": 3}


def _read_waveform(path: str) -> list[float]:
    with open(path, newline="") as f:
        rows = [row for row in csv.reader(f) if row]
    if rows and not _is_number(rows[0][0]):
        rows = rows[1:]
    return [float(row[0]) for row in rows]


def _is_number(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


def _read_readings(path: str) -> dict[str, list[Reading]]:
    by_asset: dict[str, list[Reading]] = defaultdict(list)
    with open(path, newline="") as f:
        for line, row in enumerate(csv.DictReader(f), start=2):
            try:
                by_asset[row["asset_id"]].append(
                    Reading(datetime.fromisoformat(row["timestamp"]), float(row["velocity_rms_mm_s"]))
                )
            except (KeyError, ValueError) as exc:
                raise SystemExit(f"{path}:{line}: bad row ({exc})") from None
    return by_asset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vibewatch")
    sub = parser.add_subparsers(dest="command", required=True)

    wf = sub.add_parser("waveform", help="features from one acceleration capture")
    wf.add_argument("path")
    wf.add_argument("--fs", type=float, required=True, help="sample rate in Hz")

    rp = sub.add_parser("report", help="zone and trend status per asset")
    rp.add_argument("path")
    rp.add_argument("--json", action="store_true")

    for p in (wf, rp):
        p.add_argument("--group", type=int, choices=(1, 2), default=2)
        p.add_argument("--mounting", choices=("rigid", "flexible"), default="rigid")

    args = parser.parse_args(argv)

    if args.command == "waveform":
        f = features(_read_waveform(args.path), args.fs)
        out = asdict(f) | {"zone": zone(f.velocity_rms_mm_s, args.group, args.mounting).value}
        print(json.dumps(out, indent=2))
        return 0

    statuses = [assess(a, r, args.group, args.mounting) for a, r in _read_readings(args.path).items()]
    statuses.sort(key=lambda s: (STATUS_ORDER[s.status], -s.ratio_to_baseline))
    if args.json:
        print(json.dumps([asdict(s) | {"zone": s.zone.value} for s in statuses], indent=2, default=str))
    else:
        for s in statuses:
            why = ", ".join(s.reasons) or "-"
            print(f"{s.status:<6} {s.asset_id:<18} {s.latest_mm_s:>6.2f} mm/s  zone {s.zone.value}  {why}")
    return 1 if any(s.status == "alarm" for s in statuses) else 0


if __name__ == "__main__":
    sys.exit(main())
