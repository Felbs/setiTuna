#!/usr/bin/env python3
"""agent.py - the novel-detector ensemble: try every way of being artificial.

turboSETI asks one question ("is there a narrowband carrier?"). This asks all the
questions past SETI didn't - in parallel, on the same data:

  - cyclo   : is there SPREAD structure (hidden symbol/chip periodicity)?
  - comb    : is there a UNIFORM frequency comb (engineered reference)?
  - entropy : is there BAND-LIMITED structure (a message between tone and noise)?

Each detector is orthogonal - it catches a signal class the others (and a drift
search) are blind to. The agent runs the whole panel on a capture, applies each
detector's own honest gate, and reports a combined verdict. A signal only has to
trip ONE detector to be worth a human's attention; nothing is thresholded away
silently. New detectors from NOVEL_DETECTORS.md drop into DETECTORS and are
picked up automatically - that is how the panel grows toward "try everything."

  python agent.py <iq.cs16> [fs]     # run the full panel on a capture
  python agent.py selftest           # regression-gate every detector at once
"""
import sys
from pathlib import Path

import numpy as np

import cyclo
import comb
import entropy

HERE = Path(__file__).resolve().parent

# name -> (module, gate(result)->fired?, describe(result)->str)
DETECTORS = [
    ("cyclo (spread / cyclostationary)",
     lambda x, fs: cyclo.detect(x, fs),
     lambda r: r[1] >= 8.0,
     lambda r: f"chip/symbol rate {r[0]:.0f} Hz, significance {r[1]:.1f}"),
    ("comb (uniform frequency comb)",
     lambda x, fs: comb.detect(x, fs),
     lambda r: r[1] >= 10.0,
     lambda r: f"spacing {r[0]:.0f} Hz, significance {r[1]:.1f}"),
    ("entropy (band-limited structure)",
     lambda x, fs: entropy.detect(x, fs),
     lambda r: entropy.LO <= r[0] <= entropy.HI,
     lambda r: f"spectral flatness {r[0]:.3f} -> {r[1]}"),
]


def load_iq(path, nmax=4_000_000):
    raw = np.fromfile(path, np.int16, count=2 * nmax).astype(np.float32) / 32768.0
    return (raw[0::2] + 1j * raw[1::2]).astype(np.complex64)


def run_panel(path, fs):
    x = load_iq(path)
    print(f"\n=== novel-detector panel: {Path(path).name} "
          f"({len(x)/fs:.2f}s @ {fs/1e6:.3f} MHz) ===")
    fired = []
    for name, run, gate, describe in DETECTORS:
        try:
            r = run(x, fs)
            hit = gate(r)
        except Exception as e:
            print(f"  [{name}] error: {str(e)[:50]}")
            continue
        flag = "  <== FIRED" if hit else ""
        print(f"  {name:38s} {describe(r)}{flag}")
        if hit:
            fired.append(name)
    print(f"  verdict: {len(fired)} detector(s) fired"
          + (f" -> {', '.join(n.split()[0] for n in fired)} - worth a look"
             if fired else " - nothing artificial-without-a-carrier here"))
    return fired


def selftest():
    """Regression-gate the whole suite: every detector must pass its own test."""
    import subprocess
    print("=" * 68)
    print("NOVEL-DETECTOR SUITE regression gate")
    print("=" * 68)
    results = {}
    for mod in ("cyclo", "comb", "entropy"):
        rc = subprocess.run([sys.executable, str(HERE / f"{mod}.py"), "selftest"],
                            capture_output=True, text=True).returncode
        results[mod] = rc == 0
        print(f"  {mod:10s} selftest: {'PASS' if rc == 0 else 'FAIL'}")
    ok = all(results.values())
    print("=" * 68)
    print(f"SUITE: {sum(results.values())}/{len(results)} detectors green. "
          f"{'ALL PASS' if ok else 'REGRESSION'}")
    return 0 if ok else 1


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "selftest":
        sys.exit(selftest())
    elif len(sys.argv) >= 2:
        fs = float(sys.argv[2]) if len(sys.argv) >= 3 else 250_000.0
        run_panel(sys.argv[1], fs)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
