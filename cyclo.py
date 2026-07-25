#!/usr/bin/env python3
"""cyclo.py - cyclostationary technosignature detector (the "hiss with a heartbeat").

turboSETI hunts NARROWBAND carriers - the signals a 1950s-Earth civilization
leaks. But every DIGITAL signal (which is what we, and presumably anyone past
their radio infancy, actually transmit) carries hidden PERIODICITIES in its
second-order statistics - the symbol/chip rate - even when it is spread so wide
it looks like pure noise in the power spectrum. That is cyclostationarity, and
it is invisible to any spectrum-based search.

This detects it via the cyclic autocorrelation: at lag tau, the sequence
r_tau[n] = x[n]*conj(x[n-tau]) carries a periodic component at alpha = symbol/
chip rate whenever x is digitally keyed - even a constant-envelope, spread,
sub-noise signal that is FLAT in the power spectrum. |FFT(r_tau)| peaks there;
pure noise peaks nowhere. We scan a ladder of lags, report the strongest cyclic
feature and a noise-referenced significance, with a false-alarm gate calibrated
on pure noise.

  python cyclo.py selftest        # spread-spectrum below the noise floor vs noise
  python cyclo.py scan <iq.cs16>  # scan a real capture

The honest frontier: a search that only finds carriers can only find a
civilization exactly as advanced as we were in 1950. This finds the rest.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def detect(x, fs, amin=300.0, taus=(1, 2, 4, 8, 16, 32, 64, 128)):
    """Cyclic-autocorrelation detector via FFT (fast + exact). For a lag tau,
    r_tau[n] = x[n] * conj(x[n-tau]); its Fourier transform IS the cyclic
    autocorrelation as a function of cycle frequency alpha. A digital/spread
    signal - even constant-envelope BPSK invisible in the power spectrum - has a
    periodic component in r_tau at alpha = symbol/chip rate (for tau within the
    pulse), so |FFT(r_tau)| PEAKS there. Pure noise has no such peak at any tau.
    We scan a ladder of lags and take the strongest cyclic feature.
    Returns (best_alpha_hz, significance, best_tau)."""
    best = (0.0, 0.0, 0)
    L = len(x)
    amin_bin = max(1, int(amin / (fs / L)))
    for tau in taus:
        if tau >= L:
            continue
        r = x[tau:] * np.conj(x[:-tau])
        r = r - r.mean()                       # kill the alpha=0 (DC power) line
        R = np.abs(np.fft.fft(r))
        m = len(R)
        hi = m // 2                            # positive cycle frequencies
        band = R[amin_bin:hi]
        if len(band) < 4:
            continue
        med = np.median(band) + 1e-12
        k = int(np.argmax(band)) + amin_bin
        sig = R[k] / med
        if sig > best[1]:
            alpha = k * fs / m
            best = (alpha, float(sig), tau)
    return best[0], best[1], best[2]


def _spread_signal(rng, nsamp, fs, chiprate, snr_db):
    """A direct-sequence spread BPSK: iid +-1 chips at a FAST chiprate, so the
    power is smeared across chiprate Hz - noise-like in the spectrum (no single
    bin stands out, a narrowband search sees nothing) - yet cyclostationary at
    alpha = chiprate. Constant envelope (the hard case for a cyclo detector)."""
    sps = max(1, int(round(fs / chiprate)))
    nchip = nsamp // sps + 2
    chips = rng.choice([-1.0, 1.0], nchip)
    sig = np.repeat(chips, sps)[:nsamp].astype(np.complex64)
    amp = 10 ** (snr_db / 20)
    noise = (rng.standard_normal(nsamp) + 1j * rng.standard_normal(nsamp)) / np.sqrt(2)
    return (amp * sig + noise).astype(np.complex64), fs / sps


def selftest():
    print("=" * 68)
    print("CYCLOSTATIONARY DETECTOR selftest")
    print("  goal: catch a spread signal BELOW the noise floor that is INVISIBLE")
    print("  to a power-spectrum search, while never firing on pure noise.")
    print("=" * 68)
    rng = np.random.default_rng(11)
    fs = 100_000.0
    N = 200_000
    # 1) FALSE-ALARM gate: pure complex noise must not produce a cyclic peak
    sigs = []
    for i in range(12):
        noise = ((rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)).astype(np.complex64)
        _, s, _ = detect(noise, fs)
        sigs.append(s)
    fa_thresh = max(sigs) * 1.3
    print(f"pure noise: cyclic significance max {max(sigs):.1f} over 12 trials"
          f"  -> detection threshold set to {fa_thresh:.1f}")
    # 2) can it catch a spread signal the SPECTRUM can't see?
    hits = 0
    for snr in (-3, -6, -10):
        x, chip = _spread_signal(rng, N, fs, chiprate=25_000.0, snr_db=snr)
        # is it invisible in the power spectrum? (flat -> a narrowband search misses it)
        P = np.abs(np.fft.fft(x)) ** 2
        spec_peakiness = P.max() / np.median(P)
        a, sig, tau = detect(x, fs)
        found = sig >= fa_thresh and abs(a - chip) < 600
        hits += found
        print(f"  spread BPSK @ {snr:+d} dB SNR: spectrum peak/med={spec_peakiness:5.0f}x "
              f"(narrowband search {'would catch' if spec_peakiness>25 else 'MISSES'}) | "
              f"cyclo found chip-rate {a:.0f} Hz (tau {tau}) sig {sig:.1f} -> "
              f"{'DETECTED' if found else 'miss'}")
    ok = hits >= 2 and fa_thresh < 15
    print("=" * 68)
    print(f"RESULT: cyclo caught {hits}/3 sub-noise spread signals, "
          f"FA-gated. {'PASS - hears what turboSETI cannot' if ok else 'NEEDS WORK'}")
    return 0 if ok else 1


def scan_file(path, fs=250_000.0, nmax=4_000_000):
    raw = np.fromfile(path, np.int16, count=2 * nmax).astype(np.float32) / 32768.0
    x = (raw[0::2] + 1j * raw[1::2]).astype(np.complex64)
    a, sig, tau = detect(x, fs)
    print(f"{Path(path).name}: strongest cyclic feature at alpha={a:.0f} Hz (tau {tau}), "
          f"significance {sig:.1f}"
          + ("  <- possible digital/modulated signal" if sig > 8 else "  (no strong cyclostationarity)"))


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "scan":
        fs = float(sys.argv[3]) if len(sys.argv) >= 4 else 250_000.0
        scan_file(sys.argv[2], fs)
    else:
        sys.exit(selftest())


if __name__ == "__main__":
    main()
