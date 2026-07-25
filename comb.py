#!/usr/bin/env python3
"""comb.py - frequency-comb technosignature detector.

Nature makes tones. It rarely makes tones at PERFECTLY UNIFORM Hz spacing across
a wide band: molecular rotational lines, harmonics of a rotator, plasma lines -
none are uniform in Hz over a broad span. A set of equal-amplitude tones spaced
by a constant delta-f is the fingerprint of an engineered reference (an
optical/RF frequency comb, a channelized beacon) - a way to say "this is
manufactured" that survives Doppler (the whole comb shifts together, spacing
preserved) and needs no message.

Detection: a comb spaced delta-f Hz makes the POWER SPECTRUM itself periodic with
period delta-f. So the spectrum-of-the-spectrum (a cepstrum-like transform) peaks
at quefrency 1/delta-f. We take |FFT(power_spectrum - mean)|, find the strongest
peak, and reference it to the median - high only when the spectrum is genuinely
periodic. Crucially this fires on UNIFORM spacing and NOT on the same number of
randomly-spaced tones: it is a uniformity detector, not a multi-tone counter.

  python comb.py selftest        # uniform comb vs noise vs random-spaced tones
  python comb.py scan <iq.cs16> [fs]
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def detect(x, fs, qmin=8, lmin=5):
    """Return (spacing_hz, significance, depth).

    DECISION uses the cepstrum |FFT(power_spectrum)|: a UNIFORM comb makes the
    spectrum globally periodic, concentrating cepstral energy at harmonics of one
    quefrency (high peak/median); randomly-spaced tones scatter it flat (low). So
    the cepstral peak/median cleanly separates engineered uniformity from a mere
    pile of tones - which a single autocorrelation peak cannot.

    SPACING is then read from the spectrum's autocorrelation, whose fundamental
    lag D (bins) gives delta-f = D*fs/N directly, free of the harmonic ambiguity
    that fools a cepstral argmax."""
    P = np.abs(np.fft.fft(x)) ** 2
    N = len(P)
    P = P - P.mean()
    # --- discriminator: global spectral periodicity ---
    Q = np.abs(np.fft.rfft(P))
    qband = Q[qmin:]
    if len(qband) < 4:
        return 0.0, 0.0, 0
    sig = float(qband.max() / (np.median(qband) + 1e-12))
    # --- spacing: fundamental lag of the spectrum autocorrelation ---
    ac = np.fft.irfft(Q ** 2, n=N)[:N // 2]
    D = int(np.argmax(ac[lmin:])) + lmin
    spacing = D * (fs / N)
    depth = int(round(N / D)) if D else 0
    return spacing, sig, depth


def _comb(rng, N, fs, f0, df, n_teeth, amp):
    n = np.arange(N)
    x = np.zeros(N, np.complex128)
    for k in range(n_teeth):
        f = f0 + k * df
        ph = rng.uniform(0, 2 * np.pi)
        x += amp * np.exp(2j * np.pi * f / fs * n + 1j * ph)
    return x


def _random_tones(rng, N, fs, freqs, amp):
    n = np.arange(N)
    x = np.zeros(N, np.complex128)
    for f in freqs:
        ph = rng.uniform(0, 2 * np.pi)
        x += amp * np.exp(2j * np.pi * f / fs * n + 1j * ph)
    return x


def selftest():
    print("=" * 68)
    print("FREQUENCY-COMB DETECTOR selftest")
    print("  goal: fire on UNIFORM Hz-spaced tones (engineered), and NOT on")
    print("  pure noise OR the same count of randomly-spaced tones.")
    print("=" * 68)
    rng = np.random.default_rng(7)
    fs = 100_000.0
    N = 100_000

    def noise():
        return (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)

    # 1) false-alarm gate on pure noise
    fa = []
    for _ in range(12):
        _, s, _ = detect(noise(), fs)
        fa.append(s)
    thr = max(fa) * 1.3
    print(f"pure noise: comb significance max {max(fa):.1f} over 12 trials"
          f"  -> threshold {thr:.1f}")

    n_teeth, df = 15, 3000.0
    amp = 0.6                        # each tooth modest vs unit-variance noise

    # 2) a real uniform comb in noise
    ok_comb = 0
    for trial in range(3):
        x = _comb(rng, N, fs, -21_000.0, df, n_teeth, amp) + noise()
        sp, sig, depth = detect(x, fs)
        hit = sig >= thr and abs(sp - df) < 300
        ok_comb += hit
        print(f"  uniform comb ({n_teeth} teeth @ {df:.0f} Hz): "
              f"detected spacing {sp:.0f} Hz sig {sig:.1f} -> "
              f"{'DETECTED' if hit else 'miss'}")

    # 3) CONTROL: same number of tones, RANDOM spacing -> must NOT fire
    false_fire = 0
    for trial in range(3):
        freqs = rng.uniform(-40_000, 40_000, n_teeth)
        x = _random_tones(rng, N, fs, freqs, amp) + noise()
        sp, sig, depth = detect(x, fs)
        fired = sig >= thr
        false_fire += fired
        print(f"  random-spaced {n_teeth} tones (CONTROL): sig {sig:.1f} -> "
              f"{'FALSE FIRE' if fired else 'correctly silent'}")

    ok = ok_comb >= 2 and false_fire == 0 and thr < 12
    print("=" * 68)
    print(f"RESULT: comb {ok_comb}/3 detected, {false_fire}/3 false fires on "
          f"random tones. {'PASS - detects engineered uniformity' if ok else 'NEEDS WORK'}")
    return 0 if ok else 1


def scan_file(path, fs=250_000.0, nmax=4_000_000):
    raw = np.fromfile(path, np.int16, count=2 * nmax).astype(np.float32) / 32768.0
    x = (raw[0::2] + 1j * raw[1::2]).astype(np.complex64)
    sp, sig, depth = detect(x, fs)
    print(f"{Path(path).name}: strongest comb spacing {sp:.0f} Hz, "
          f"significance {sig:.1f}"
          + ("  <- possible frequency comb" if sig > 10 else "  (no uniform comb)"))


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "scan":
        fs = float(sys.argv[3]) if len(sys.argv) >= 4 else 250_000.0
        scan_file(sys.argv[2], fs)
    else:
        sys.exit(selftest())


if __name__ == "__main__":
    main()
