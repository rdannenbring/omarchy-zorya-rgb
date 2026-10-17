## ADDED Requirements

### Requirement: Desktop event overlays
The plugin SHALL optionally reflect desktop notifications and the active workspace on selected devices without changing saved lighting settings.

#### Scenario: New notification
- **WHEN** notification flash is enabled and a new notification arrives while Do Not Disturb is off
- **THEN** selected devices show the configured alert effect in the alert color for the configured duration and return to their lighting.

#### Scenario: Critical notification during Do Not Disturb
- **WHEN** a critical notification arrives while Do Not Disturb is on
- **THEN** selected devices show the alert in the critical color.

#### Scenario: Workspace change
- **WHEN** workspace highlighting is enabled and the active workspace changes to 1 through 10
- **THEN** keyboards with named number keys light that workspace's key in the second color over the base effect.

#### Scenario: Onboard mode restore
- **WHEN** an overlay ends on a device running an onboard mode
- **THEN** the onboard mode is restored without an extra flash write.
