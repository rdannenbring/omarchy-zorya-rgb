## Why
Lighting can carry ambient desktop state: a glance at the keyboard can show a new notification or the active workspace without looking at the bar.

## What Changes
- Add `notify_flash` with configurable alerts: effect (`flash` fade, `strobe` blink or `solid`), total duration (0.5 to 10 s, default 2 s), cycle length for flash and strobe (0.1 to 1 s, default 0.25 s), alert color (`auto` follows the second color, or a fixed color) and critical color (default `#FF2020`). Critical notifications ignore Do Not Disturb; other notifications respect it.
- Add `workspace_keys`: keyboards that report named keys light the number key of the active Hyprland workspace (1 to 10, where 10 is `0`) in the second color over the base effect.
- Both are off by default and have panel toggles.

## Impact
New stdlib event listeners, daemon overlay state and backend per-LED overlay rendering. Uses `dbus-monitor` and `omarchy-shell` when the notification setting is on.
