## Why
Omarchy themes define a keyboard color (`keyboard.rgb`) and an accent. Users who want lighting to follow the theme currently need a separate Keychron-only plugin that talks raw VIA HID. Zorya already controls every OpenRGB device, so it can follow the theme for all of them.

## What Changes
- Add an opt-in `theme_sync` setting. While enabled, the theme supplies the lighting colors and the panel disables manual color controls. Effect, speed and brightness stay user-controlled.
- Map theme colors to effects: static and pulse use the primary color, gradient blends primary and secondary, and rainbow cycles the theme palette instead of the full spectrum.
- Save the new mode to devices with onboard storage (`MANUAL_SAVE`) when sync is enabled or the theme changes, so the color survives replugs and wireless use.
- Prefer a `Solid Color` mode for static lighting where `Static` is absent, so static lighting can be saved onboard.

## Impact
New read-only theme module, daemon theme polling, backend save flag and panel controls. No package, service or permission changes.
