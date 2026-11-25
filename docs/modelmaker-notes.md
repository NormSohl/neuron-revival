# MODELmaker 1.2 — findings (2026-11-16)

## What's in the downloads
- `NeuronMM_1_2_OSX.sit` → Java app (`neuronapp.NeuronApp`) + `libNASAnalysis.jnilib` (**PowerPC only** — won't run on modern Macs).
- `NeuronMM_1_2_OS9.sit` → MRJ app + `NASLib` (PEF/PPC).
- `NeuronMM_1_2_PC.zip` → `MODELmaker_1_2.exe` = **JEXEPack** bundle. Unpacked with `jxparse.py`:
  records 'B' (boot.class), 'V' (props), 'Z' (gzip archive: `NASAnalysis.dll` x86 + classes + ftp.jar + images.zip).
  Decode: `b' = ((b ^ i) - 100) & 0xff`, then Z = 8-byte header + gzip, entries magic 0xEAE9F3F0.

## Java side
- `NASAnalysisProvider` natives: validateSample, initNAS, analyseSample(in, scape, sphere, recursionDepth, parameterSet, isMulti, loopStartID, loopEndID), cancelAnalysis.
- analyseSample is called repeatedly (1024 samples per call) until status != 0 (1 = done).
- Input: AIFF, 44.1 kHz, 16-bit, mono (loops via markers).
- Complexity 1..10 → recursion depth 1,4,8,12,16,24,32,42(default=8),54,64.
- **Parameter Set 0..9 = engine algorithm** (sphere +0x10): Default, Stringed/Bowed, Plucked & Bells, Plucked & Picked, Carpet Shop, Piano etc., Woodwinds, Extreme Pads, Loop Factory, Multipurpose. Set 9 forces depth 32.
- Transfer to Neuron = FTP over USB-Ethernet (ftp.jar). With the new setup just copy into NeuronDB/Models/NNN.model/.

## Sphere header (LE, 0x8c bytes, magic 'NAsp')
+0x10 algorithm/parset · +0x18 frame count · +0x1c depth · +0x20/+0x24 2^ceil(log2 depth) · +0x28/+0x2c 0x3d (single) / 0x19 (multi) · +0x30 0x1808 · +0x34/+0x38 loop start/end (frames) · **+0x3c = 512-frame flag, always written 0 by MM 1.2** · frame scale constant 1/1024 hard-coded.

## Headless runner: `nasmm`
Minimal PE loader + kernel32 stubs + fake JNIEnv; runs the original x86 DLL on Linux (gcc -m32). 
`./nasmm in.aif outbase depth parset [isMulti loopStart loopEnd]` → outbase.scape/.sphere. 2 s sample ≈ instant.
Output headers match factory models byte-for-byte in layout; model plays correctly on the revived engine.

## 512 "full rez" experiment (trick)
Upsample source 2× (band-limited) → analyse as if 44.1k (octave down, 2× long) → set sphere +0x3c = 1 → map root key 12 lower.
Result on engine: correct pitch, correct duration. Need a dry test patch to judge transient gain.

## Dry A/B (2026-11-16 pm)
Test patch = InitSound (384) with R1 → test model, pitch LFO 0, AmpEnvR 30; models installed in slot 336. Scripts: ab2.sh, mm2.py (vpanel), ana2.py, err.py, dur.py.
- **Engine couples model time to pitch** (like a sampler): a note 12 above root plays the model 2× faster.
- So the earlier "flag=1 + root −12" trick played at 4× → half-length notes (that's the quicker drop-off heard in the first B file).
- Correct trick: 2× upsampled source, analyse normally, **flag left 0**, root key −12. Plays full length, correct pitch. (= frames every 512 source samples.)
- vs source (harmonics 1–10, mean |dB error|): std 1024: 2.9 overall / 3.0 early / 3.0 late; trick: 3.4 / **1.4 early** / 4.7 late.
  Trick captures the attack spectrum much better but high harmonics decay too fast in the tail. Depth 64 didn't help.

## True 512-frame analysis (2026-11-16 pm) — mkdll512.py
The analyzer is natively hop-512 inside (2048 FFT, phase-vocoder hop 512); MM 1.2 just feeds it 1024 samples per call
and keeps the last frame. Patch: feed window/4 = 512 samples per call, divide frame count & loop points by 512.
Then set sphere +0x3c = 1 and map the real root key (no transposition). Engine plays correct pitch & duration.

Results (dry InitSound patch, key = root):
- Clave (2.5 kHz, 18 ms decay): envelope rms error **2.6 dB (512) vs 5.9 dB (1024)**; 512 tail follows the source to −40 dB, 1024 dies ~15 ms early.
- Marimba A3: both decay too fast vs source (~−8 dB at 500 ms); 512 no better. Not a resolution issue — look at Parameter Set / complexity.
- Gated tone (10 Hz square): 1024 already reproduces 1 ms gate edges (scape data seems to carry fast envelope); 512 slightly worse depth.
- Pluck: about equal.
=> 512 helps short, fast-decaying percussive sounds; not a universal win.

## Real samples (VCSL, CC0 — github.com/sgossner/VCSL)
Marimba C4 (loud), Claves1 v3, Cowbell1 normal v3, Hi-hat closed v3 → towav_aif.py (44.1k/16/mono, trimmed) → mk.sh (Parameter Set 2) → dry patch.
| sound | envelope err 1024 / 512 | spectro-temporal err 1024 / 512 |
| claves | 4.6 / 7.4 dB | 15.4 / 16.7 |
| cowbell | 2.4 / 4.3 | 11.9 / 12.3 |
| hi-hat | 7.5 / 8.9 | 16.9 / 17.4 |
| marimba | 1.3 / 1.8 | 6.8 / 8.8 |
=> On real recordings the stock 1024 models are as good or slightly better. The synthetic-clave win didn't carry over.
Real marimba is reproduced well (synthetic marimba issue was my synthesis). Percussive noise (hi-hat, clave) is the weak spot for both.
Likely the analyzer/engine was tuned for 1024; my patch only changes the hop. Hartmann's own hi-res work may have changed more.
