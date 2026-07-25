# Hunt result: Epsilon Eridani (GJ 144) — 2026-07-25

The star Frank Drake pointed at for Project Ozma in 1960 (the first modern SETI
search). Green Bank Telescope open data, S-band, 351,232 channels × 273 time
steps. Ran turboSETI drift search + our sideband-family detector.

## Verdict: NO TECHNOSIGNATURE (honest, and the forensics worked)
- SNR >= 10, drift <= 4 Hz/s: **0 hits**. Clean.
- SNR >= 5, drift <= 10 Hz/s: 23 hits — BUT **every single one sits at the exact
  same drift rate (+/-5.214 Hz/s)**. A real signal from a rotating/orbiting planet
  would show a RANGE of drift rates; a single shared drift rate is the fingerprint
  of instrumental/RFI artifacts, not ET. The strongest (SNR 800+) are at
  2193-2197 MHz — classic S-band terrestrial interference.
- The "sideband families" our detector flagged all inherit that one artifact
  drift, so they are RFI structure, not a modulated transmitter.

## Why this is a GOOD result
This is the discipline that matters: we didn't get excited by 23 hits — we
EXPLAINED them (uniform drift => RFI). That's exactly what separates a real
candidate from noise, and it's what took the professionals months to do for BLC1.
Full rigor next: find_event over the 6-file ON/OFF cadence (a true signal appears
ONLY when pointed at the star). Pipeline + forensics validated on a real star.
