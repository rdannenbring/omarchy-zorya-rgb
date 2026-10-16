## ADDED Requirements

### Requirement: Per-device onboard modes
The plugin SHALL let the user run a device's own onboard mode instead of the Zorya effect, using the scene's colors where the mode accepts colors.

#### Scenario: Choosing an onboard mode
- **WHEN** the user picks an onboard mode for a device
- **THEN** the device runs that mode with scene colors, speed and brightness mapped to the mode's capabilities, and saves it when the device supports onboard storage.

#### Scenario: Theme sync with an onboard mode
- **WHEN** theme sync is on and a device runs an onboard color mode
- **THEN** the mode's colors come from the theme and follow theme changes.

#### Scenario: Returning to the Zorya effect
- **WHEN** the user picks "Zorya effect" for a device
- **THEN** the device resumes the selected Zorya effect.

#### Scenario: Unavailable mode
- **WHEN** a stored mode name no longer exists on the device
- **THEN** that device reports an error and other devices are unaffected.
