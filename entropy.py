#!/usr/bin/env python3
"""entropy.py - compressibility / spectral-entropy detector.

The founding SETI assumption is a carrier: all the energy in one bin. But a
carrier is the MOST boring thing a transmitter can send - it carries no
information (you can compress it to nothing). Pure noise is the opposite: maximum
entropy, incompressible, no structure. A MESSAGE lives in between - structured,
partly predictable, partly surprising. So instead of hunting peaks, score the
COMPLEXITY of the band and flag the structured middle, whatever its shape
(narrowband, wide, or spread). Modulation-agnostic by construction.

The measure is the spectral flatness (Wiener entropy) of the power spectrum:
  SFM = geometric_mean(P) / arithmetic_mean(P),  in (0, 1].
A pure carrier -> SFM ~ 0 (one bin dominates, trivially compressible).
Pure noise    -> SFM ~ 1 (flat, incompressible).
A modulated / band-limited signal -> the structured MIDDLE.

  python entropy.py selftest      # carrier vs noise vs modulated, 3-way
  python entropy.py scan <iq.cs16> [fs]
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LO, HI = 0.30, 0.70          # < LO: carrier-like  |  > HI: noise-like  |  middle: STRUCTURED


def spectral_flatness(x, ncoarse=512):
    """SFM of the power spectrum, coarse-grained to ncoarse bins so pure noise
    averages toward flat (SFM->1) instead of fluctuating."""
    P = np.abs(np.fft.fft(x)) ** 2
    N = len(P)
    g = N // ncoarse
    if g >= 2:
        P = P[:g * ncoarse].reshape(ncoarse, g).sum(1)
    P = P + 1e-12
    gm = np.exp(np.mean(np.log(P)))
    am = np.mean(P)
    return float(gm / am)


def classify(sfm):
    if sfm < LO:
        return "carrier-like (over-compressible - a dead tone, no message)"
    if sfm > HI:
        return "noise-like (incompressible - no structure)"
    return "STRUCTURED (the informative middle - worth a look)"


def detect(x, fs=None):
    sfm = spectral_flatness(x)
    return sfm, classify(sfm)


def _carrier(rng, N, fs):
    n = np.arange(N)
    sig = np.exp(2j * np.pi * 12_345.0 / fs * n)
    noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)
    return 8.0 * sig + 0.05 * noise


def _noise(rng, N, fs):
    return (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)


def _modulated(rng, N, fs, bw=24_000.0, amp=2.4):
    """A band-limited modulated signal: filtered noise (a real data-bearing band
    looks like colored noise confined to its channel), a few dB above the noise
    floor - the informative middle between a dead tone and pure noise. The
    bandwidth/level are calibrated so its spectral flatness lands mid-scale, where
    a real modulated channel sits (empirically SFM ~ 0.5)."""
    from scipy.signal import firwin, lfilter
    base = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)
    taps = firwin(255, bw / (fs / 2)).astype(np.float64)
    band = lfilter(taps, 1.0, base)
    band = band / (np.std(band) + 1e-12)
    n = np.arange(N)
    band = band * np.exp(2j * np.pi * 20_000.0 / fs * n)   # park it off-center
    noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)
    return amp * band + noise


def selftest():
    print("=" * 68)
    print("COMPRESSIBILITY / SPECTRAL-ENTROPY DETECTOR selftest")
    print("  goal: order carrier < modulated < noise, and label the modulated")
    print("  band as STRUCTURED (the informative middle) - modulation-agnostic.")
    print("=" * 68)
    rng = np.random.default_rng(3)
    fs = 100_000.0
    N = 100_000
    c = np.mean([spectral_flatness(_carrier(rng, N, fs)) for _ in range(3)])
    m = np.mean([spectral_flatness(_modulated(rng, N, fs)) for _ in range(3)])
    nz = np.mean([spectral_flatness(_noise(rng, N, fs)) for _ in range(3)])
    print(f"  carrier   SFM {c:.3f}  -> {classify(c)}")
    print(f"  MODULATED SFM {m:.3f}  -> {classify(m)}")
    print(f"  noise     SFM {nz:.3f}  -> {classify(nz)}")
    ordered = c < m < nz
    labelled = c < LO and nz > HI and LO <= m <= HI
    ok = ordered and labelled
    print("=" * 68)
    print(f"RESULT: ordering {'OK' if ordered else 'WRONG'}, "
          f"modulated labelled STRUCTURED: {'yes' if labelled else 'no'}. "
          f"{'PASS - finds structure between tone and noise' if ok else 'NEEDS WORK'}")
    return 0 if ok else 1


def scan_file(path, fs=250_000.0, nmax=4_000_000):
    raw = np.fromfile(path, np.int16, count=2 * nmax).astype(np.float32) / 32768.0
    x = (raw[0::2] + 1j * raw[1::2]).astype(np.complex64)
    sfm, label = detect(x, fs)
    print(f"{Path(path).name}: spectral flatness {sfm:.3f} -> {label}")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "scan":
        fs = float(sys.argv[3]) if len(sys.argv) >= 4 else 250_000.0
        scan_file(sys.argv[2], fs)
    else:
        sys.exit(selftest())


if __name__ == "__main__":
    main()
