#!/usr/bin/env python3
"""Compare a KAPE --tdest tree against the fixture manifest from kape_fixtures.py.

KAPE with RecreateDirectories recreates C:\\Users\\... as <tdest>\\C\\Users\\...
Exit 1 if any expected file is missing or any decoy was collected.
"""
import argparse
import json
import os
import re
import sys


def dest_path(win, tdest):
    drive = win[0].upper()
    rest = re.sub(r"^[A-Za-z]:\\", "", win)
    return os.path.join(tdest, drive, *rest.split("\\"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--tdest", required=True)
    args = ap.parse_args()
    m = json.load(open(args.manifest, encoding="utf-8"))

    missing, collected = [], []
    for e in m["expected"]:
        (collected if os.path.exists(dest_path(e["win"], args.tdest)) else missing).append(e)
    leaked = [d for d in m["decoys"] if os.path.exists(dest_path(d["win"], args.tdest))]

    by_target = {}
    for e in m["expected"]:
        by_target.setdefault(e["target"], [0, 0])[1] += 1
    for e in collected:
        by_target[e["target"]][0] += 1

    print(f"{'TARGET ENTRY':<55} COLLECTED/EXPECTED")
    for name, (c, n) in by_target.items():
        flag = "" if c == n else "   <-- MISSING"
        print(f"{name:<55} {c}/{n}{flag}")
    print()
    for e in missing:
        print(f"MISSING : {e['win']}")
    for d in leaked:
        print(f"LEAKED  : {d['win']}  (decoy was collected)")
    print(f"\nsummary: {len(collected)}/{len(m['expected'])} expected collected, "
          f"{len(leaked)}/{len(m['decoys'])} decoys leaked")
    return 1 if missing or leaked else 0


if __name__ == "__main__":
    sys.exit(main())
