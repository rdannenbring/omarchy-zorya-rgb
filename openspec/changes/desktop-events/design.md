## Sources
`events.WorkspaceListener` reads the active workspace from Hyprland's request socket, then follows `workspacev2` and `focusedmonv2` on `.socket2.sock`. `events.NotificationListener` runs `dbus-monitor` for `Notify` calls, skips updates to existing notifications (non-zero `replaces_id`) and checks `omarchy-shell notifications isDnd`. Listeners start only after their setting is first enabled and reconnect with backoff up to 30 s.

## Overlay
The daemon adds `overlay` to the effective state: `flash` (0 to 1 alert strength from `alert_level`: sine-squared fade, 50% duty strobe or constant, over `alert_duration`) with `flash_color`, and `keys` mapping LED names to colors. The loop runs at 30 FPS while a flash is active. Lights off suppress overlays.

## Rendering
A device with an active overlay switches to its Direct (per-LED) mode and receives software frames of the base effect with the overlay blended in. When the overlay ends, the device signature changes and the base mode, including onboard modes, is restored without writing flash. A workspace highlight is persistent, so keyboards stay on per-LED frames while it is enabled.

Pending onboard saves are kept during overlays and sent after the base mode returns, unless the base mode changed.
