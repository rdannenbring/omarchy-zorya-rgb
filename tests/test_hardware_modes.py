import types
import unittest
from test_backend_sdk import Client, Device
from zorya_rgb.openrgb_backend import OpenRGBBackend
from zorya_rgb.state import DEFAULT_STATE, validate_patch


def keychron():
    device = Device(name='Keyboard', location='HID: /dev/hidraw2')
    base = dict(colors=[], speed_min=0, speed_max=4, speed=0, brightness_min=0, brightness_max=255, brightness=0)
    device.modes = [
        types.SimpleNamespace(name='Direct', id=0, flags=32, color_mode=1, colors_min=None, colors_max=None, **base),
        types.SimpleNamespace(name='Breathing', id=1, flags=1 | 64 | 256, color_mode=2, colors_min=1, colors_max=1, **base),
        types.SimpleNamespace(name='Dual Beacon', id=2, flags=1 | 16 | 128 | 256, color_mode=3, colors_min=None, colors_max=None, **base),
        types.SimpleNamespace(name='Two Tone', id=3, flags=64, color_mode=2, colors_min=1, colors_max=4, **base),
    ]
    return device


class HardwareModeTests(unittest.TestCase):
    def setUp(self):
        self.device = keychron()
        self.backend = OpenRGBBackend(client_factory=lambda: Client([self.device]), color_factory=lambda *c: c)
        self.backend.connect()
        self.identity = self.backend.devices([])[0]['id']
        self.state = dict(DEFAULT_STATE, devices=[self.identity], color='#FF0000', secondary_color='#00FF00')

    def run_mode(self, name, **extra):
        state = dict(self.state, hardware_modes={self.identity: name}, **extra)
        return self.backend.apply(state, 0), state

    def test_listing_excludes_direct(self):
        self.assertEqual(self.backend.devices([])[0]['hardware_modes'], ['Breathing', 'Dual Beacon', 'Two Tone'])

    def test_single_color_mode_gets_primary_and_streams_nothing(self):
        result, _ = self.run_mode('Breathing')
        self.assertEqual(result['errors'], {})
        mode = self.device.mode_writes[-1]
        self.assertEqual((mode.name, mode.colors), ('Breathing', [(255, 0, 0)]))
        self.assertEqual(self.device.writes, [])

    def test_multi_color_mode_uses_secondary_and_palette(self):
        self.run_mode('Two Tone', palette=['#0000FF'])
        self.assertEqual(self.device.mode_writes[-1].colors, [(255, 0, 0), (0, 255, 0), (0, 0, 255)])

    def test_brightness_and_speed_scale_into_mode_ranges(self):
        self.run_mode('Dual Beacon', brightness=50, speed=5.0)
        mode = self.device.mode_writes[-1]
        self.assertEqual((mode.brightness, mode.speed), (128, 4))

    def test_missing_mode_is_a_device_error(self):
        result, _ = self.run_mode('Gone')
        self.assertIn('Hardware mode unavailable', result['errors'][self.identity])

    def test_persist_saves_only_saveable_modes(self):
        state = dict(self.state, hardware_modes={self.identity: 'Two Tone'})
        self.backend.apply(state, 0, persist=True); self.assertEqual(self.device.saves, 0)
        self.backend.apply(dict(state, hardware_modes={self.identity: 'Breathing'}), 1, persist=True)
        self.assertEqual(self.device.saves, 0)
        self.backend.apply(dict(state, hardware_modes={self.identity: 'Breathing'}), 2.1)
        self.assertEqual(self.device.saves, 1)

    def test_lights_off_ignores_hardware_mode(self):
        self.run_mode('Breathing', on=False)
        self.assertNotEqual(self.device.mode_writes[-1].name, 'Breathing')

    def test_setting_is_validated(self):
        self.assertEqual(validate_patch(DEFAULT_STATE, {'hardware_modes': {'a': 'Breathing'}})['hardware_modes'], {'a': 'Breathing'})
        for bad in ([], {'a': ''}, {'a': 3}, {'': 'x'}):
            with self.assertRaises(ValueError): validate_patch(DEFAULT_STATE, {'hardware_modes': bad})


if __name__ == '__main__':
    unittest.main()
