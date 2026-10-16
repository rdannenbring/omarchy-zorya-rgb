## Theme source
`theme.py` reads `$XDG_STATE_HOME/omarchy/current/theme`. Primary is `keyboard.rgb` when present, otherwise the `colors.toml` accent. Files are opened with `O_NOFOLLOW`, must be regular and at most 64 KiB. Colors pass through an LED saturation boost adapted from Omakeychron (MIT); near-grays are unchanged.

Secondary is the palette color closest to 120° of hue from primary. A complement would fade through gray at the gradient midpoint. Palette is the saturated ANSI colors (red, yellow, green, cyan, blue, magenta) ordered by hue.

## Change detection
`omarchy-theme-set` replaces the `current/theme` symlink, so watching one file misses switches. The daemon re-reads the theme once per second while sync is enabled, and does not read it otherwise.

## Effective state
Saved settings are not rewritten. The daemon overlays `color`, `secondary_color` and `palette` on the snapshot it passes to the backend. Turning sync off restores the user's saved colors.

## Onboard storage
Writes to device flash happen only on explicit enablement or a real theme change, never on daemon start or restart. OpenRGB applies `UPDATEMODE` on a deferred device thread but runs `SAVEMODE` immediately, so saving with the update stored the previous state (a Keychron Q6 Max showed white). The backend sets the mode, then about one second later resends the identical mode with `save=True`. A newer change before then cancels the pending save. `save_mode()` is not used because it resends the SDK's cached mode.

## Mode switching
After `set_mode`, the backend records the requested mode as active. An SDK refresh can report the previous mode, and `set_colors` then rejects LED frames against that mode's palette limits.
