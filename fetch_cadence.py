#!/usr/bin/env python3
"""fetch_cadence.py — download a full BL ON/OFF *cadence* for one target.

`fetch_public_data.py bl` grabs the single smallest file for a target, which is
fine for a demo and useless for the test that actually matters. Breakthrough
Listen observes ABACAD — target, throwaway sky position, target, ... — and a
signal is only interesting if it appears in the ON scans and NOT in the OFF
scans. That comparison needs the whole set.

    python fetch_cadence.py --target GJ699 --n 6

Downloads land in data/ (gitignored). Files are ~1.3 GB each, so `--n 6` is
~8 GB: check `--dry-run` first. Resumes with `curl -C -`, so an interrupted pull
costs nothing.

Credit: Breakthrough Listen open data (Lebofsky et al. 2019 PASP 131:124505;
Price et al. 2020 AJ 159:86), Berkeley SETI Research Center.
"""
import argparse
import json
import os
import re
import subprocess
import time
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
API = "http://seti.berkeley.edu/opendata/api/query-files"


def query(target, limit=40):
    url = API + "?" + urllib.parse.urlencode(
        {"target": target, "file-types": "HDF5", "limit": limit})
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read()).get("data", [])


def classify(name):
    """ON or OFF from the filename. BL marks the throwaway sky positions with
    _OFF_ in the product name; everything else is a target scan."""
    return "OFF" if "_OFF_" in name.upper() else "ON"


def seq(name):
    """Sequence number of the POINTING within the session (…_GJ699_0005.gpuspec…).

    Deliberately anchored to the scan number that precedes '.gpuspec', because
    the product suffix also ends in four digits: a naive "last 4-digit group"
    rule reads 0000/0001/0002 (the RESOLUTION) as the scan number and happily
    returns three copies of the same pointing as a six-scan cadence.
    """
    m = re.search(r"_(\d{4})\.gpuspec", name)
    return int(m.group(1)) if m else -1


def product(name):
    """Which of the three BL data products this is.

    Each pointing is released three times at different resolutions, and picking
    the wrong one silently ruins a drift search:
      0000  ~3 Hz channels, ~18 s integrations  -> FINE FREQUENCY. Narrowband
            SETI needs this; it is also the 12.8 GB one.
      0001  high TIME resolution, coarse in frequency (~1.3 GB)
      0002  mid resolution (~0.2 GB)
    """
    if ".gpuspec.0000." in name:
        return "0000"
    if ".0001." in name:
        return "0001"
    if ".gpuspec.0002." in name:
        return "0002"
    return "?"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", default="GJ699")
    ap.add_argument("--n", type=int, default=6, help="how many files (cadence=6)")
    ap.add_argument("--product", default="0000",
                    choices=["0000", "0001", "0002"],
                    help="0000=fine frequency (~3 Hz, what drift "
                         "searches need), 0001=fine time, 0002=mid")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = query(a.target)
    if not rows:
        print(f"no HDF5 files for {a.target}", file=sys.stderr)
        return 1
    files = []
    for x in rows:
        u = x.get("url") or ""
        n = u.split("/")[-1]
        if n and product(n) == a.product:
            files.append(dict(url=u, name=n, size=x.get("size", 0),
                              kind=classify(n), seq=seq(n)))
    # ONE file per pointing, in observation order — otherwise the three
    # resolutions of a single scan masquerade as three scans.
    by_seq = {}
    for f in files:
        by_seq.setdefault(f["seq"], f)
    files = [by_seq[k] for k in sorted(by_seq)]
    pick = files[:a.n]
    if not pick:
        print(f"no product-{a.product} files for {a.target}", file=sys.stderr)
        return 1

    total = sum(f["size"] for f in pick) / 1e9
    print(f"{a.target}: {len(files)} pointing(s) with product {a.product}; "
          f"taking {len(pick)}")
    pattern = "".join("A" if f["kind"] == "ON" else "-" for f in pick)
    for f in pick:
        print(f"  seq {f['seq']:>4}  {f['kind']:<3}  {f['size']/1e9:5.2f} GB  "
              f"{f['name'][:60]}")
    print(f"  cadence pattern: {pattern}   total {total:.2f} GB")
    if pattern[:6] == "A-A-A-":
        print("  -> textbook ABACAD: ON/OFF alternating, the comparison that "
              "kills false positives")
    if a.dry_run:
        return 0

    DATA.mkdir(exist_ok=True)

    # ── SINGLE-WRITER LOCK (2026-07-30) ─────────────────────────────────────
    # Learned the expensive way: two copies of this script were started by
    # accident (a background launch that looked like it had failed, then a
    # relaunch). Both ran, both `curl -C -` onto the SAME filenames, and resume
    # semantics turned two writers into interleaved garbage — all six files came
    # out 158 MB to 1.4 GB OVERSIZED and unreadable past the second time row.
    # 80 GB of download thrown away for want of six lines.
    lock = DATA / ".fetch_cadence.lock"
    if lock.exists():
        try:
            age = time.time() - lock.stat().st_mtime
        except OSError:
            age = 0
        if age < 6 * 3600:
            print(f"another fetch_cadence appears to be running "
                  f"({lock}, {age/60:.0f} min old). Refusing to run a second "
                  f"writer — delete the lock if you are sure.", file=sys.stderr)
            return 2
    lock.write_text(str(os.getpid()), encoding="utf-8")

    got, bad = [], []
    try:
        for f in pick:
            out = DATA / f["name"]
            if out.exists():
                have = out.stat().st_size
                # EXACT size check, both directions. An oversized file is
                # corrupt (this is what a double-writer produces) and resuming
                # onto it appends yet more garbage, so it is deleted, not resumed.
                if have == f["size"]:
                    print(f"[have] {f['name']}", flush=True)
                    got.append(out)
                    continue
                if have > f["size"]:
                    print(f"[bad ] {f['name']} is {(have-f['size'])/1e6:+.0f} MB "
                          f"OVERSIZED — corrupt, deleting and refetching",
                          flush=True)
                    out.unlink()
                else:
                    print(f"[part] {f['name']} {have/1e9:.2f}/"
                          f"{f['size']/1e9:.2f} GB — resuming", flush=True)
            print(f"[get ] {f['name']}  ({f['size']/1e9:.2f} GB)", flush=True)
            rc = subprocess.run(["curl", "-L", "-C", "-", "--retry", "3",
                                 "--retry-delay", "5", "-o", str(out),
                                 f["url"]]).returncode
            size_ok = out.exists() and out.stat().st_size == f["size"]
            if rc == 0 and size_ok:
                got.append(out)
            else:
                actual = out.stat().st_size if out.exists() else 0
                print(f"[fail] {f['name']}: curl rc={rc}, size {actual/1e9:.2f} "
                      f"vs {f['size']/1e9:.2f} GB", flush=True)
                bad.append(f["name"])
    finally:
        lock.unlink(missing_ok=True)

    print(f"\ndownloaded {len(got)}/{len(pick)} into {DATA}")
    for g in got:
        print(f"  {g.name}  {g.stat().st_size/1e9:.2f} GB  OK")
    for b in bad:
        print(f"  {b}  FAILED")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
