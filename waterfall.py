#!/usr/bin/env python3
"""waterfall.py - see the signal. Spectrograms, overlays, and two views that
standard SETI plotting tools do not give you.

A waterfall (dynamic spectrum) is time down, frequency across, power as colour.
Every phenomenon in SETI_HISTORY.md has a SHAPE in this plane, and the overlays
here draw the shape the physics predicts on top of the data so you can see
whether it fits:

  plot     the spectrogram + its integrated spectrum
             --drift R      straight lines at R Hz/s   (technosignature / RFI)
             --dm D         the quadratic dispersion sweep for DM=D (FRB/pulsar)
             --mark f,f,..   candidate markers in MHz
             --log-freq     logarithmic frequency axis (for wide bands)
             --norm         divide out the instrument bandpass first
  hough    DRIFT-RATE vs FREQUENCY space - the de-Doppler plane itself. Every
           pixel is "how bright is this frequency if I assume this drift rate".
           A real drifting tone is a compact blob OFF the zero-drift row; local
           interference is a hard vertical stripe ON the zero-drift row. One
           picture that separates "sky" from "us".
  cadence  the ON/OFF/ON/OFF/ON/OFF strip. Breakthrough Listen's verification
           pattern, drawn: a signal from the target appears only in the ON
           panels. This is the plot that killed BLC-1 (Sheikh et al. 2021).
  fold     phase-folded profile at a trial period - how a pulsar is actually
           seen, since single pulses are usually buried in the noise.

  python waterfall.py plot data/star_GJ699.h5 --f-start 1420.2 --f-stop 1420.7 \
        --norm --out figures/hi.png
  python waterfall.py hough synth:drift --out figures/hough.png
  python waterfall.py cadence ON=a.h5 OFF=b.h5 ON=c.h5 OFF=d.h5 --out cad.png
  python waterfall.py fold synth:pulsar --period 0.714 --out figures/fold.png

Colour: one perceptually-uniform sequential ramp (viridis) for magnitude - never
a rainbow, which invents edges that are not in the data. Overlays use a small
fixed set of high-contrast annotation colours and are always labelled, so the
meaning never rests on colour alone.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402

import seti_io                                                    # noqa: E402
from seti_io import DM_CONST, HI_MHZ                              # noqa: E402

HERE = Path(__file__).resolve().parent
FIGDIR = HERE / "figures"

# --- one sequential ramp for magnitude, a fixed annotation set for overlays ---
CMAP = "viridis"
INK = "#1c1c1c"
MUTED = "#6b6b6b"
GRID = "#d8d8d8"
ANN = ["#e8590c", "#0b7285", "#a61e4d", "#5f3dc4"]   # drift / dispersion / marks

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "grid.color": GRID,
    "axes.grid": False, "font.size": 9, "axes.titlesize": 10,
    "figure.dpi": 110, "savefig.bbox": "tight",
})


def _img(ax, spec, db=True, pct=(5, 99.5)):
    d = np.asarray(spec.data, np.float64)
    if db:
        d = 10 * np.log10(np.maximum(d, np.nanmax(d) * 1e-9) + 1e-30)
    lo, hi = np.percentile(d, pct)
    f = spec.freqs_mhz()
    t = spec.times_s()
    im = ax.imshow(d, aspect="auto", origin="upper", cmap=CMAP, vmin=lo, vmax=hi,
                   extent=[f[0], f[-1], t[-1], t[0]], interpolation="nearest")
    ax.set_xlabel("frequency (MHz)")
    ax.set_ylabel("time (s)")
    return im


def _decimate_for_plot(spec, max_chan=2400, max_time=900):
    ff = max(1, spec.nchan // max_chan)
    tf = max(1, spec.ntime // max_time)
    return spec.decimate(tfac=tf, ffac=ff) if (ff > 1 or tf > 1) else spec


def plot(spec, out, drift=None, dm=None, marks=None, log_freq=False, norm=False,
         title=None, db=True):
    """Waterfall + integrated spectrum, with physics overlays."""
    if norm:
        spec = spec.bandpass_normalized()
    s = _decimate_for_plot(spec)
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(9.2, 6.4), sharex=True,
                                  gridspec_kw=dict(height_ratios=[3, 1.15],
                                                   hspace=0.06))
    im = _img(ax, s, db=db)
    ax.set_xlabel("")                 # shared axis: only ax2 is labelled
    cb = fig.colorbar(im, ax=[ax, ax2], pad=0.015, fraction=0.045)
    cb.set_label("power (dB, relative)" if db else "power")
    cb.outline.set_edgecolor(MUTED)

    f = s.freqs_mhz()
    t = s.times_s()
    handles = []
    if drift:
        for k, r in enumerate(np.atleast_1d(drift)):
            fc = marks[0] if marks else 0.5 * (f[0] + f[-1])
            ax.plot(fc + r * (t - t[0]) / 1e6, t, lw=1.6, ls="--",
                    color=ANN[0], alpha=0.9 - 0.2 * k,
                    label=f"drift {r:+.3f} Hz/s")
        handles = ax.get_legend_handles_labels()[0]
    if dm:
        for k, D in enumerate(np.atleast_1d(dm)):
            # arrival time vs frequency, referenced to the top of the band
            t_sweep = t[0] + DM_CONST * D * (f ** -2 - f[-1] ** -2)
            ax.plot(f, t_sweep, lw=1.8, color=ANN[1], ls="-", alpha=0.85,
                    label=f"DM {D:g} pc cm$^{{-3}}$ sweep")
        handles = ax.get_legend_handles_labels()[0]
    if marks:
        for m in np.atleast_1d(marks):
            ax.axvline(m, color=ANN[2], lw=1.0, ls=":", alpha=0.9)
            ax2.axvline(m, color=ANN[2], lw=1.0, ls=":", alpha=0.9)
        ax2.plot([], [], color=ANN[2], ls=":", label="candidate")
    if handles:
        ax.legend(loc="upper right", framealpha=0.9, fontsize=8)

    sp = s.integrated()
    ax2.plot(f, sp, lw=1.0, color=INK)
    ax2.set_xlabel("frequency (MHz)")
    ax2.set_ylabel("mean power" + (" / continuum" if norm else ""))
    ax2.grid(True, lw=0.4, alpha=0.6)
    if log_freq:
        ax.set_xscale("log")
        ax2.set_xscale("log")
    if ax2.get_legend_handles_labels()[0]:
        ax2.legend(loc="upper right", fontsize=8, framealpha=0.9)

    m = spec.meta
    ax.set_title(title or (f"{m.get('source_name','?')} - {m.get('telescope','?')} - "
                           f"{m.get('origin','')}\n{spec.f_lo:.4f}-{spec.f_hi:.4f} MHz, "
                           f"{spec.res_hz:.2f} Hz channels, {spec.duration_s:.0f} s"),
                 loc="left")
    return _save(fig, out)


def hough(spec, out, max_drift=4.0, ndrift=161, title=None, mark_zero=True):
    """Drift-rate vs frequency space: the de-Doppler plane, drawn.

    NOVEL VIEW. Standard tools give you a hit LIST out of a drift search; this
    gives you the search's whole parameter space as an image. Signals separate by
    SHAPE: a genuine sky tone is a blob at non-zero drift, ground-based
    interference is a stripe pinned to drift = 0, and a chirping satellite is a
    smear along the drift axis."""
    d = np.asarray(spec.data, np.float64)
    nt, nch = d.shape
    t = spec.times_s() - spec.t0_s
    res = spec.res_hz
    drifts = np.linspace(-max_drift, max_drift, ndrift)
    plane = np.empty((ndrift, nch))
    for k, r in enumerate(drifts):
        shift = np.round(r * t / res).astype(int)
        acc = np.zeros(nch)
        for i in range(nt):
            acc += np.roll(d[i], -shift[i])
        med = np.median(acc)
        mad = np.median(np.abs(acc - med)) or 1.0
        plane[k] = (acc - med) / (1.4826 * mad)

    f = spec.freqs_mhz()
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    lo, hi = np.percentile(plane, (5, 99.9))
    im = ax.imshow(plane, aspect="auto", origin="lower", cmap=CMAP,
                   vmin=lo, vmax=max(hi, 6),
                   extent=[f[0], f[-1], drifts[0], drifts[-1]],
                   interpolation="nearest")
    if mark_zero:
        ax.axhline(0.0, color=ANN[0], lw=1.0, ls="--", alpha=0.9)
        ax.text(f[-1], 0.0, "drift = 0: bolted to the ground with us  ",
                color=ANN[0], va="bottom", ha="right", fontsize=8)
    k, c = np.unravel_index(np.argmax(plane), plane.shape)
    ax.plot(f[c], drifts[k], "o", ms=9, mfc="none", mec=ANN[2], mew=1.6)
    ax.annotate(f"peak {plane[k,c]:.0f}$\\sigma$ @ {f[c]:.6f} MHz, "
                f"{drifts[k]:+.3f} Hz/s", (f[c], drifts[k]),
                textcoords="offset points",
                xytext=(12, 12 if drifts[k] < 0 else -18), fontsize=8,
                color=ANN[2],
                ha="left" if f[c] < 0.6 * f[-1] + 0.4 * f[0] else "right")
    ax.set_xlabel("frequency (MHz)")
    ax.set_ylabel("trial drift rate (Hz/s)")
    cb = fig.colorbar(im, ax=ax, pad=0.015, fraction=0.045)
    cb.set_label("de-drifted significance (robust $\\sigma$)")
    cb.outline.set_edgecolor(MUTED)
    ax.set_title(title or f"drift-rate / frequency plane - "
                          f"{spec.meta.get('source_name','?')} "
                          f"({spec.meta.get('origin','')})", loc="left")
    return _save(fig, out)


def cadence(specs, roles, out, f_start=None, f_stop=None, mark=None, norm=False,
            title=None):
    """ON/OFF cadence strip - the standard SETI verification pattern, drawn.

    NOVEL VIEW (for a hobbyist toolkit): six panels sharing one frequency axis,
    ON scans tinted, OFF scans plain. A candidate is only interesting if it is
    present in every ON panel and absent from every OFF panel. Anything visible
    in an OFF panel is local. This is the picture that ended BLC-1."""
    n = len(specs)
    fig, axes = plt.subplots(1, n, figsize=(2.35 * n + 1.2, 4.4), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, sp, role in zip(axes, specs, roles):
        s = sp.bandpass_normalized() if norm else sp
        if f_start or f_stop:
            s = s.crop(f_start, f_stop)
        s = _decimate_for_plot(s, max_chan=600, max_time=400)
        _img(ax, s, db=True)
        ax.set_title(f"{role.upper()}\n{s.meta.get('source_name','?')}",
                     loc="left", fontsize=9,
                     color=ANN[0] if role.upper() == "ON" else MUTED)
        if role.upper() == "ON":
            for sp_ in ax.spines.values():
                sp_.set_color(ANN[0])
                sp_.set_linewidth(1.6)
        if mark:
            for m in np.atleast_1d(mark):
                ax.axvline(m, color=ANN[2], lw=1.0, ls=":", alpha=0.9)
        ax.set_xlabel("MHz")
        ax.set_ylabel("time (s)" if ax is axes[0] else "")
        ax.tick_params(labelsize=7)
        ax.xaxis.set_major_locator(plt.MaxNLocator(3))
    fig.suptitle(title or "ON/OFF cadence - a real signal appears ONLY in the "
                          "ON panels (orange)", x=0.01, ha="left", fontsize=10)
    return _save(fig, out)


def fold(spec, out, period_s, nbins=64, dm=0.0, title=None):
    """Phase-folded profile at a trial period, plus the phase-vs-time stack -
    how a pulsar is actually detected (single pulses are usually invisible)."""
    s = spec.dedisperse(dm) if dm else spec
    ph, prof = s.fold(period_s, nbins=nbins)
    _, wrong = s.fold(period_s * 1.37, nbins=nbins)
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(7.4, 5.4),
                                  gridspec_kw=dict(height_ratios=[1, 1.4],
                                                   hspace=0.28))
    ax.step(np.concatenate([ph, ph + 1]), np.concatenate([prof, prof]),
            where="mid", lw=1.3, color=INK, label=f"folded at {period_s:g} s")
    ax.step(np.concatenate([ph, ph + 1]), np.concatenate([wrong, wrong]),
            where="mid", lw=1.0, color=MUTED, alpha=0.75,
            label=f"control: wrong period ({period_s*1.37:g} s)")
    ax.set_xlabel("pulse phase (two cycles shown)")
    ax.set_ylabel("mean power")
    ax.legend(fontsize=8, framealpha=0.9)
    ax.grid(True, lw=0.4, alpha=0.6)

    # phase vs pulse-number stack: is the pulse there EVERY rotation?
    ts = s.timeseries()
    t = s.times_s()
    npulse = max(2, int(t[-1] / period_s))
    stack = np.full((npulse, nbins), np.nan)
    idx = ((t / period_s) % 1.0 * nbins).astype(int)
    pnum = (t / period_s).astype(int)
    for i in range(len(ts)):
        if pnum[i] < npulse:
            stack[pnum[i], idx[i]] = ts[i]
    im = ax2.imshow(np.nan_to_num(stack, nan=np.nanmedian(stack)), aspect="auto",
                    origin="lower", cmap=CMAP, extent=[0, 1, 0, npulse],
                    interpolation="nearest")
    ax2.set_xlabel("pulse phase")
    ax2.set_ylabel("rotation number")
    cb = fig.colorbar(im, ax=ax2, pad=0.015, fraction=0.045)
    cb.set_label("power")
    cb.outline.set_edgecolor(MUTED)
    ax.set_title(title or f"period fold - {spec.meta.get('source_name','?')} "
                          f"@ P={period_s:g} s"
                          + (f", DM={dm:g}" if dm else ""), loc="left")
    return _save(fig, out)


def figure_set(outdir=None):
    """Regenerate every figure used by SETI_HISTORY.md and the README.

    Synthetic scenes are generated from the formulae quoted in the document, so
    the teaching figures need NO download and are reproducible by anyone. Figures
    that need real data are made only if that data is present in data/ (which is
    gitignored - fetch it yourself, see fetch_public_data.py)."""
    out = Path(outdir or FIGDIR)
    out.mkdir(parents=True, exist_ok=True)
    made = []

    # 1. the four canonical SHAPES, synthetic, side by side
    scenes = [
        ("drift", dict(kind="drift", ntime=64, nchan=1024, f0_mhz=1400.0,
                       df_mhz=2.79e-6, drift_hz_s=-1.2, snr=14),
         "TECHNOSIGNATURE (or RFI): narrowband, DRIFTING\n"
         "a tone on a rotating planet - here -1.2 Hz/s over 64 s"),
        ("frb", dict(kind="frb", ntime=900, nchan=384, f0_mhz=1100.0, df_mhz=2.0,
                     dt_s=0.002, dm=560, snr=25, t_s=0.15),
         "FAST RADIO BURST: broadband, milliseconds, DISPERSED\n"
         "t = 4.1488 ms x DM x nu_GHz^-2   (DM 560, teal = the prediction)"),
        ("pulsar", dict(kind="pulsar", ntime=760, nchan=128, f0_mhz=300.0,
                        df_mhz=1.0, dt_s=0.005, period_s=0.714, dm=26.8, snr=15.0),
         "PULSAR: the same dispersed sweep, but PERIODIC\n"
         "P = 0.714 s, DM 26.8 (PSR B0329+54-like), VHF band"),
        ("maser", dict(kind="maser", ntime=64, nchan=2048, f0_mhz=1665.3,
                       df_mhz=1e-4, snr=30),
         "ASTROPHYSICAL MASER: narrow, bright, NO drift\n"
         "nature's own carrier - OH 1665 MHz, ~3 kHz wide"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11.4, 7.6))
    for ax, (name, kw, cap) in zip(axes.ravel(), scenes):
        s = seti_io.synth(**kw)
        _img(ax, _decimate_for_plot(s, 400, 300), db=False, pct=(60, 99.9))
        ax.set_title(cap, loc="left", fontsize=8.5)
        ax.tick_params(labelsize=7)
        ax.xaxis.set_major_locator(plt.MaxNLocator(4))
        if name == "frb":
            f = s.freqs_mhz()
            ax.plot(f, kw["t_s"] + DM_CONST * kw["dm"] *
                    (f ** -2 - f[-1] ** -2), lw=1.2, color=ANN[1], alpha=0.75)
    fig.suptitle("Four things you will actually see in a SETI waterfall "
                 "(synthetic, from the physics in SETI_HISTORY.md)",
                 x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    made.append(_save(fig, out / "signature_atlas.png"))

    # 2. the drift-rate plane, with a real sky tone AND a zero-drift RFI stripe
    s = seti_io.synth("drift", ntime=128, nchan=1024, f0_mhz=1400.0,
                      df_mhz=2.79e-6, drift_hz_s=-2.0, snr=10, seed=2,
                      f_mhz=1400.0 + 2.79e-6 * 620)
    rfi = seti_io.synth("zerodrift", ntime=128, nchan=1024, f0_mhz=1400.0,
                        df_mhz=2.79e-6, snr=10, seed=3,
                        f_mhz=1400.0 + 2.79e-6 * 250)
    s.data = s.data + rfi.data - 1.0
    s.meta["source_name"] = "SYNTH drifting tone (-2 Hz/s) + zero-drift RFI"
    made.append(hough(s, out / "hough_drift_plane.png", max_drift=3.0, ndrift=161,
                      title="drift-rate / frequency plane: a sky tone sits OFF the "
                            "zero-drift row, local interference sits ON it"))

    # 3. pulsar fold
    ps = seti_io.synth("pulsar", ntime=4000, nchan=64, f0_mhz=1300.0, df_mhz=1.0,
                       dt_s=0.005, period_s=0.714, dm=26.8, snr=1.1, seed=4)
    ps.meta["source_name"] = "SYNTH pulsar (B0329+54-like)"
    made.append(fold(ps, out / "pulsar_fold.png", 0.714, nbins=48, dm=26.8,
                     title="folding is how a pulsar becomes visible: 0.714 s "
                           "period recovers a profile the raw data hides"))

    # 4. a synthetic ON/OFF cadence, the way BL verifies everything
    on = [seti_io.synth("drift", ntime=48, nchan=512, f0_mhz=1400.0,
                        df_mhz=2.79e-6, drift_hz_s=-0.4, snr=14, seed=10 + i)
          for i in range(3)]
    off = [seti_io.synth("noise", ntime=48, nchan=512, f0_mhz=1400.0,
                         df_mhz=2.79e-6, seed=20 + i) for i in range(3)]
    for i, s_ in enumerate(on):
        s_.meta["source_name"] = "target"
    for i, s_ in enumerate(off):
        s_.meta["source_name"] = "off-target sky"
    seq = [on[0], off[0], on[1], off[1], on[2], off[2]]
    made.append(cadence(seq, ["ON", "OFF", "ON", "OFF", "ON", "OFF"],
                        out / "cadence_pattern.png",
                        title="ON/OFF/ON/OFF/ON/OFF: the verification pattern. "
                              "A candidate must be in every ON and no OFF."))

    # 5-6. real data, only if the user has downloaded it
    real = HERE / "data" / "star_GJ699.h5"
    if real.exists():
        sp = seti_io.load_bl(real, f_start=1420.15, f_stop=1420.75)
        made.append(plot(sp, out / "hi_line_gj699.png", norm=True,
                         marks=[HI_MHZ],
                         title="REAL DATA: galactic neutral hydrogen in a "
                               "Breakthrough Listen SETI observation\n"
                               "(GBT L-band, target GJ699/Barnard's Star; dotted "
                               "line = 1420.405752 MHz rest frequency)"))
    voy = HERE / "data" / "Voyager1.single_coarse.fine_res.h5"
    if voy.exists():
        sp = seti_io.load_bl(voy, f_start=8419.26, f_stop=8419.34)
        made.append(plot(sp, out / "voyager1.png", norm=False,
                         title="REAL DATA: Voyager 1 from 19 billion km - the one "
                               "confirmed interstellar-distance technosignature\n"
                               "(GBT X-band; carrier + telemetry sidebands, "
                               "drifting -0.38 Hz/s)"))
        # zoom on the carrier so the DRIFT itself is visible, with the drift rate
        # turboSETI measured drawn on top (data/Voyager1...dat: -0.377557 Hz/s)
        z = seti_io.load_bl(voy, f_start=8419.2955, f_stop=8419.2985)
        made.append(plot(z, out / "voyager1_drift.png", drift=[-0.377557],
                         marks=[8419.297028],
                         title="REAL DATA, zoomed: the Voyager 1 carrier DRIFTING\n"
                               "dashed line = -0.377557 Hz/s from 8419.297028 MHz, "
                               "the drift turboSETI measured\n(our own loader "
                               "re-measures -0.3776 Hz/s from the same file)"))
        made.append(hough(sp.decimate(ffac=4), out / "voyager1_hough.png",
                          max_drift=1.0, ndrift=121,
                          title="Voyager 1 in the drift-rate plane: a real "
                                "spacecraft carrier sits OFF the zero-drift row"))
    print(f"\n{len(made)} figure(s) in {out}")
    return made


def _save(fig, out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    print(f"wrote {out}  ({out.stat().st_size/1e3:.0f} kB)")
    return out


# ------------------------------------------------------------------- CLI
def _open(path, args):
    kw = {}
    if getattr(args, "fs", None):
        kw["fs"] = args.fs
    if Path(str(path)).suffix.lower() in (".h5", ".hdf5", ".fil"):
        for a in ("f_start", "f_stop", "t_start", "t_stop"):
            v = getattr(args, a, None)
            if v is not None:
                kw[a] = v
    return seti_io.open_any(path, **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    def common(p, data=True):
        if data:
            p.add_argument("data")
        p.add_argument("--out", default=None)
        p.add_argument("--fs", type=float)
        p.add_argument("--f-start", type=float)
        p.add_argument("--f-stop", type=float)
        p.add_argument("--t-start", type=float)
        p.add_argument("--t-stop", type=float)
        p.add_argument("--title")

    p = sub.add_parser("plot")
    common(p)
    p.add_argument("--drift", type=float, nargs="*")
    p.add_argument("--dm", type=float, nargs="*")
    p.add_argument("--mark", type=float, nargs="*")
    p.add_argument("--log-freq", action="store_true")
    p.add_argument("--norm", action="store_true")
    p.add_argument("--linear", action="store_true", help="linear power, not dB")

    p = sub.add_parser("hough")
    common(p)
    p.add_argument("--max-drift", type=float, default=4.0)
    p.add_argument("--ndrift", type=int, default=161)

    p = sub.add_parser("cadence")
    p.add_argument("pointings", nargs="+", help="ON=file OFF=file ...")
    common(p, data=False)
    p.add_argument("--mark", type=float, nargs="*")
    p.add_argument("--norm", action="store_true")

    p = sub.add_parser("fold")
    common(p)
    p.add_argument("--period", type=float, required=True)
    p.add_argument("--nbins", type=int, default=64)
    p.add_argument("--dm", type=float, default=0.0)

    p = sub.add_parser("figures", help="regenerate every documentation figure")
    p.add_argument("--outdir")

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 0
    FIGDIR.mkdir(exist_ok=True)
    if args.cmd == "figures":
        figure_set(args.outdir)
        return 0
    if args.cmd == "cadence":
        roles, paths = zip(*(i.partition("=")[::2] for i in args.pointings))
        specs = [_open(pp, args) for pp in paths]
        if args.f_start or args.f_stop:
            specs = [s for s in specs]
        cadence(specs, roles, args.out or FIGDIR / "cadence.png",
                f_start=args.f_start, f_stop=args.f_stop, mark=args.mark,
                norm=args.norm, title=args.title)
        return 0
    spec = _open(args.data, args)
    stem = Path(str(args.data).replace(":", "_")).stem
    out = args.out or FIGDIR / f"{stem}_{args.cmd}.png"
    if args.cmd == "plot":
        plot(spec, out, drift=args.drift, dm=args.dm, marks=args.mark,
             log_freq=args.log_freq, norm=args.norm, title=args.title,
             db=not args.linear)
    elif args.cmd == "hough":
        hough(spec, out, max_drift=args.max_drift, ndrift=args.ndrift,
              title=args.title)
    elif args.cmd == "fold":
        fold(spec, out, args.period, nbins=args.nbins, dm=args.dm,
             title=args.title)
    return 0


if __name__ == "__main__":
    sys.exit(main())
