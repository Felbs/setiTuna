#!/usr/bin/env python3
"""hi_annotated.py — the HI-line window with every feature named.

Three things stand up out of the noise in 1419.9-1421.0 MHz of the GJ699 scan,
and they are three DIFFERENT kinds of thing. Naming them is the whole lesson:

  1420.000000 MHz   2 channels wide (5.7 Hz)   an oscillator / clock harmonic.
                    Exactly round in human units, which nature has no reason to
                    prefer. This is what recipe_api.round_number_reason catches.

  1420.605    MHz   ~7,300 channels (21 kHz)   the galactic HI 21 cm line —
                    neutral hydrogen in our own galaxy. BROAD because it is warm
                    turbulent gas spread over a range of velocities, and offset
                    from the 1420.405752 MHz rest frequency by the cloud's
                    motion toward us.

  1420.898438 MHz   2 channels wide (5.7 Hz)   the instrument's own coarse-
                    channel centre spike: 1420.8984375 = 485 x 2.9296875 MHz
                    EXACTLY. It is the same artifact that draws one vertical
                    line down every row of band_mosaic.py, 256 times.

The width is the tell. A 5.7 Hz feature at 1.4 GHz is a fractional bandwidth of
4e-9; no astrophysical process is that monochromatic, so anything that narrow is
built by somebody — either a transmitter or our own receiver.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

HI_REST = 1420.405751768
COARSE = 2.9296875


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seti_io

    P = (HERE / "data" /
         "spliced_blc02030405_2bit_guppi_57457_48006_GJ699_0003.gpuspec.0000.h5")
    sp = seti_io.open_any(str(P), f_start=1419.9, f_stop=1421.0)
    d, f = sp.data, sp.freqs_mhz()
    s = sp.integrated()
    nchan_true = len(f)

    # decimate ONLY for drawing, and say so on the figure — the plot is ~1400
    # columns for 388,000 channels, so each column is an average of ~277 of them.
    NCOL = 1400
    n = (nchan_true // NCOL) * NCOL
    img = d[:, :n].reshape(d.shape[0], NCOL, -1).mean(2)
    spec = s[:n].reshape(NCOL, -1).mean(1)
    fcol = f[:n].reshape(NCOL, -1).mean(1)
    per_col = n // NCOL

    fig, (ax, bx) = plt.subplots(
        2, 1, figsize=(13, 8.5), dpi=130, sharex=True,
        gridspec_kw=dict(height_ratios=[2.2, 1], hspace=0.06))

    db = 10 * np.log10(np.maximum(img / np.median(img), 1e-6))
    v0, v1 = np.percentile(db, (5, 99.6))
    ax.imshow(db, aspect="auto", cmap="viridis", vmin=v0, vmax=v1,
              extent=[fcol[0], fcol[-1], sp.duration_s, 0])
    ax.set_ylabel("time (s)")
    ax.set_title("Barnard's Star (GJ 699) — 1.1 MHz of a 750 MHz scan\n"
                 f"{nchan_true:,} channels @ {abs(sp.res_hz):.3f} Hz, "
                 f"{d.shape[0]} x {sp.dt_s:.1f} s = {sp.duration_s:.0f} s total")

    bx.plot(fcol, spec / np.median(spec), lw=0.9, color="k")
    bx.set_xlabel("frequency (MHz)")
    bx.set_ylabel("power / median")
    bx.grid(alpha=0.3)

    ann = [
        (1420.000000, "1420.000000 MHz — EXACTLY round\n"
                      "5.7 Hz wide (2 channels)\n"
                      "oscillator / clock harmonic", "tab:red", 40),
        (1420.6053, "galactic HYDROGEN, 21 cm\n"
                    "~21 kHz wide (7,300 channels)\n"
                    "rest 1420.405752 -> moving at -42 km/s", "tab:orange", -60),
        (1420.898438, "1420.898438 = 485 x 2.9296875 MHz\n"
                      "5.7 Hz wide (2 channels)\n"
                      "instrument coarse-channel spike", "tab:cyan", 40),
    ]
    for fx, txt, col, dx in ann:
        for a_ in (ax, bx):
            a_.axvline(fx, color=col, lw=0.9, ls="--", alpha=0.85)
        bx.annotate(txt, xy=(fx, 1.0), xytext=(dx, 46),
                    textcoords="offset points", fontsize=7.6, color=col,
                    ha="center",
                    arrowprops=dict(arrowstyle="->", color=col, lw=0.9),
                    bbox=dict(boxstyle="round,pad=0.3", fc="white",
                              ec=col, alpha=0.9))
    bx.text(0.5, -0.30,
            f"NOTE: drawn at {NCOL} columns, so each column averages {per_col} "
            f"channels — individual 2.8 Hz channels are NOT resolved here. "
            f"The search runs on the full {nchan_true:,}.",
            transform=bx.transAxes, ha="center", fontsize=8, style="italic")
    fig.tight_layout()
    out = HERE / "hi_line_annotated.png"
    fig.savefig(out, bbox_inches="tight")
    print(f"wrote {out}")
    print(f"  window {f[0]:.4f}-{f[-1]:.4f} MHz, {nchan_true:,} channels")
    print(f"  drawn at {NCOL} cols -> {per_col} channels averaged per column")
    print(f"  duration {sp.duration_s:.1f} s ({d.shape[0]} x {sp.dt_s:.3f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
