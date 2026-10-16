## Why
Many controllers ship onboard effects (reactive typing, splash, beacon, digital rain) that run without host frames, keep working wirelessly and can be stored on the device. Zorya only exposes four portable effects, so these modes are unreachable.

## What Changes
- Add a per-device `hardware_modes` setting mapping a device ID to one of its onboard mode names. Devices without an entry keep following the Zorya effect.
- Fill the mode's color slots from the scene: primary, secondary, then theme palette when theme sync is on. Scale speed and brightness into the mode's ranges.
- Save the mode to devices with onboard storage when the user picks it.
- Add a mode picker to each device in the Devices tab.

## Impact
State schema, backend mode preparation, daemon persistence trigger and Devices tab. Presets capture the per-device modes.
