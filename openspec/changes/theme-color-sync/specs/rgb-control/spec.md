## ADDED Requirements

### Requirement: Optional theme color sync
The plugin SHALL let the user follow the active Omarchy theme colors without losing effect, speed or brightness control.

#### Scenario: Enabling sync
- **WHEN** the user enables theme sync
- **THEN** lighting uses the theme's keyboard color, or its accent when no keyboard color exists, and the panel disables manual color inputs.

#### Scenario: Effects under sync
- **WHEN** theme sync is enabled
- **THEN** static and pulse use the primary theme color, gradient blends the primary and secondary theme colors, and rainbow cycles only theme palette colors.

#### Scenario: Theme change
- **WHEN** the active theme changes while sync is enabled
- **THEN** lighting updates within about one second and devices with onboard storage save the new mode.

#### Scenario: Restart
- **WHEN** the daemon starts with sync enabled
- **THEN** it applies the theme colors without writing device flash.

#### Scenario: Disabling sync
- **WHEN** the user disables theme sync
- **THEN** the previously saved manual colors are restored.
