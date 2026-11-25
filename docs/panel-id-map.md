# Neuron front panel ID map (tested on the original software, 2026-11-15)

Method: original OS 1.5 booted in QEMU with the owner's serial number, virtual panel on COM1.
VM state saved at the main screen ("Sound 0 / Symbiont"); each ID pressed from that same state
([ID][1] then [ID][0]). "LED" = output registers that changed. Pots/sliders send absolute
values, so a 1/0 press just shows their page. Not yet checked against the real hardware.

## Keypad / navigation
| ID | Function |
|---|---|
| 0x00-0x0A | Numeric keypad: 0x00=7, 0x01=8, 0x02=9, 0x03=4, 0x04=5, 0x05=6, 0x06=1, 0x07=2, 0x08=3, 0x0A=0 (0x09 unknown, maybe +/-) |
| 0x0B | Next sound (Sound 1 "Myst") |
| 0x0C | 10's Hold (LED 0x27) |
| 0x0D | Save ("Save as") (LED 0x26) |
| 0x25 | 10's Hold toggle path (LED 0x3A in code) |
| 0x52 | Menu joystick by the main display, one bit per direction then 0 on release: 8 = up, 1 = down, 0x10 = left, 2 = right, 4 = push (push puts the selected value back to its default). Confirmed in the VM. |
| 0xF9 | Power button ("Switch Off?") |
| 'H' 0x48 | Master Volume encoder (global MasterVolume, shown as [nnn]); 1 = up, 0 = down. Factory default 51, which is why the stick sounded quiet; the stick now ships 100. |
| 'L' 0x4C, 'Q' 0x51 | Control section encoders: GlobalController2Value / GlobalController3Value; 1 = up, 0 = down. |
| 0x0E | Store snapshot ("Saved Snapshot Number n", counts up each press) |
| 0x40 | Leaves the Saved Snapshot screen |

## Global
| ID | Page shown | LED |
|---|---|---|
| 0x20 | SetUp / InitSetUp | 0x3F |
| 0x21 | Pitch Bend: Range | 0x3E |
| 0x22 | CopyFromSnd | 0x3D |
| 0x23 | Load FTP: Software | 0x3C |
| 0x24 | Basic Settings: Master Tune | 0x3B |
| 0x35 | Snapshots ("Playing Original") | 0x20 |

## Resynator 1 / 2
| R1 | R2 | Function | LEDs |
|---|---|---|---|
| 0x28 | 0x2F | Switch on/off | 0x06 / 0x16 |
| 0x29 | 0x30 | Param Level | 0x03-0x05 / 0x13-0x15 |
| 0x2A | 0x31 | Load Model | |
| 0x2B | 0x32 | Pitch (octave) | 0x01-0x02 / 0x1E-0x1F |
| 0x2C | 0x33 | Type Sphere/Scape | 0x0C-0x0E / 0x1A-0x1B |
| 0x36 | 0x38 | Parameter select | 0x0B / 0x12 |
| 0x37 | 0x39 | Parameter value | 0x0A / 0x10 |
| 0x4D | 0x4E | Volume (pot) | |
Small displays: R1 model name in 0x9B-0xA4, R2 in 0xC6-0xD0 (ASCII per register).

## Blender, Shapers, LFO, Slicer
| ID | Function |
|---|---|
| 0x2D | Blender Type; 0x45 Blender Amount (pot) |
| 0x2E | Shaper 1/2 status (LEDs 0x08-0x09, 0x41/0x43/0x48/0x4A) |
| 0x41-0x44 | Shaper 1 Amp Attack / Decay / Sustain / Release (wheels) |
| 0x47, 0x49-0x4B | Shaper 2 Amp Attack / Decay / Sustain / Release |
| 0x26 | Shaper 3 status (LEDs 0x38, 0x39, 0x46, 0x4C, 0x4D) |
| 0x3B-0x3F | Shaper 3 Env Attack / Decay / Sustain / Release / Depth |
| 0x27 | LFO switch (LED 0x07); 0x46 LFO Depth |
| 0x34 | Slicer type (LED 0x19); 0x4F Depth/Spread, 0x50 Rate |

## Silver section and Master FX
| ID | Function | LED |
|---|---|---|
| 0x13 | Silver switch | 0x21 |
| 0x14 | Silver level / mode (FreqFX) | 0x2B, 0x2D, 0x2E |
| 0x15, 0x17 | Silver Filter type (24 dB / 12 dB LP) | 0x36, 0x37 |
| 0x1A | Silver Filter cutoff | 0x2A, 0x2B |
| 0x3A | Silver Filter contour | 0x2C |
| 0x18 | Silver FreqFX switch | 0x35 |
| 0x19 | Silver TimeFX switch | 0x34 |
| 0x1C | Master FX Delay switch | 0x32 |
| 0x1D, 0x1F | Master FX Delay time / mix as absolute pots. **No such knobs on the real panel**: Delay and Reverb are the Shaper 3 A and D wheels (0x3B, 0x3C) when Shaper 3's Status button selects Efx Mix (checked 2026-11-24). | |
| 0x1E | Master FX Reverb switch | 0x31 |

| 0x16 | **Surround** (real panel, 2026-11-24). The engine acts on it only when the global SetUpMode = 1
(SetUp mode, several sounds placed in the surround field); in single-sound mode it is ignored on purpose. 0x12 has the same check. | |

## Other inputs (from the code)
- 0x5B-0xB2: keybed (note = ID - 0x37, VALUE = velocity). 'S'-'Z' (0x53-0x5A): stick axes; 'V' = pitch bend.
- **0xB4 = keyboard aftertouch** (real panel, 2026-11-24): sent only while a key is held, values 0 to ~140.
  0xB3: pedal input (not seen; no pedals). 0xB5 = switch pedal, 0xB6 = sustain pedal (polarity from globals PedalSwitchDefault / PedalSustainDefault).
- Sticks (real panel, 2026-11-24), X / Y: Resynator 1 0x54 / 0x58, Resynator 2 0x55 / 0x59, Silver 0x53 / 0x57,
  Control stick (bottom left) 0x56 / 0x5A. Raw range about 30-225 without handles; keep the stored calibration.
- All other section knobs and wheels (0x41-0x47, 0x49-0x4B, 0x4D-0x50, 0x3F) are endless: 1 = up, 0 = down; other values ignored (checked 2026-11-18).
- No visible reaction from the main screen: 0x09 (the keypad ±), and 0x5B-0xF8 outside the keybed range.

## Output registers (208 sent on panel start-up)
- 0x00-0x4D: button/section LEDs (0 off, 1 on, 2 probably blink).
- 0x4E-0x6D: main LCD (2 x 16).
- 0x6E-0x99: small parameter displays (3-digit values and 8-char names) for the sections.
- 0x9B-0xE9: Resynator model-name and parameter displays.
- 0xF1, 0xF2: unknown values.

## Stick v4 (2026-11-19)
The on-screen panel and text panel now use these findings: menu joystick on 0x52, Master Volume on 'H',
Ctrl 2/3 on 'L'/'Q', Silver filter 0x15/0x17, delay pots 0x1D/0x1F. The stick's neuron.globals ships
MasterVolume 100 (factory 51). Boot-tested in QEMU; image sha256
d8f07e83cc353eba802ee15f39a11ec5dc8ca9bd7f695cd9e0ac4a8b2f4146c3.

## Data knob, Sound page, wheel lights (2026-11-19, stick v6)
- **0x40 = data knob** (1 = up, 0 = down). Every menu state registers 0x40 as its value up/down. Master Tune 440 -> 443, Stick Mode Jump <-> Snap confirmed in the VM.
- **0x25 = Sound page** (state 0x215/0x217, the home page). A TAP: held for 2 s it runs FULL RESET. LED 0x3A.
- On the sound page the data knob steps through sounds; the number shows with the top bit set (0xB0-0xB9) while picked but not loaded. Wraps 0 -> 999 (InitSound).
- **Wheel lights**: LED registers carry a level 0 (dark) .. 9 (all lit): Shaper 1 A/D/S/R 0x40/0x47/0x41/0x48, Shaper 2 0x42/0x49/0x43/0x4A, Shaper 3 0x45/0x4C/0x46/0x4D, Blender 0x44 (max 8), Ctrl 2 wheel 0x4B.
- Keypad digits and 0x0B do nothing outside the sound page.
