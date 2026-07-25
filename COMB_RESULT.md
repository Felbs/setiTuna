# EXP-15 — frequency-comb detector: catching engineered uniformity

**Hypothesis.** Nature makes tones, but almost never tones at *perfectly uniform
Hz spacing* across a wide band (molecular lines, harmonics, plasma lines are none
of them uniform in Hz over a broad span). A constant-delta-f comb is the
fingerprint of an engineered frequency reference — Doppler-robust (the whole comb
shifts together, spacing preserved), message-free, unmistakably manufactured.

**Method.** A comb spaced delta-f Hz makes the *power spectrum itself* periodic.
Two transforms, each doing one job:
- **Decision** — the cepstrum |FFT(power spectrum)|. A uniform comb concentrates
  its energy at harmonics of a single quefrency (high peak/median); randomly
  spaced tones scatter it flat (low). This is what separates a *comb* from a mere
  *pile of tones* — a single autocorrelation peak cannot.
- **Spacing** — the spectrum's autocorrelation, whose fundamental lag D gives
  delta-f = D·fs/N with no harmonic ambiguity.

**Result.** 15-tooth comb at 3000 Hz spacing, each tooth modest vs unit-variance
noise:

| input | verdict |
|---|---|
| uniform comb (15 teeth @ 3 kHz) ×3 | **DETECTED, spacing 3000 Hz exactly, sig ~15** |
| pure noise ×12 | silent (max 4.6; threshold 5.9) |
| **15 randomly-spaced tones ×3 (control)** | **correctly silent (sig ~4)** |

**3/3 combs detected with exact spacing, 0/3 false fires on the random-tone
control.** The control is the whole point: a naive "count the peaks" detector
fires on any clutter of carriers. This fires only on *uniformity* — the thing
nature doesn't fake.

**Conclusion.** CONFIRMED and kept. `comb.py` is the second detector in the
novel-detector suite. Selftest is a regression gate: `python comb.py selftest`.
Next: entropy/compressibility (EXP-16), then the agent loop.
