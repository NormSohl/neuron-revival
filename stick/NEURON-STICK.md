# Neuron USB stick

A USB stick that turns any 64-bit PC into the Hartmann Neuron's computer. It boots straight
into the original Neuron software and runs from the stick; the PC's own drive is never touched.
Remove the stick and the PC starts its normal system again.

## What you need

- A USB stick, **8 GB or larger** (16 GB gives room to spare; USB 3 starts faster). It will be erased.
- The PC (tested target: Lenovo IdeaCentre, Core i7).
- A USB audio interface (optional: without one, sound comes from the PC's own headphone/line output).
- An FTDI USB-to-RS-232 adapter for the Neuron's panel cable.

## Make the stick (on the Mac)

1. Install **balenaEtcher** (free, balena.io/etcher).
2. Open it, choose **Flash from file**, pick `neuron-stick.img`.
3. Choose the USB stick as the target, then **Flash**. It takes a few minutes.
4. If macOS says the disk is not readable afterwards, click **Ignore** (the Mac can't read Linux disks; that's normal).

## Start the Neuron

1. Plug in the stick, the USB-serial adapter (connected to the Neuron's panel cable) and the audio interface.
2. Switch on the PC and open its boot menu: on Lenovo desktops, tap **F12** right after power-on.
   Pick the USB stick (it may appear twice, as "UEFI: …" and as plain USB; either works).
3. The screen shows a short menu ("Hartmann Neuron"), then a few lines of text. After about a minute
   the line `[neuron] panel /dev/ttyUSB0, audio …` appears and the Neuron's displays come alive.
4. The very first start takes a little longer: the stick enlarges its storage area to fill the stick.

To make it start every time without F12, set the USB stick first in the PC's boot order
(Lenovo: press F1 at power-on for setup, Startup menu).

To switch off: just switch off. Sounds you saved are written immediately.
(If Secure Boot blocks the stick, turn Secure Boot off in the PC's setup.)

## The on-screen panel

The stick shows a full-screen Neuron panel on the PC's display, laid out like the Neuron's top panel:
Resynators with their sticks and displays, Blender, Slicer, Programmer keypad, Silver, Effects, the three
Shapers, LFO, the main display with its menu joystick and Master Volume knob, Silver Filter type, Master
Delay time and mix, the Control section (stick plus Ctrl 2 and Ctrl 3) and a five-octave keyboard.
Use the mouse or a touch screen: click buttons, drag wheels and knobs up or down (or use the scroll
wheel), drag the orange sticks (double-click centres them). The computer keyboard plays as below.
The computer keyboard also works the panel: arrow keys move the menu joystick, Enter pushes it
(push puts the selected setting back to its default), and [ ] turn the Master Volume down and up.
The same panel works alongside the real Neuron panel once that is connected.

If the PC's graphics can't run the full-screen panel, the stick falls back after about a minute to the
simple text panel described next.

## Text panel

If no USB-serial adapter is plugged in, the stick uses the PC's own keyboard and screen as the
Neuron's panel. The screen shows the Neuron's main display and the two Resynator model names.

| Keys | Function |
|---|---|
| Z S X D C V G B H N J M , | keybed from C (lower row), held as long as you hold the key |
| Q 2 W 3 E R 5 T 6 Y 7 U I | one octave higher (upper row) |
| - and = | octave down / up |
| F5 / F6 | softer / harder |
| Page Down | next sound |
| arrow keys, Enter | menu joystick, joystick push (resets the selected setting to its default) |
| [ and ] | Master Volume down / up |
| number pad | the Neuron's keypad |
| Space | all notes off |

## Settings

Settings live in `neuron.conf` on the stick's small **NEURONCFG** drive, which Windows and the Mac
can open: edit it with Notepad or TextEdit (plain text).

| Setting | Default | Meaning |
|---|---|---|
| PANEL_DEV | auto | real panel: auto = through a USB-serial adapter if present; `virtual` = on-screen only; or a port like /dev/ttyS0 |
| KIOSK | 1 | 1 = full-screen web panel, 0 = text panel |
| ALSA_DEV | auto | audio output; auto = first USB audio interface, else built-in audio |
| ENGINE | neuron | `neuron` = original (32 voices), `neuron_v64` = 64 voices |
| DEDICATED | 1 | real-time priority, two CPU cores, 6 ms output buffer |

Or on the Neuron PC itself: press **Ctrl+Alt+F2**, log in as `root`, password `neuron`,
type `nano /cfg/neuron.conf`, edit, save with Ctrl+O, exit with Ctrl+X, then type `reboot`.
Ctrl+Alt+F1 shows the Neuron's status messages.

## Backing up your sounds

Your Sounds, SetUps and Models are in `/data/neuron/NeuronDB` on the stick. The simplest backup is to
make a second copy of the whole stick with balenaEtcher's "Clone drive" option.
