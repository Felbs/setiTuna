#!/usr/bin/env python3
"""sideband_pairs.py - search turboSETI hit lists for MODULATION STRUCTURE.

Every drift search hunts isolated lines. This hunts what a data-carrying
transmitter actually looks like (cf. our Voyager detection: carrier + two
symmetric sidebands, drifting in lockstep): PAIRS of hits at f0 +/- delta
sharing a common drift rate, and TRIPLETS where the center hit exists too.
A lone spike can be anything; a drift-locked symmetric family is a machine.

  python sideband_pairs.py data/*.dat
"""
import glob
import sys

DRIFT_TOL = 0.06        # Hz/s - pair members must drift together
SYM_TOL_HZ = 200.0      # symmetry tolerance for (f1+f2)/2 vs a center hit
MAX_SPLIT_HZ = 200e3    # widest plausible sideband spacing to consider


def load_hits(path):
    hits = []
    for ln in open(path):
        if ln.startswith("#") or not ln.strip():
            continue
        f = ln.split()
        # turboSETI .dat: idx, drift, snr, freq(corr), freq(uncorr), index, ...
        hits.append(dict(drift=float(f[1]), snr=float(f[2]), mhz=float(f[3])))
    return hits


def families(hits):
    out = []
    n = len(hits)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = hits[i], hits[j]
            split = abs(a["mhz"] - b["mhz"]) * 1e6
            if not (10.0 < split < MAX_SPLIT_HZ):
                continue
            if abs(a["drift"] - b["drift"]) > DRIFT_TOL:
                continue
            center = (a["mhz"] + b["mhz"]) / 2
            # is there a center hit? (-> triplet = carrier + sidebands)
            carrier = None
            for c in hits:
                if c is a or c is b:
                    continue
                if abs(c["mhz"] - center) * 1e6 < SYM_TOL_HZ and \
                   abs(c["drift"] - (a["drift"] + b["drift"]) / 2) < DRIFT_TOL:
                    carrier = c
                    break
            out.append(dict(kind="TRIPLET" if carrier else "PAIR",
                            center_mhz=round(center, 6),
                            split_khz=round(split / 2e3, 3),
                            drift=round((a["drift"] + b["drift"]) / 2, 4),
                            snrs=[round(a["snr"], 1), round(b["snr"], 1)]
                                 + ([round(carrier["snr"], 1)] if carrier else [])))
    return out


def main():
    paths = sys.argv[1:] or glob.glob("data/*.dat")
    for p in paths:
        hits = load_hits(p)
        fams = families(hits)
        print(f"=== {p}: {len(hits)} hits -> {len(fams)} symmetric families ===")
        for f in fams:
            print(f"  {f['kind']}: center {f['center_mhz']} MHz, sidebands "
                  f"+/-{f['split_khz']} kHz, common drift {f['drift']} Hz/s, "
                  f"SNRs {f['snrs']}"
                  + ("   <-- carrier + data sidebands: a TRANSMITTER"
                     if f["kind"] == "TRIPLET" else ""))
        if not fams:
            print("  (no modulation structure found)")


if __name__ == "__main__":
    main()
