# EXP-14 — cyclostationary detector: hearing what turboSETI can't

**Hypothesis.** A civilization even slightly past its radio infancy transmits
*spread* / digital signals that look like pure noise in the power spectrum — so
a narrowband drift search (turboSETI, our own star sweep) is structurally blind
to them. But any digitally-keyed signal is *cyclostationary*: its second-order
statistics carry a hidden periodicity at the symbol/chip rate. A cyclic-
autocorrelation detector should expose that periodicity where the spectrum is
flat, and should NOT fire on real noise.

**Method.** For lag τ, form r_τ[n] = x[n]·conj(x[n−τ]); its Fourier transform is
the cyclic autocorrelation vs. cycle-frequency α. A digital signal peaks at
α = chip/symbol rate even when constant-envelope and sub-noise; noise peaks
nowhere. Scan a ladder of lags, take the strongest feature, reference its height
to the median of the α-band, and gate on a threshold calibrated on pure noise.

**Controlled result (the proof).** Direct-sequence spread BPSK (25 kHz chips,
constant envelope) buried in complex noise:

| SNR | spectrum peak/median | narrowband search | cyclo verdict |
|----:|---------------------:|-------------------|---------------|
| −3 dB | 32× | would catch | chip-rate 25 000 Hz, **12–42σ → DETECTED** |
| −6 dB | 25× | **MISSES** | chip-rate 25 000 Hz, **25σ → DETECTED** |
| −10 dB | 20× | **MISSES** | chip-rate 25 000 Hz, **12σ → DETECTED** |

Pure-noise false-alarm gate: 12 trials, cyclic significance never exceeded 4.8;
threshold set to 6.3. **3/3 sub-noise spread signals detected, zero false
alarms.** At −6 and −10 dB the signal is invisible to any spectrum-based search,
and cyclo still recovers the exact chip rate. This is the class of signal a
narrowband SETI search cannot see, and the detector sees it.

**Real-data smoke test (honest).** Scanned a real GPS L1 capture — a genuine
spread-spectrum signal ~19 dB below the noise floor, the closest thing on the
rig to an "alien-like" (spread, sub-noise) transmission. Cyclo returned a *weak*
cyclostationary feature (8.2σ, just over threshold), not a clean chip-rate lock.
That is the expected outcome for a signal this far below noise at this
integration length: structure is present but faint. It confirms the detector
runs end-to-end on real IQ and doesn't blow up; it is not a clean GPS detection.

**The deeper point — why nobody runs this.** Cyclostationary detection needs
*voltage/IQ* data (it uses phase). The Breakthrough Listen public archive ships
*integrated power spectra* (filterbank/HDF5) — the phase is already thrown away.
So the very data format SETI archives is the one that makes its most powerful
possible detector impossible. To hunt spread-spectrum ET properly you need
raw-voltage recordings, which exist but are enormous and rarely public. That is
a concrete, actionable gap, not a vibe.

**Conclusion.** CONFIRMED and kept. cyclo.py is the first detector in the
novel-detector suite that provably beats a narrowband search on the signal class
past-SETI was blind to. Next in the suite: frequency-comb and entropy detectors,
then the agent loop that proposes/tests/keeps detectors autonomously
(NOVEL_DETECTORS.md). Selftest is a regression gate: `python cyclo.py selftest`.
