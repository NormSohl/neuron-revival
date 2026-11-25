# Neuron front panel serial protocol (first pass, 2026-11-15)

Decoded from the original `neuron` binary (OS 1.5, Feb 2004) with Ghidra and objdump.
Addresses refer to that binary. Status: from code reading only, not yet checked against hardware.

## Link
- `/dev/ttyS0` (COM1), **115200 baud**, opened by `PanelHndlr` through `SerialDrv` (termios: cfsetispeed/cfsetospeed/tcsetattr). 8N1 assumed.
- Byte values 0x00-0xF9 are data; **0xFA-0xFF are single-byte control codes**.
- Everything else is a **2-byte message: [ID][VALUE]**, both 0x00-0xF9. There is no framing byte; the receiver keeps a "pending ID" and resets it after each value (0x8067360).

## Panel → host (handled by the dispatcher at 0x80b1560)
| ID | Meaning (as far as known) |
|---|---|
| 0x5B-0xB2 | **Keybed notes.** Note number = ID - 0x37 (0x5B → 36 ... 0xB2 → 123). VALUE = **key travel time** (about 0.15 ms per unit; small = hard), 0 = note off. The host converts it with one of 5 curves or a fixed velocity (32/64/96/127). Default curve 2: time 10 → velocity 125, 30 → 75, 60 → 48, 100 → 25, 250 → 1. Confirmed on the running software 2026-11-15. |
| 'S' 'T' 'U' 'W' 'X' 'Y' (0x53-0x59 minus V) | Analog stick axes (calibration index 0-5). Matches sticks Control, Resynator 1, Resynator 2, Silver (X/Y). Calibration min/mid/max from neuron.globals (StickR1XMin etc.). |
| 'V' (0x56) | Axis with calibration index 6, mapped to a 14-bit value with a centre dead zone (centre 0x2000): pitch bend. |
| 'Z' (0x5A) | Axis index 7, 14-bit with centre dead zone, then reduced to 8 bits. |
| 'H' 'L' 'Q' (0x48, 0x4C, 0x51) | Sent to three different UI objects (probably the three encoder/data-entry groups). For 'Q' the VALUE is a direction: 0 = one step down, non-zero = one step up (one message per encoder detent). |
| 0xB3, 0xB4 | Continuous controllers with their own calibration (likely aftertouch and/or a pedal / wheel). |
| 0xB5, 0xB6 | **Footswitches 1 and 2** (0/1). Polarity can be inverted in settings. The receive layer inserts an opposite value when the same state repeats. |
| 0x1B | Host answers by sending display contrast (cmd 0x33) from settings. |
| any other ID < 0xFA | Generic button/control: passed to the UI handler (0x809edc0) with ID and VALUE, then changed LEDs are sent. |
| 0xFC | Host replies with 0xFC 0x0A 0x14 0x1E 0x28 (handshake / test pattern). |
| 0xFD | **Panel (re)started.** Host sends 0xFD, then the full UI state (ForceSendCurrentUI), then 0xF3 1, 0xFD, and marks the panel ready. |
| 0xFA, 0xFB, 0xFE, 0xFF | Ignored by the dispatcher. |

## Host → panel
Sent with `Send(cmd, value)` (0x80671d0): writes CMD, then VALUE, except CMD 0xFD (no value) and CMD 0xFC (followed by 0x0A 0x14 0x1E 0x28).
| CMD | Meaning |
|---|---|
| 0x00 0xFF 0xFD 0xFD 0xFD | Start-up / re-init sequence sent when the port opens. |
| 0xFA 0xFA 0xFA | Sent when the UI manager installs its handler (reset / attention). |
| 0x4E + n (n = 0-15) | **Main LCD line 1**, character position n; VALUE = character (through a character map). |
| 0x5E + n (n = 0-15) | **Main LCD line 2**, character position n. (So the main display is 2 × 16.) |
| 0x33 | Display contrast. |
| 0x22-0x25 | Four related outputs set to 0 (unknown yet). |
| 0xF3 | 0/1 flag sent around panel init (unknown yet). |
| table at 0x8146d98 | Button LEDs, VALUE 0 = off, 1 = on, 2 = probably blink. |
| UI register table | The host keeps two copies of all panel outputs (wanted at 0x95f11a0, last sent at 0x95ef180) and sends only entries that changed (0x80a08a0). |

## What this means for the project
- The panel and the keybed both talk over this one serial link. A modern computer (USB-serial adapter) or an RP2040 can drive the whole player interface.
- One encoder detent = one 2-byte message, about 0.17 ms at 115200 baud. **The serial link is not the cause of the knob lag**; the slowness is in the host program (processing and redraw), which a faster CPU and a new host program can fix.
- Still to do: list every button/LED ID (tables at 0x8146d98 and the UI register table), the second-display LCDs (left/right boards), the meaning of 0x22-0x25 and 0xF3, and confirm signal levels on the cable.
