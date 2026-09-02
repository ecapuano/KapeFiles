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

    expected = []
    for tk in args.tkape:
        with open(tk, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        for t in doc["Targets"]:
            if t["Path"].lower().endswith(".tkape"):
                continue
            winpath = t["Path"].replace("%user%", args.user).rstrip("\\") + "\\"
            for name in mask_to_names(t.get("FileMask")):
                if not name or name.startswith("."):
                    if name in ("", "."):
                        continue
                win_file = winpath + name
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
