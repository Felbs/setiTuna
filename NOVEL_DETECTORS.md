# What human SETI probably missed — and what alien radio might *actually* sound like

The founding assumption of 65 years of SETI: **an artificial signal looks
artificial in the SPECTRUM** — a narrowband carrier, a spike where nature makes
none. turboSETI, our own sweep, almost everything: they hunt narrowband tones.

That assumption is anthropocentric and probably wrong for anything but the
briefest, most primitive phase of a civilization. Here is the imagination SETI
has been short on.

## The core blind spot: WE stopped using narrowband
Human radio went narrowband (AM, 1900) → spread-spectrum / OFDM / noise-like
(5G, WiFi, GPS, military, 2020) in ONE century. Our most SETI-detectable era —
loud narrowband carriers — was a ~100-year window that is already closing. A
civilization even slightly ahead of us leaks **structured noise**, not tones.
turboSETI would see nothing. So the search that only finds carriers is tuned to
catch a civilization exactly as advanced as 1950s Earth, and no other.

## Detectors nobody runs (ranked by "physics says this could work")

1. **CYCLOSTATIONARITY** — the big one. Every digital signal, even one spread
   below the noise floor and looking like pure noise in the spectrum, has HIDDEN
   PERIODICITIES in its second-order statistics (symbol rate, carrier, chip
   rate). The spectral correlation function / cyclic autocorrelation reveals them
   where the power spectrum is flat. This is standard in signals intelligence and
   modem sync; SETI barely uses it. It can detect a spread-spectrum "TV leakage"
   equivalent that turboSETI is blind to. **Build this first.**

2. **FREQUENCY COMBS** — a set of tones at exactly even spacing across a wide
   band. Nature makes evenly-spaced lines only in narrow, physics-fixed places
   (rotational molecular lines aren't uniform in Hz). A broad, uniform Hz-spaced
   comb is an optical-frequency-comb-grade artifact. Search the hit list's
   spacing histogram for a sharp uniform peak.

3. **ZERO-DRIFT / ANTI-DRIFT beacons** — SETI throws OUT zero-drift signals as
   RFI (they must be local, since the sky Doppler-drifts). But a smart beacon
   would DRIFT-COMPENSATE to arrive at a constant frequency at the target — so a
   *perfectly* zero-drift signal from a fixed sky position (not our building) is
   the fingerprint of intent, not the thing to discard.

4. **INFORMATION / COMPRESSIBILITY** — pure noise is incompressible (max
   entropy); a pure carrier is trivially compressible (min entropy); a MESSAGE
   sits in between with structured, scale-dependent complexity. Slide a
   compression-ratio window over the spectrogram: modulation of ANY kind lights
   up the middle band. Modulation-agnostic — doesn't assume narrowband.

5. **POLARIZATION signatures** — most SETI discards polarization. Strong, stable
   CIRCULAR polarization of a specific handedness is rare in nature but standard
   for engineered satellite links (avoids Faraday rotation). A signal that is
   too cleanly circularly polarized is a discriminator natural masers rarely fake.

6. **TEMPORAL / PULSED** — SETI is frequency-domain-heavy. An alien radar or
   clock might be PULSED at mathematically loud spacings (primes, π, powers of 2)
   — an autocorrelation-of-arrival-times search, not a spectrum search. (FRBs
   proved nature makes bright ms bursts; the question is whether any repeat with
   engineered timing.)

7. **"TOO PERFECT" natural mimics** — a pulsar with impossibly low timing jitter,
   a maser too monochromatic, a scintillation pattern too regular. A civilization
   might hide inside a natural-looking envelope. Flag sources whose statistics are
   MORE regular than the astrophysics allows.

8. **WIDEBAND IMPULSES** — a single-cycle EM pulse smeared across GHz by
   dispersion. Clean, broadband, non-thermal transients. Dedisperse-and-search,
   like pulsar/FRB pipelines, but looking for engineered dispersion or repetition.

## What alien radio might "sound like" (if you demodulated it)
- Not a whistle (carrier) but **HISS with a heartbeat** — noise whose rhythm
  (cyclostationary period) is the only tell.
- A **shimmer of evenly-spaced tones** (comb) — a rake dragged across the band.
- **Silence that clicks** — rare, precisely-timed wideband impulses.
- **Noise that won't compress** the way real noise does — structure you can't
  hear but a compressor can feel.

## The plan: an autonomous novel-detector agent (task #31)
The right way to explore this isn't one detector — it's a LOOP that (1) proposes
a detection hypothesis from this list (or a new combination), (2) implements it
as a small detector, (3) runs it on real BL data + injected synthetic
"exotic-alien" test signals (setigen for the narrowband control; custom
generators for spread-spectrum / comb / pulsed), (4) measures its detection
floor and false-alarm rate honestly, (5) keeps the detectors that beat
turboSETI on the exotic signals, and iterates. Same hypothesis→experiment→
conclusion discipline as the whole rig. Start: cyclostationarity, comb, entropy.
