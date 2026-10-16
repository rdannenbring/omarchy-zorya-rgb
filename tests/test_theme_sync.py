from pathlib import Path
import tempfile
import unittest
from zorya_rgb import theme
from zorya_rgb.daemon import ZoryaDaemon
from zorya_rgb.effects import frame
from zorya_rgb.state import DEFAULT_STATE, StateStore, validate_patch

COLORS = '''accent = "#5e81ac"
red = "#bf616a"
yellow = "#ebcb8b"
green = "#a3be8c"
cyan = "#88c0d0"
blue = "#81a1c1"
magenta = "#b48ead"
'''


class ThemeColorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.dir = Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()

    def test_accent_is_primary_without_keyboard_color(self):
        (self.dir/'colors.toml').write_text(COLORS)
        colors = theme.colors(self.dir)
        self.assertEqual(colors['source'], 'accent')
        self.assertEqual(colors['primary'], theme.vivid('#5E81AC'))
        self.assertEqual(len(colors['palette']), 6)

    def test_keyboard_color_wins_over_accent(self):
        (self.dir/'colors.toml').write_text(COLORS)
        (self.dir/'keyboard.rgb').write_text('#ff00ff\n')
        colors = theme.colors(self.dir)
        self.assertEqual((colors['source'], colors['primary']), ('keyboard.rgb', '#FF00FF'))

    def test_secondary_is_about_a_third_of_the_hue_circle_away(self):
        (self.dir/'colors.toml').write_text('accent = "#ff0000"\nred = "#ff0000"\ngreen = "#00ff00"\nyellow = "#ffff00"\n')
        self.assertEqual(theme.colors(self.dir)['secondary'], '#00FF00')

    def test_missing_or_invalid_theme_yields_none(self):
        self.assertIsNone(theme.colors(self.dir))
        (self.dir/'colors.toml').write_text('accent = [not toml')
        self.assertIsNone(theme.colors(self.dir))

    def test_symlinked_color_file_is_refused(self):
        target = self.dir/'elsewhere'; target.write_text('#00ff00')
        (self.dir/'keyboard.rgb').symlink_to(target)
        (self.dir/'colors.toml').write_text(COLORS)
        self.assertEqual(theme.colors(self.dir)['source'], 'accent')

    def test_vivid_keeps_grays_and_boosts_washed_colors(self):
        self.assertEqual(theme.vivid('#808080'), '#808080')
        self.assertEqual(theme.vivid('#5E81AC')[0:3], '#19')


class EffectAndStateTests(unittest.TestCase):
    def test_theme_sync_is_a_validated_boolean(self):
        self.assertTrue(validate_patch(DEFAULT_STATE, {'theme_sync': True})['theme_sync'])
        with self.assertRaises(ValueError): validate_patch(DEFAULT_STATE, {'theme_sync': 'yes'})

    def test_rainbow_cycles_only_palette_colors(self):
        state = dict(DEFAULT_STATE, effect='rainbow', palette=['#FF0000', '#0000FF'])
        self.assertEqual(frame(state, 2, 0), [(255, 0, 0), (0, 0, 255)])


class BackendPersistTests(unittest.TestCase):
    def setUp(self):
        from test_backend_sdk import Client, Device
        from zorya_rgb.openrgb_backend import OpenRGBBackend
        self.device = Device(); self.device.modes[0].name = 'Solid Color'
        self.backend = OpenRGBBackend(client_factory=lambda: Client([self.device]), color_factory=lambda *c: c)
        self.backend.connect()
        self.state = dict(DEFAULT_STATE, devices=[d['id'] for d in self.backend.devices([])])

    def test_static_uses_saveable_solid_color_and_saves_only_on_request(self):
        self.backend.apply(self.state, 0)
        self.assertEqual((self.device.active_mode, self.device.saves), (0, 0))
        self.backend.apply(dict(self.state, color='#00FF00'), 1, persist=True)
        self.assertEqual(self.device.saves, 1)

    def test_switch_from_palette_mode_to_direct_tracks_active_mode(self):
        stale = self.device.set_mode
        def keep_previous(mode, save=False):
            previous = self.device.active_mode; stale(mode, save); self.device.active_mode = previous
        self.device.set_mode = keep_previous
        self.backend.apply(dict(self.state, effect='rainbow'), 0)
        self.assertEqual(self.device.active_mode, 1)

    def test_themed_rainbow_streams_palette_frames(self):
        self.backend.apply(dict(self.state, effect='rainbow', palette=['#FF0000', '#0000FF']), 0)
        self.assertEqual(self.device.writes[-1][0], (255, 0, 0))


class DaemonThemeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); root = Path(self.tmp.name)
        self.colors = {'primary': '#FF0000', 'secondary': '#00FF00', 'palette': ['#FF0000', '#00FF00'], 'source': 'accent'}
        self.daemon = ZoryaDaemon(store=StateStore(root/'state.json'), backend=object(),
                                  socket_path=root/'socket', theme_reader=lambda: self.colors)
    def tearDown(self): self.tmp.cleanup()

    def test_effective_state_overlays_theme_only_when_enabled(self):
        self.daemon.store.update({'theme_sync': True}); self.daemon._check_theme(0)
        state = self.daemon.effective_state(self.daemon.store.snapshot())
        self.assertEqual((state['color'], state['secondary_color']), ('#FF0000', '#00FF00'))
        self.daemon.store.update({'theme_sync': False})
        state = self.daemon.effective_state(self.daemon.store.snapshot())
        self.assertEqual(state['color'], '#FFFFFF'); self.assertNotIn('palette', state)

    def test_flash_persist_only_on_real_theme_change(self):
        self.daemon.store.update({'theme_sync': True}); self.daemon._check_theme(0)
        self.assertFalse(self.daemon.persist)
        self.daemon._check_theme(0.5); self.assertFalse(self.daemon.persist)
        self.colors = dict(self.colors, primary='#0000FF'); self.daemon._check_theme(2)
        self.assertTrue(self.daemon.persist)

    def test_enabling_sync_requests_one_persist(self):
        self.daemon.dispatch({'command': 'set', 'patch': {'theme_sync': True}})
        self.assertTrue(self.daemon.persist)


if __name__ == '__main__':
    unittest.main()
