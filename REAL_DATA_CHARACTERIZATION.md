# Novel detectors on real RF — do they behave sanely? (task #31)

Before trusting cyclo/comb/entropy on sky data, they earn it on real, **known-type**
terrestrial captures from the rig: FLAG engineered/digital signals (the class a
narrowband drift search misses), and stay honest on featureless input.
`python real_data_char.py` runs the panel; results below.

| capture | modulation | truth | cyclo | comb | entropy SFM | flags |
|---|---|---|--:|--:|--:|---|
| GPS L1 | DSSS spread | digital | 7.7 | **16.5** | 0.525 | comb, entropy |
| ADS-B | pulsed PPM | digital | **46** | **499** | 0.485 | all three |
| AIS | GMSK | digital | **43** | **355** | 0.692 | all three |
| FLEX pager | 4-FSK | digital | **2361** | **22** | 0.072 | cyclo, comb |
| FT8 | 8-MFSK | digital | **54** | **92** | 0.080 | cyclo, comb |
| WWFD 820 | **HD-AM OFDM** | digital | **3129** | 2.1 | 0.002 | cyclo |
| CHU | AM voice + FSK timecode | digital | **79** | 6.5 | 0.284 | cyclo |
| WWV 10 | AM carrier + tones | "analog" | **451** | 1.2 | 0.026 | cyclo |
| **~noise~** | (control) | none | 4.9 | 4.4 | 1.000 | **silent (correct)** |
| **~carrier~** | (control) | none | 5.1 | 1.0 | 0.000 | **silent (correct)** |

## What it shows
- **True positives: 7/7.** Every engineered/digital signal tripped at least one
  detector — the class turboSETI is structurally blind to, caught on real air.
  Digital modulation is loud in second-order statistics even when the power
  spectrum looks unremarkable.
- **True negatives: both controls silent.** Pure noise reads SFM 1.000 with
  cyclo/comb below their gates; a pure carrier reads SFM 0.000, cyclo/comb silent.
  The false-alarm gates hold on real-scale data, not just the selftest.
- **The "analog" that fired is a lesson, not a failure.** WWV lit cyclo (451) —
  but it carries a BCD time code, precise tones and 1 Hz ticks: engineered and
  information-bearing, so a fire is correct. The clean controls prove the detector
  can stay silent; WWV firing means WWV genuinely has structure. The real axis is
  "engineered/structured vs featureless," and the detectors track that.

## Why the ensemble matters
- **GPS** (spread, ~19 dB under noise) slipped past cyclo (7.7, just under gate)
  but comb + entropy caught it. Spread-spectrum needs the panel, not one lens.
- **HD-AM OFDM (WWFD 820)** screams on cyclo (3129 — its OFDM symbol clock): a
  direct preview of the digital-AM task (#32); the detector that will confirm
  HD-AM on the incoming loop antenna already lights up on a real HD-AM capture.
- **FSK modes** (FLEX, FT8, CHU timecode) have enormous cyclo features — keyed
  tones are maximally cyclostationary.

## Bottom line
On real terrestrial RF the suite flags engineered structure of every kind (spread,
OFDM, FSK, GMSK, PPM) and stays silent on noise and bare carriers — the empirical
grounding for pointing it at the sky, where the thesis is that an advanced
civilization looks engineered but not narrowband, and this panel hears that.
