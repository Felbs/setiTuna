# RECIPES — invent your own way to find aliens

SETI has a telescope-time problem and an **imagination problem**, and only one of
those is yours to fix. The Breakthrough Listen archive is free, public and
enormous — petabytes of the sky at Green Bank and Parkes, already recorded. What
almost nobody has done is ask it a *new question*.

For 65 years the question has been essentially one question: **"is there a
narrowband carrier?"** That is what Project Ozma asked in 1960 and what turboSETI
asks today. It is a good question. It is also *one* question, and
[NOVEL_DETECTORS.md](NOVEL_DETECTORS.md) argues it is tuned to catch a
civilization at exactly our 1950s stage of radio and no other.

A **recipe** is a new question, written as ~80 lines of Python, that this repo
will run and score against everyone else's on the same public data.

```
recipes/
  narrowband_drift.py    the reference: a Doppler-drifting tone
  comb_uniformity.py     ours: uniformly Hz-spaced tones (engineered uniformity)
  spread_flatness.py     ours: wide FLAT excess power (spread spectrum)
  dispersion_sweep.py    nature: FRBs and pulsar single pulses
  hi_line_natural.py     nature: the galaxy's hydrogen and the maser lines
  pi_ratio.py            playful: tone pairs at a Doppler-invariant ratio
  your_idea_here.py      <-- this
```

---

## The contract (the whole thing)

Drop a `.py` file in `recipes/`. It is auto-discovered. That is the deploy step.

```python
NAME        = "my_detector"          # unique
DESCRIPTION = "one line: what signal class does this catch?"
AUTHOR      = "your name or handle"
VERSION     = "1.0"
INPUT       = "spectrogram"          # the only input type today
TAGS        = ["technosignature", "whatever"]

def run(spec, params=None) -> list[Candidate]:
    ...

def selftest() -> int:               # optional, but see "The one rule" below
    ...
```

### What you get: `spec`

A `seti_io.Spectrogram`. One convention, everywhere: **`data[time, channel]`,
frequency ASCENDING, physical axes attached.** It does not matter whether the
bytes came from Green Bank, Parkes, an RTL-SDR capture or a synthetic test
signal — your recipe never has to care.

| | |
|---|---|
| `spec.data` | `(ntime, nchan)` float power |
| `spec.freqs_mhz()` / `spec.times_s()` | the axes |
| `spec.f_lo`, `spec.f_hi`, `spec.res_hz`, `spec.dt_s`, `spec.duration_s` | scalars |
| `spec.integrated()` | time-averaged spectrum |
| `spec.timeseries()` | frequency-averaged light curve |
| `spec.bandpass_normalized()` | instrument shape divided out |
| `spec.crop(f_start, f_stop, t_start, t_stop)` | a window, in MHz and seconds |
| `spec.decimate(tfac, ffac)` | block-average |
| `spec.dedisperse(dm)` | undo the cold-plasma sweep for a trial DM |
| `spec.fold(period_s, nbins)` | phase-fold the light curve |
| `spec.meta` | `source_name`, `telescope`, `tstart_mjd`, `ra_hr`, `dec_deg`, `origin` |

Helpers in `recipe_api` you are welcome to reuse: `robust_z()` (median/MAD
z-score), `peaks_z()`, `spectral_flatness()`.

### What you return: `Candidate`

```python
R.Candidate(
    freq_mhz=1420.123456,     # required
    score=42.0,               # required: higher = more interesting
    drift_hz_s=-0.35,         # whatever your method measures; leave 0 if n/a
    t_start_s=0.0, duration_s=None, bandwidth_hz=None,
    dm=None, period_s=None,
    kind="techno",            # techno | natural | rfi | unknown - your honest call
    label="human-readable: what you think this is",
    provenance=dict(          # HOW you got it, so a human can re-derive it
        method="...", measures=["..."], reference="paper or repo doc",
        # ...any numbers your method produced
    ))
```

`provenance` is not decoration. This repo's rule is that **every hit gets
explained, not thresholded away** — a candidate a reader cannot re-derive is not
a result.

---

## Run it

```bash
python cookbook.py list                          # see it discovered
python recipes/my_detector.py                    # your own selftest
python cookbook.py run my_detector synth:drift   # on a synthetic scene, no download
python cookbook.py run all data/star_GJ699.h5 --f-start 1420.2 --f-stop 1420.7
python cookbook.py bench                         # score it, rewrite LEADERBOARD.md
```

Synthetic scenes need no data at all and take parameters:

```
synth:noise      synth:drift,drift_hz_s=-0.35,snr=25      synth:zerodrift
synth:frb,dm=560,f0_mhz=4000,df_mhz=4,dt_s=0.001,ntime=400,nchan=512
synth:pulsar,period_s=0.714,dm=26.8      synth:comb      synth:spread
synth:maser      synth:hi,v_kms=25
```

---

## The one rule: **be clean on noise**

A detector that fires on pure noise has found nothing, however impressive its
hit list. The benchmark includes `NULL_noise` scenes and the leaderboard ranks
every recipe that fires on them *below* every recipe that does not, permanently,
regardless of how many real scenes it catches.

So the shape of a good selftest is not "does it find my signal" — it is
**"does it find my signal AND stay silent on the controls"**:

```python
def selftest():
    ok = []
    ok.append(bool(run(seti_io.synth("my_signal_kind"))))        # sensitivity
    for seed in (11, 12, 13):
        ok.append(not run(seti_io.synth("noise", seed=seed)))     # false alarms
    ok.append(not run(seti_io.synth("drift", snr=200)))           # the WRONG signal
    return 0 if all(ok) else 1
```

That third control is the one people skip and it is the one that matters most: a
"spread-spectrum detector" that also fires on a loud carrier is a power meter.
Every shipped recipe here has one — `comb_uniformity` must stay silent on the
same number of *randomly*-spaced tones, `spread_flatness` must stay silent on a
carrier 200× the noise, `pi_ratio` must veto an exact harmonic.

---

## How a candidate actually gets believed

Finding something is the easy part. Every recipe's output goes through
`recipe_api.explain()`, which attaches a verdict rather than deleting anything:

1. **Band edge** — within 3 channels of the block edge; usually an artifact.
2. **Natural line** — sits on HI (1420.405751768 MHz), the OH quartet
   (1612/1665/1667/1720), methanol (6668.5/12178.6) or water (22235.1). Nature
   makes narrowband tones. See [SETI_HISTORY.md](SETI_HISTORY.md).
3. **Known-RFI band** — GNSS, Iridium, DME/radar, satellite radio, WiFi. The
   table is in `recipe_api.RFI_BANDS` with a reason attached to each range.
4. **Zero drift** — a sky source must Doppler-drift; Earth's rotation alone gives
   ~0.05–0.3 Hz/s at L band. Exactly 0.000 Hz/s over minutes means it is bolted
   to the ground next to you. (We *label* rather than delete, because
   NOVEL_DETECTORS #3 argues a drift-*compensated* beacon would look exactly
   like this.)
5. **Unexplained** — survived everything. These are the ones to work on.

Then the real test, which no single-pointing search can substitute for:

### The ON/OFF cadence

Breakthrough Listen observes **ON-OFF-ON-OFF-ON-OFF**: the target, then a nearby
throwaway sky position, alternating. A signal from the target appears only in the
ON scans. Anything in an OFF scan is local.

```bash
python cookbook.py cadence my_detector ON=a.h5 OFF=b.h5 ON=c.h5 OFF=d.h5 ON=e.h5 OFF=f.h5
python waterfall.py cadence ON=a.h5 OFF=b.h5 ON=c.h5 OFF=d.h5 --out cad.png
```

![the cadence pattern](figures/cadence_pattern.png)

This is not a formality. It is how **BLC-1** — the 982.002 MHz Proxima Centauri
candidate of 2020, the best modern SETI candidate — was shown to be an
intermodulation product of local interference (Sheikh et al. 2021, *Nature
Astronomy* 5, 1153). Zero survivors is the normal, honest result.

---

## The leaderboard

`python cookbook.py bench` scores every recipe on the same synthetic scenes,
generated from the physics quoted in [SETI_HISTORY.md](SETI_HISTORY.md), and
writes [LEADERBOARD.md](LEADERBOARD.md).

Nobody is expected to catch everything — a comb detector legitimately misses
FRBs. **Breadth of the panel is the goal, not any one recipe.** The interesting
column is the last one: which scenes does *nobody* catch?

### Open bounties

Scenes on the benchmark that no shipped recipe detects, ranked by how gettable
they look. Claim one:

- **`pulsar_B0329`** — a periodic dispersed pulse train where no single pulse is
  significant. Needs a periodicity search (fold over trial periods, or an FFT of
  the light curve), not a peak-finder. `spec.fold()` is already there. This is
  the most winnable one on the board.
- Beyond the benchmark, from [NOVEL_DETECTORS.md](NOVEL_DETECTORS.md), still
  unwritten as recipes: **polarization** signatures (needs Stokes products),
  **pulsed-timing** searches (arrival times at mathematically loud spacings),
  **"too perfect" natural mimics** (a pulsar with impossibly low jitter, a maser
  too monochromatic — flag sources whose statistics are *more* regular than the
  astrophysics allows), and **anti-drift beacons** (a signal at *exactly* zero
  drift from a fixed sky position, which every standard pipeline throws away).

If you add a benchmark scene as well as a recipe, add the scene *first* and in a
separate commit, so it is clear you did not tune the detector to the test.

---

## Credit and prior art

Recipes stand on other people's work; say whose in `provenance["reference"]`.
The ones this repo leans on:

- **Breakthrough Listen** / Berkeley SETI Research Center — the open data that
  makes any of this possible (Lebofsky et al. 2019, PASP 131:124505; Price et al.
  2020, AJ 159:86).
- **turboSETI** (Enriquez & Price 2019) — the reference narrowband drift search,
  descended from Taylor's 1974 tree de-dispersion.
- **blimpy** (Price et al. 2019) — reading BL filterbank/HDF5 products.
- **setigen** (Brzycki et al. 2022) — synthetic signal injection, the honest way
  to measure a detector's completeness.
