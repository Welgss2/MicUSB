# MicUSB Windows desktop direction

## Product contract

MicUSB carries iPhone microphone audio over USB, processes it locally on the PC, and routes it to VB-Cable. Audio state and useful controls take priority over decoration.

## Committed visual direction

Use a near-black, restrained studio surface with warm white text, cool gray secondary labels, and a single soft mint signal color. Keep the hierarchy compact and precise: custom title bar, visible signal path, input level and meter, then local voice treatment. Minimize ornamental cards; sections are separated by spacing and fine neutral rules. Window controls stay monochrome and quiet. Use Segoe UI Variable for readable Windows-native text and the authored MicUSB mark for the app, taskbar, tray, and installer surfaces.

The visual reference is `pc/micusb-reference.png`. The source identity is `pc/brand-mark.svg`; `pc/build_brand_assets.py` produces its high-resolution PNG, multi-size ICO, and tray image.

## Signal path and copy

The path reads iPhone → USB → MicUSB AI → VB-Cable. Noise reduction is described accurately as DeepFilterNet3 running locally. “Natural”, “Equilibrado”, and “TV alta” describe increasing attenuation, not guaranteed removal of overlapping speech. Do not claim that multiple physical microphones are mixed or that television speech can always be removed cleanly.

## Interaction commitments

- Minimize hides the window; closing the window keeps audio active in the notification area.
- The tray icon offers reopen and exit.
- Sliders and toggles continue to change the live processor while the stream runs.
- The window icon and Windows AppUserModelID identify MicUSB rather than Python.
- Launch with `pythonw.exe`; the USB forwarder is also spawned without a console.
