#!/usr/bin/env python3
"""Plant fixture files for every entry in one or more KAPE .tkape files.

For each Target entry the Path (with %user% replaced) is created and one or more
files matching FileMask are written. Recursive entries also get a nested file.
Decoy files that must NOT be collected can be supplied with --decoy.
Writes a JSON manifest of expected and decoy files for kape_verify.py.
"""
import argparse
import json
import os
import re
import sys

import yaml


def win_to_local(path, root):
    """Map C:\\foo\\bar to <root>/foo/bar so the generator can run anywhere."""
    p = re.sub(r"^[A-Za-z]:\\", "", path).replace("\\", os.sep)
    return os.path.join(root, p)


def mask_to_names(mask):
    if not mask:
        return ["fixture.bin"]
    mask = mask.strip("'\"")
    if "*" not in mask:
        return [mask]
    return [mask.replace("*", "sample"), mask.replace("*", "")]


def plant(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tkape", nargs="+")
    ap.add_argument("--root", required=True, help="filesystem root standing in for C:\\")
    ap.add_argument("--user", default="testuser")
    ap.add_argument("--decoy", action="append", default=[],
                    help="Windows path of a file to create that must NOT be collected")
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    # First pass: every directory any entry will need, so file names that collide with a directory can be skipped.
    entries = []
    dirs = set()
    for tk in args.tkape:
        with open(tk, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        for t in doc["Targets"]:
            if t["Path"].lower().endswith(".tkape"):
                continue
            winpath = t["Path"].replace("%user%", args.user).rstrip("\\").replace("*", "wildcard") + "\\"
            entries.append((t, winpath))
            dirs.add(winpath.rstrip("\\").lower())
            if t.get("Recursive"):
                dirs.add((winpath + "nested\\deeper").lower())
                dirs.add((winpath + "nested").lower())

    expected = []
    for t, winpath in entries:
        for name in mask_to_names(t.get("FileMask")):
            if name in ("", "."):
                continue
            win_file = winpath + name
            if win_file.lower() in dirs:
                print(f"skip {win_file}: collides with a directory used by another entry")
                continue
            plant(win_to_local(win_file, args.root), f"fixture for {t['Name']}\n{win_file}\n")
            expected.append({"target": t["Name"], "win": win_file})
        if t.get("Recursive"):
            win_file = winpath + "nested\\deeper\\" + mask_to_names(t.get("FileMask"))[0]
            plant(win_to_local(win_file, args.root), f"nested fixture for {t['Name']}\n{win_file}\n")
            expected.append({"target": t["Name"], "win": win_file})

    decoys = []
    for d in args.decoy:
        win_file = d.replace("%user%", args.user)
        plant(win_to_local(win_file, args.root), f"DECOY - must not be collected\n{win_file}\n")
        decoys.append({"win": win_file})

    with open(args.manifest, "w", encoding="utf-8") as fh:
        json.dump({"user": args.user, "expected": expected, "decoys": decoys}, fh, indent=2)
    print(f"planted {len(expected)} expected files and {len(decoys)} decoys; manifest -> {args.manifest}")


if __name__ == "__main__":
    sys.exit(main())
