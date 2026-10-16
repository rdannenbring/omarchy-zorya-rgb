"""Read-only Omarchy theme colors mapped to LED-friendly lighting colors."""
from __future__ import annotations
import colorsys
import os
from pathlib import Path
import re
import stat
import tomllib

MAX_FILE=64*1024
PALETTE_KEYS=('red','yellow','green','cyan','blue','magenta')
HEX=re.compile(r'#?([0-9a-fA-F]{6})')


def theme_dir():
    base=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))
    return base/'omarchy'/'current'/'theme'


def _read(path):
    # current/theme is a symlink by design; refuse anything but a small regular file.
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_FILE: return None
        return os.read(fd,MAX_FILE).decode('utf-8','replace')
    finally:
        os.close(fd)


def _hex(value):
    match=HEX.fullmatch(value.strip()) if isinstance(value,str) else None
    return '#'+match.group(1).upper() if match else None


def vivid(color):
    """Boost saturation and value so theme colors read true on LEDs.

    Adapted from Omakeychron (paulsp94, MIT). Near-grays pass through; hues in the
    green-cyan band are pulled toward green because LEDs render them bluer.
    """
    r,g,b=(int(color[i:i+2],16)/255 for i in (1,3,5))
    h,s,v=colorsys.rgb_to_hsv(r,g,b)
    if s>=.15:
        s=max(s,.9); v=1.0
        degrees=h*360
        if 120<degrees<180: h=(120+(degrees-120)*.2)/360
    return '#%02X%02X%02X'%tuple(round(x*255) for x in colorsys.hsv_to_rgb(h,s,v))


def _hue(color):
    r,g,b=(int(color[i:i+2],16)/255 for i in (1,3,5))
    h,s,_=colorsys.rgb_to_hsv(r,g,b)
    return h,s


def colors(directory=None):
    """Return the active theme's lighting colors, or None without usable colors.

    primary: keyboard.rgb when the theme ships one, otherwise the accent.
    secondary: the palette color closest to 120 degrees of hue from primary.
    palette: the theme's saturated ANSI colors ordered by hue, for color cycling.
    """
    directory=Path(directory) if directory else theme_dir()
    try:
        table=tomllib.loads(_read(directory/'colors.toml') or '')
    except tomllib.TOMLDecodeError:
        table={}
    keyboard=_hex(_read(directory/'keyboard.rgb') or '')
    primary=keyboard or _hex(table.get('accent'))
    if primary is None: return None
    primary=vivid(primary)
    palette=[vivid(c) for c in (_hex(table.get(k)) for k in PALETTE_KEYS) if c and _hue(c)[1]>=.15]
    palette=sorted(dict.fromkeys(palette),key=lambda c:_hue(c)[0])
    base,_=_hue(primary)
    def triadic_error(color):
        delta=abs(_hue(color)[0]-base)
        return abs(min(delta,1-delta)-1/3)
    # A complement would fade through gray at the gradient midpoint; a color about
    # 120 degrees away stays saturated across the blend while still contrasting.
    secondary=min(palette,key=triadic_error) if palette else primary
    return {'primary':primary,'secondary':secondary,'palette':palette or [primary],
            'source':'keyboard.rgb' if keyboard else 'accent'}
