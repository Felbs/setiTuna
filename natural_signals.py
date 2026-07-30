#!/usr/bin/env python3
"""natural_signals.py - find the ASTROPHYSICS hiding in your SETI data.

Point a technosignature search at the sky and it does not come back empty. It
comes back full of nature - and 65 years of SETI history is largely the story of
people learning to recognise what nature does (SETI_HISTORY.md). This tool does
that recognition on the Breakthrough Listen files you have already downloaded:

  1. HYDROGEN. Every L-band SETI observation contains the galaxy's own 21 cm
     line at 1420.405751768 MHz. This measures it, and converts the observed
     frequency into a VELOCITY - first topocentric, then (with astropy, optional)
     barycentric- and LSR-corrected, which is the number an astronomer quotes.
  2. THE DISCRIMINATOR. Given two or more files, it separates SKY features from
     INSTRUMENT features by the oldest trick there is: a feature at the SAME
     topocentric frequency in two different pointings on two different days is
     ours; a feature that MOVES with the pointing direction is the galaxy's.
     This is the same logic as the ON/OFF cadence, applied to spectral lines.
  3. THE ARTIFACTS. Coarse-channel edges, notch filters and DC spikes, so you
     stop mistaking the spectrometer for the universe.

  python natural_signals.py data/star_GJ699.h5
  python natural_signals.py data/star_*.h5 --figure figures/hi_survey.png

astropy is OPTIONAL: without it you get topocentric velocities and a warning
instead of LSR velocities. Nothing here needs a GPU or a telescope.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

import seti_io
from seti_io import HI_MHZ, C_KMS

HERE = Path(__file__).resolve().parent

# Green Bank Telescope, the site of most BL open data (public coordinates).
GBT = dict(lon_deg=-79.8398, lat_deg=38.4331, height_m=807.0)
TELESCOPE_SITES = {"GBT": GBT}

# Standard solar motion w.r.t. the LSR, Schoenrich, Binney & Dehnen 2010
# (MNRAS 403, 1829): (U, V, W) = (11.1, 12.24, 7.25) km/s.
SOLAR_UVW = (11.1, 12.24, 7.25)


def sky_frame(meta):
    """Galactic coordinates + the corrections that turn a topocentric frequency
    into an LSR velocity. Returns a dict; astropy is optional."""
    out = dict(ok=False, note="astropy not installed - topocentric velocities only")
    ra_hr, dec_deg = meta.get("ra_hr"), meta.get("dec_deg")
    mjd = meta.get("tstart_mjd")
    if ra_hr is None or dec_deg is None:
        return dict(ok=False, note="no pointing in the file header")
    try:
        import warnings
        warnings.filterwarnings("ignore")
        from astropy.coordinates import SkyCoord, EarthLocation
        from astropy.time import Time
        import astropy.units as u
    except ImportError:
        return out
    c = SkyCoord(ra=ra_hr * 15 * u.deg, dec=dec_deg * u.deg, frame="icrs")
    g = c.galactic
    l, b = g.l.rad, g.b.rad
    U, V, W = SOLAR_UVW
    v_lsr_proj = (U * np.cos(l) * np.cos(b) + V * np.sin(l) * np.cos(b)
                  + W * np.sin(b))
    bary = 0.0
    note = "no tstart in header - barycentric correction skipped"
    if mjd:
        site = TELESCOPE_SITES.get(meta.get("telescope", ""), GBT)
        loc = EarthLocation.from_geodetic(lon=site["lon_deg"] * u.deg,
                                         lat=site["lat_deg"] * u.deg,
                                         height=site["height_m"] * u.m)
        bary = float(c.radial_velocity_correction(
            kind="barycentric", obstime=Time(mjd, format="mjd"),
            location=loc).to(u.km / u.s).value)
        note = ("v_LSR = v_topocentric + barycentric correction + solar motion "
                "projection")
    return dict(ok=True, l_deg=float(g.l.deg), b_deg=float(g.b.deg),
                bary_kms=bary, solar_lsr_kms=float(v_lsr_proj),
                total_kms=bary + float(v_lsr_proj), note=note)


def hi_profile(path, halfwidth_mhz=2.0, smooth_kms=4.0):
    """Bandpass-normalised HI profile in VELOCITY space. Returns
    (velocity_topocentric_kms, profile_over_continuum, spectrogram, meta)."""
    s = seti_io.load_bl(path, f_start=HI_MHZ - halfwidth_mhz,
                        f_stop=HI_MHZ + halfwidth_mhz)
    n = s.bandpass_normalized()
    f = n.freqs_mhz()
    sp = n.integrated()
    w = max(1, int(round((smooth_kms / C_KMS * HI_MHZ) / s.df_mhz)))
    from scipy.ndimage import uniform_filter1d
    sp = uniform_filter1d(sp, w, mode="nearest")
    v = -C_KMS * (f - HI_MHZ) / HI_MHZ
    return v, sp, s, s.meta


def report(path, halfwidth_mhz=2.0, verbose=True):
    """Everything natural in one file."""
    import recipe_api as R
    res = {}
    s_full = seti_io.load_bl(path, max_chans=1 << 21)
    m = s_full.meta
    frame = sky_frame(m)
    res["file"] = str(path)
    res["header"] = s_full.summary()
    res["frame"] = frame
    if verbose:
        print("=" * 74)
        print(f"{Path(path).name}   source {m.get('source_name')}  "
              f"telescope {m.get('telescope')}")
        print(f"  band {s_full.f_lo:.4f}-{s_full.f_hi:.4f} MHz, "
              f"{s_full.res_hz:.2f} Hz channels, {s_full.duration_s:.0f} s, "
              f"MJD {m.get('tstart_mjd')}")
        if frame.get("ok"):
            print(f"  pointing: galactic l={frame['l_deg']:.2f} deg "
                  f"b={frame['b_deg']:+.2f} deg   "
                  f"v_LSR = v_topo {frame['total_kms']:+.2f} km/s "
                  f"(barycentric {frame['bary_kms']:+.2f}, "
                  f"solar {frame['solar_lsr_kms']:+.2f})")
        else:
            print(f"  pointing frame: {frame.get('note')}")

    # --- the spectral lines nature puts there ---------------------------------
    lines = []
    if s_full.f_lo - 2 < HI_MHZ < s_full.f_hi + 2:
        v, sp, s, _ = hi_profile(path, halfwidth_mhz)
        rec = R.get("hi_line_natural")
        cands, _ = rec.run(s)
        for c in cands:
            v_topo = c.provenance["velocity_kms_topocentric"]
            d = dict(line=c.provenance["line"], freq_mhz=c.freq_mhz,
                     v_topocentric_kms=v_topo,
                     v_lsr_kms=(round(v_topo + frame["total_kms"], 2)
                                if frame.get("ok") else None),
                     fwhm_kms=c.provenance["fwhm_kms"],
                     peak_over_continuum=c.provenance["peak_over_continuum"],
                     z=round(c.score, 1))
            lines.append(d)
            if verbose:
                lsr = (f"{d['v_lsr_kms']:+.1f} km/s LSR" if d["v_lsr_kms"] is not None
                       else "LSR unavailable")
                print(f"  LINE  {d['line']:26s} {d['freq_mhz']:.5f} MHz  "
                      f"{v_topo:+7.1f} km/s topo -> {lsr}  "
                      f"x{d['peak_over_continuum']:.2f} continuum, "
                      f"FWHM {d['fwhm_kms']:.0f} km/s, {d['z']:.0f} sigma")
        if verbose and not cands:
            print("  LINE  no HI detected above threshold in this pointing "
                  "(high galactic latitude / low column density?)")
    res["lines"] = lines

    # --- the artifacts the SPECTROMETER puts there ----------------------------
    art = coarse_channel_artifacts(s_full)
    res["artifacts"] = art
    if verbose:
        if art["coarse_width_mhz"]:
            print(f"  ARTIFACT  coarse-channel structure every "
                  f"{art['coarse_width_mhz']:.3f} MHz "
                  f"({art['n_dips']} band-edge dips found) - the spectrometer's "
                  f"own shape, not the sky")
        else:
            print("  ARTIFACT  no obvious coarse-channel periodicity")
    return res


def coarse_channel_artifacts(spec, ndip_max=64):
    """BL's GPU spectrometer splits the band into coarse channels (2.9 MHz at
    GBT) whose EDGES roll off. Those periodic dips are the single most common
    'feature' in BL data, and they are pure instrument. Find their period."""
    sp = spec.integrated()
    n = len(sp)
    if n < 512:
        return dict(coarse_width_mhz=None, n_dips=0)
    from scipy.ndimage import median_filter
    base = median_filter(sp, min(n - 1 | 1, 2001), mode="nearest")
    r = sp / np.where(base > 0, base, 1.0)
    dips = np.where(r < 0.85)[0]
    if len(dips) < 2:
        return dict(coarse_width_mhz=None, n_dips=int(len(dips)))
    # group contiguous dips, then take the modal spacing between groups
    groups = [[dips[0]]]
    for d in dips[1:]:
        (groups[-1] if d - groups[-1][-1] <= 8 else groups.append([d]) or groups[-1]).append(d)
    centres = np.array([np.mean(g) for g in groups])
    if len(centres) < 2:
        return dict(coarse_width_mhz=None, n_dips=len(groups))
    gaps = np.diff(centres) * spec.df_mhz
    return dict(coarse_width_mhz=float(np.median(gaps)), n_dips=int(len(groups)),
                dip_freqs_mhz=[round(float(spec.f0_mhz + c * spec.df_mhz), 4)
                               for c in centres[:24]])


def discriminate(paths, tol_khz=20.0, halfwidth_mhz=2.0, verbose=True):
    """SKY or INSTRUMENT? The oldest test in radio astronomy.

    A feature at the SAME topocentric frequency in independent pointings taken
    on different days cannot be the sky - the sky Doppler-shifts with Earth's
    motion and changes with direction. A feature whose frequency MOVES between
    pointings is celestial. Run this over several downloads and the galaxy
    separates itself from the receiver."""
    import recipe_api as R
    rec = R.get("hi_line_natural")
    per_file = []
    for p in paths:
        try:
            s = seti_io.load_bl(p, f_start=HI_MHZ - halfwidth_mhz,
                                f_stop=HI_MHZ + halfwidth_mhz)
        except Exception as e:
            if verbose:
                print(f"  {Path(p).name}: skipped ({type(e).__name__}: {e})")
            continue
        cands, _ = rec.run(s)
        frame = sky_frame(s.meta)
        per_file.append((Path(p).name, s.meta, frame, cands))

    freqs = {}
    for name, meta, frame, cands in per_file:
        for c in cands:
            key = round(c.freq_mhz, 4)
            freqs.setdefault(key, []).append((name, meta, frame, c))
    tol = tol_khz / 1e3
    # cluster by topocentric frequency
    keys = sorted(freqs)
    clusters = []
    for k in keys:
        if clusters and k - clusters[-1][-1] <= tol:
            clusters[-1].append(k)
        else:
            clusters.append([k])
    verdicts = []
    for cl in clusters:
        members = [m for k in cl for m in freqs[k]]
        names = sorted({m[0] for m in members})
        fmean = float(np.mean([m[3].freq_mhz for m in members]))
        # how many of the loaded files actually COVER this frequency? A
        # non-detection only counts as evidence if the file could have seen it.
        covering = [n for n, meta, fr, cs in per_file]
        if len(names) > 1:
            v = ("INSTRUMENTAL / RFI: same topocentric frequency in "
                 f"{len(names)} independent pointings - the sky cannot do that")
        elif len(covering) > 1:
            v = (f"SKY: present in {names[0]} and ABSENT from the "
                 f"{len(covering)-1} other pointing(s) covering this frequency")
        else:
            v = ("UNTESTED: only one loaded file covers this frequency - "
                 "download another pointing to discriminate")
        verdicts.append(dict(freq_mhz=round(fmean, 5), files=names,
                             n_files_covering=len(covering), verdict=v))

    if verbose:
        print("=" * 74)
        print("SKY-or-INSTRUMENT discriminator "
              f"({len(per_file)} file(s), {tol_khz:g} kHz tolerance)")
        print("=" * 74)
        for name, meta, frame, cands in per_file:
            gl = (f"l={frame['l_deg']:6.2f} b={frame['b_deg']:+6.2f}"
                  if frame.get("ok") else "no coords")
            for c in cands:
                v_topo = c.provenance["velocity_kms_topocentric"]
                lsr = (f"{v_topo + frame['total_kms']:+7.1f}"
                       if frame.get("ok") else "      ?")
                print(f"  {meta.get('source_name','?'):8s} {gl}  "
                      f"{c.freq_mhz:.5f} MHz  v_topo {v_topo:+7.1f}  "
                      f"v_LSR {lsr} km/s  x{c.provenance['peak_over_continuum']:.2f}")
        print("-" * 74)
        for v in verdicts:
            print(f"  {v['freq_mhz']:.5f} MHz  {v['verdict']}")
            print(f"      seen in: {', '.join(v['files'])}")
    return verdicts, per_file


def figure(paths, out, halfwidth_mhz=1.2):
    """The money plot: HI profiles from several pointings, in LSR velocity.

    If these are real galactic hydrogen, the profiles must DIFFER between
    pointings in exactly the way galactic rotation predicts - strong and
    velocity-shifted near the plane, weak at high galactic latitude. If they
    were instrumental they would lie on top of each other."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from waterfall import INK, MUTED, GRID, ANN

    plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white",
                         "text.color": INK, "axes.labelcolor": INK,
                         "axes.edgecolor": MUTED, "xtick.color": MUTED,
                         "ytick.color": MUTED, "font.size": 9,
                         "figure.dpi": 110, "savefig.bbox": "tight"})
    fig, ax = plt.subplots(figsize=(9.0, 5.0))
    colours = ANN + ["#2b8a3e", "#495057"]
    n = 0
    for i, p in enumerate(paths):
        try:
            v, sp, s, meta = hi_profile(p, halfwidth_mhz)
        except Exception:
            continue
        frame = sky_frame(meta)
        shift = frame["total_kms"] if frame.get("ok") else 0.0
        lab = (f"{meta.get('source_name','?')}  "
               + (f"l={frame['l_deg']:.0f}$^\\circ$ b={frame['b_deg']:+.0f}$^\\circ$"
                  if frame.get("ok") else "(no LSR correction)"))
        ax.plot(v + shift, sp, lw=1.3, color=colours[i % len(colours)], label=lab)
        n += 1
    ax.axvline(0.0, color=MUTED, lw=0.8, ls=":")
    ax.text(0.0, ax.get_ylim()[1], " 0 km/s LSR", color=MUTED, fontsize=8,
            va="top")
    ax.set_xlabel("velocity w.r.t. the Local Standard of Rest (km s$^{-1}$)")
    ax.set_ylabel("power / local continuum")
    ax.grid(True, lw=0.4, color=GRID)
    ax.legend(fontsize=8, framealpha=0.9)
    ax.set_title("REAL DATA: galactic neutral hydrogen inside Breakthrough Listen "
                 "SETI observations\n"
                 "the 21 cm line moves and weakens with galactic coordinates - "
                 "which is how you know it is the sky, not the receiver\n"
                 "(broad symmetric DIPS and the hair-thin spikes are instrumental: "
                 "coarse-channel edges and RFI, not gas)",
                 loc="left", fontsize=9.5)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    print(f"wrote {out} ({n} profile(s), {out.stat().st_size/1e3:.0f} kB)")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="BL .h5/.fil files (default: data/*.h5)")
    ap.add_argument("--figure", help="write the LSR-velocity HI figure here")
    ap.add_argument("--halfwidth", type=float, default=2.0, help="MHz around HI")
    ap.add_argument("--no-report", action="store_true")
    args = ap.parse_args()
    paths = args.files or [r["path"] for r in seti_io.list_data()]
    paths = [p for p in paths if Path(p).suffix.lower() in (".h5", ".hdf5", ".fil")]
    if not paths:
        print("no BL files found - see fetch_public_data.py / star_sweep.py")
        return 1
    if not args.no_report:
        for p in paths:
            try:
                report(p, args.halfwidth)
            except Exception as e:
                print(f"{Path(p).name}: {type(e).__name__}: {e}")
    if len(paths) > 1:
        discriminate(paths, halfwidth_mhz=args.halfwidth)
    if args.figure:
        figure(paths, args.figure)
    return 0


if __name__ == "__main__":
    sys.exit(main())
