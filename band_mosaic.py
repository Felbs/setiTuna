#!/usr/bin/env python3
"""band_mosaic.py — the WHOLE band in one picture, by wrapping frequency onto rows.

A BL fine scan is 264,503,296 channels x 16 integrations. As a conventional
waterfall that is a 4.2-gigapixel strip 2.8 km wide at screen DPI, so every
normal plot of it is a 0.1% crop. But the frequency axis does not have to be one
long line: wrap it like text on a page and the entire 750 MHz fits on a screen.

Each ROW is one coarse channel (2.93 MHz); x within the row is frequency inside
that channel; brightness is power, time-averaged over the scan. Reading down the
page is tuning across the band.

The layout earns its keep rather than just being pretty: because every row is the
same width as the instrument's own coarse channel, anything belonging to the
INSTRUMENT lines up vertically down the page, while anything belonging to the SKY
does not. The polyphase filterbank's roll-off becomes two clean vertical edges,
and that is the same structure the coarse-channel veto in recipe_api keys on.

    python band_mosaic.py --scan <file.h5> --out band.png
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

COARSE_MHZ = 2.9296875


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scan", required=True)
    ap.add_argument("--out", default="band_mosaic.png")
    ap.add_argument("--cols", type=int, default=1400, help="pixels per row")
    ap.add_argument("--f-start", type=float, default=None)
    ap.add_argument("--f-stop", type=float, default=None)
    a = ap.parse_args()

    import hdf5plugin          # noqa: F401  (BL bitshuffle)
    import h5py
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    f = h5py.File(a.scan, "r")
    d = f["data"]
    at = dict(d.attrs)
    fch1 = float(at["fch1"])
    foff = float(at["foff"])
    ntime, _, nchan = d.shape
    # frequency ascending
    f_lo = min(fch1, fch1 + foff * nchan)
    f_hi = max(fch1, fch1 + foff * nchan)
    lo = a.f_start if a.f_start is not None else f_lo
    hi = a.f_stop if a.f_stop is not None else f_hi
    per_row = int(round(COARSE_MHZ / abs(foff)))
    nrows = int((hi - lo) / COARSE_MHZ)
    print(f"{Path(a.scan).name}")
    print(f"  band {f_lo:.3f}-{f_hi:.3f} MHz, {nchan:,} channels, {ntime} integrations")
    print(f"  mosaic: {nrows} rows x {a.cols} px  (one row = {COARSE_MHZ:.4f} MHz "
          f"= {per_row:,} channels averaged to {a.cols})")

    img = np.zeros((nrows, a.cols), np.float32)
    t0 = time.time()
    for r in range(nrows):
        # channel index of this row's start (freq ascending vs stored order)
        fr = lo + r * COARSE_MHZ
        # BL stores frequency DESCENDING (foff < 0), so the channel index of the
        # row's low edge is the LARGER index. Compute both ends and order them;
        # the previous version swapped c0/c1 and then sliced [c0:c1] with c0 > c1,
        # which silently yields an empty slice for every row and writes a blank
        # image in zero seconds.
        ca = int(round((fr - fch1) / foff))
        cb = int(round((fr + COARSE_MHZ - fch1) / foff))
        c0, c1 = (ca, cb) if ca < cb else (cb, ca)
        c0 = max(0, min(nchan - 1, c0))
        c1 = max(0, min(nchan, c1))
        if c1 - c0 < a.cols:
            continue
        acc = np.zeros(c1 - c0, np.float64)
        for t in range(ntime):                       # row-at-a-time: one chunk
            acc += d[t, 0, c0:c1]
        acc /= ntime
        if foff < 0:
            acc = acc[::-1]
        n = (len(acc) // a.cols) * a.cols
        img[r] = acc[:n].reshape(a.cols, -1).mean(1)
        if r % 40 == 0:
            el = time.time() - t0
            print(f"   row {r:>3}/{nrows}  {fr:8.2f} MHz   "
                  f"eta {el/(r+1)*(nrows-r-1):5.0f}s", flush=True)

    # per-row normalisation: every coarse channel has its own gain, and without
    # this the picture is a map of the receiver's gain curve, not of the sky.
    med = np.median(img, axis=1, keepdims=True)
    med[med <= 0] = 1.0
    shown = 10 * np.log10(np.maximum(img / med, 1e-6))

    fig, ax = plt.subplots(figsize=(14, 9), dpi=130)
    v0, v1 = np.percentile(shown, (2, 99.7))
    im = ax.imshow(shown, aspect="auto", cmap="viridis", vmin=v0, vmax=v1,
                   extent=[0, COARSE_MHZ, lo + nrows * COARSE_MHZ, lo])
    ax.set_xlabel("frequency WITHIN each 2.9297 MHz coarse channel (MHz)")
    ax.set_ylabel("band frequency (MHz)  —  each row is one coarse channel")
    ax.set_title(f"{Path(a.scan).name[:44]}\n"
                 f"the whole {hi-lo:.0f} MHz in one picture: "
                 f"{nchan:,} channels wrapped onto {nrows} rows")
    fig.colorbar(im, ax=ax, label="dB relative to that row's median")
    # HI line marker
    hi_line = 1420.405751768
    if lo < hi_line < lo + nrows * COARSE_MHZ:
        row_f = lo + int((hi_line - lo) / COARSE_MHZ) * COARSE_MHZ
        ax.plot([(hi_line - row_f)], [row_f + COARSE_MHZ / 2], "r<", ms=9)
        ax.annotate("HI 21cm", xy=((hi_line - row_f), row_f), color="red",
                    fontsize=9, xytext=(4, -6), textcoords="offset points")
    fig.tight_layout()
    fig.savefig(a.out)
    print(f"\nwrote {a.out}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
