# EXP-16 — compressibility / spectral-entropy detector: the informative middle

**Hypothesis.** SETI hunts carriers — but a carrier is the *most boring* thing a
transmitter can send: it carries no information, you can compress it to nothing.
Pure noise is the opposite extreme: maximum entropy, incompressible, no
structure. A *message* lives between them — partly predictable, partly
surprising. So rather than hunt peaks, score the **complexity** of a band and
flag the structured middle, whatever its spectral shape. Modulation-agnostic.

**Method.** Spectral flatness (Wiener entropy) of the power spectrum:
SFM = geometric_mean(P) / arithmetic_mean(P), in (0, 1]. Coarse-grained so pure
noise averages toward flat. A pure carrier → SFM ≈ 0 (one bin dominates,
trivially compressible); pure noise → SFM ≈ 1 (flat, incompressible); a
band-limited modulated signal → the middle.

**Result.** Three inputs at fs = 100 kHz:

| input | SFM | label |
|---|---:|---|
| pure carrier (single tone + trace noise) | **0.000** | carrier-like — over-compressible, a dead tone |
| **modulated band** (colored channel, few dB SNR) | **0.506** | **STRUCTURED — the informative middle** |
| pure complex noise | **0.998** | noise-like — incompressible, no structure |

Strict ordering carrier < modulated < noise, and the modulated band correctly
labelled STRUCTURED (0.30 ≤ SFM ≤ 0.70). **PASS.**

**Honest scope.** SFM catches signals that *partly* fill a band with structure —
a modulated channel a few dB out of the noise. It does **not** catch a fully
spread signal that fills the whole band (that reads as noise-like, SFM ≈ 1) —
which is exactly the gap `cyclo.py` (EXP-14) exists to fill. The two are
complementary: entropy flags band-limited structure by shape alone; cyclo flags
spread structure by its hidden periodicity. Neither assumes a carrier.

**Conclusion.** CONFIRMED and kept. `entropy.py` is the third detector in the
suite. Selftest is the regression gate: `python entropy.py selftest`. With
cyclostationarity (spread), combs (uniformity), and entropy (band structure)
built, the suite now spans three orthogonal ways to be artificial-without-a-
carrier. Next: the agent that composes and tests these autonomously.
