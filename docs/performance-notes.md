# Performance notes (2026-11-16 night)

## CPU cost
- Old glibc threads show up as separate processes; the DSP runs in one thread.
- 32 voices of a heavy sound (e.g. Symbiont, two resynators per note) ≈ half of one 2.1 GHz cloud Xeon core; idle ≈ 4%.
  The 1.2 GHz Celeron could not sustain that, hence the original's load throttling and the knob lag.
- The DSP is single-threaded, so one fast core matters more than core count. A 2013 ThinkPad i7 handles
  32 voices comfortably.

## Launcher (run_neuron.sh)
- DEDICATED=1 (only on the Neuron's own PC): real real-time priority and memory locking, two cores
  (DSP + panel/UI threads no longer share one core), small output buffer instead of 20 ms. PERF=1 is the same for a shared machine, with memory locking still faked.
- OUT_RATE / ALSA_DEV as before; FTDI latency set to 1 ms automatically.

## Latency, measured (ThinkPad i7-3537U, MOTU M4, 2026-11-24)
- Key to sound about 24 ms (median, 5 ms player buffer), measured with `tools/latency-test.py` and a loopback cable.
- About 11 ms of that is inside the engine: its 256-frame blocks are fixed, and forcing 128 breaks it
  (notes missing or very late).
- A 3 ms player buffer dropped out; 5 ms is clean (`neuron-engine set-buffer`). See also `desktop/README.md`, Tips.
