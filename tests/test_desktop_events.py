from pathlib import Path
import tempfile
import threading
import types
import unittest
from test_backend_sdk import Client, Device
from zorya_rgb import events
from zorya_rgb.daemon import ZoryaDaemon, CRITICAL_COLOR
from zorya_rgb.openrgb_backend import OpenRGBBackend
from zorya_rgb.state import DEFAULT_STATE, StateStore

NOTIFY = '''method call time=1 sender=:1.5 -> destination=:1.9 serial=7 path=/org/freedesktop/Notifications; interface=org.freedesktop.Notifications; member=Notify
   string "app"
   uint32 0
   string ""
   string "Hello"
   string "Body"
   array [
   ]
   array [
      dict entry(
         string "urgency"
         variant             byte {urgency}
      )
   ]
   int32 -1
'''


class ParserTests(unittest.TestCase):
    def test_workspace_events(self):
        self.assertEqual(events.parse_workspace('workspacev2>>3,3'), 3)
        self.assertEqual(events.parse_workspace('focusedmonv2>>DP-1,7'), 7)
        self.assertIsNone(events.parse_workspace('workspace>>3'))
        self.assertIsNone(events.parse_workspace('workspacev2>>special,name'))

    def test_notification_urgency_and_updates(self):
        lines = NOTIFY.format(urgency=1).splitlines()[1:]
        self.assertEqual(events.parse_notification(lines), 'normal')
        self.assertEqual(events.parse_notification(NOTIFY.format(urgency=2).splitlines()[1:]), 'critical')
        updated = [line.replace('uint32 0', 'uint32 12') for line in lines]
        self.assertIsNone(events.parse_notification(updated))

    def run_listener(self, text, dnd):
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as handle:
            handle.write(text)
        stopping = threading.Event(); received = []
        listener = events.NotificationListener(stopping, received.append, command=['cat', handle.name], dnd=lambda: dnd)
        with self.assertRaises(ConnectionError): listener.listen()
        Path(handle.name).unlink()
        return received

    def test_listener_respects_dnd_except_critical(self):
        text = NOTIFY.format(urgency=1) + NOTIFY.format(urgency=2)
        self.assertEqual(self.run_listener(text, dnd=False), ['normal', 'critical'])
        self.assertEqual(self.run_listener(text, dnd=True), ['critical'])


class DaemonOverlayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); root = Path(self.tmp.name)
        self.daemon = ZoryaDaemon(store=StateStore(root/'state.json'), backend=object(), socket_path=root/'socket')
        self.state = dict(DEFAULT_STATE, secondary_color='#00FF00', notify_flash=True, workspace_keys=True)
    def tearDown(self): self.tmp.cleanup()

    def test_no_overlay_until_events_arrive(self):
        self.assertNotIn('overlay', self.daemon.effective_state(self.state, 0))

    def test_workspace_key_uses_secondary_color_and_ten_maps_to_zero(self):
        self.daemon.on_workspace(10)
        self.assertEqual(self.daemon.effective_state(self.state, 0)['overlay']['keys'], {'Key: 0': '#00FF00'})
        self.daemon.on_workspace(42)
        self.assertNotIn('overlay', self.daemon.effective_state(self.state, 0))

    def test_flash_fades_and_expires(self):
        state = dict(self.state, flash_speed=.2, flash_count=3)
        self.daemon.on_notification('critical'); started = self.daemon.flash_started
        overlay = self.daemon.effective_state(state, started + .1)['overlay']
        self.assertAlmostEqual(overlay['flash'], 1.0); self.assertEqual(overlay['flash_color'], CRITICAL_COLOR)
        self.assertIn('overlay', self.daemon.effective_state(state, started + .55))
        self.assertNotIn('overlay', self.daemon.effective_state(state, started + .61))
        self.assertIsNone(self.daemon.flash_started)

    def test_flash_settings_are_validated(self):
        from zorya_rgb.state import validate_patch
        self.assertEqual(validate_patch(DEFAULT_STATE, {'flash_count': 4, 'flash_speed': .1})['flash_count'], 4)
        for bad in ({'flash_count': 0}, {'flash_count': 2.0}, {'flash_speed': .05}, {'flash_speed': 2}):
            with self.assertRaises(ValueError): validate_patch(DEFAULT_STATE, bad)

    def test_disabled_settings_ignore_events(self):
        self.daemon.on_workspace(2); self.daemon.on_notification('normal')
        state = dict(self.state, notify_flash=False, workspace_keys=False)
        self.assertNotIn('overlay', self.daemon.effective_state(state, self.daemon.flash_started))


class BackendOverlayTests(unittest.TestCase):
    def setUp(self):
        self.device = Device(location='HID: /dev/hidraw9')
        self.device.leds = [types.SimpleNamespace(name=n) for n in ('Key: Escape', 'Key: 1', 'Key: 2', 'Key: 3')]
        solid = self.device.modes[0]
        solid.name, solid.flags, solid.color_mode = 'Solid Color', 64 | 256, 2
        self.backend = OpenRGBBackend(client_factory=lambda: Client([self.device]), color_factory=lambda *c: c)
        self.backend.connect()
        self.state = dict(DEFAULT_STATE, color='#FF0000', devices=[d['id'] for d in self.backend.devices([])])

    def test_key_overlay_switches_to_direct_and_restores_base(self):
        self.backend.apply(self.state, 0); self.assertEqual(self.device.active_mode, 0)
        self.backend.apply(dict(self.state, overlay={'keys': {'Key: 2': '#00FF00'}}), 1)
        self.assertEqual(self.device.active_mode, 1)
        self.assertEqual(self.device.writes[-1], [(255, 0, 0), (255, 0, 0), (0, 255, 0), (255, 0, 0)])
        self.backend.apply(self.state, 2); self.assertEqual(self.device.active_mode, 0)

    def test_flash_blends_every_led(self):
        self.backend.apply(dict(self.state, overlay={'flash': .5, 'flash_color': '#0000FF'}), 0)
        self.assertEqual(self.device.writes[-1][0], (128, 0, 128))

    def test_overlay_keeps_pending_save_for_base_mode(self):
        self.backend.apply(self.state, 0, persist=True)
        self.backend.apply(dict(self.state, overlay={'keys': {'Key: 1': '#00FF00'}}), .5)
        self.backend.apply(self.state, 1.2)
        self.backend.apply(self.state, 2.5)
        self.assertEqual(self.device.saves, 1)

    def test_lights_off_ignore_overlay(self):
        self.backend.apply(dict(self.state, on=False, overlay={'keys': {'Key: 1': '#00FF00'}}), 0)
        self.assertNotIn((0, 255, 0), self.device.writes[-1] if self.device.writes else [])


if __name__ == '__main__':
    unittest.main()
