## Mode list
`devices` reports `hardware_modes`: every mode except Direct/Custom-style modes whose only capability is per-LED host control.

## Applying
A per-device entry bypasses effect mode picking. The backend sets the named mode with scaled speed and brightness and does not stream LED frames. Color slots are filled up to the mode's maximum from primary, secondary and palette, repeating when a mode needs more colors than available. Modes with random or no colors keep their own.

When lights are off, the entry is ignored so the device turns off.

A missing mode name is reported as that device's error; other devices continue.

## Storage
Selecting a mode (any `hardware_modes` patch) requests one save on the next apply, using the same `set_mode(save=True)` call as theme sync. Daemon start does not save.
