"""Desktop event listeners: Hyprland workspaces and desktop notifications.

Both run as daemon threads, reconnect with backoff and only report events through
callbacks. They never touch hardware.
"""
from __future__ import annotations
import json
import logging
import os
from pathlib import Path
import re
import socket
import subprocess
import threading

LOG=logging.getLogger(__name__)
NOTIFY_MONITOR=['dbus-monitor','--session','--monitor',
                "type='method_call',interface='org.freedesktop.Notifications',member='Notify'"]


def hyprland_dir():
    signature=os.environ.get('HYPRLAND_INSTANCE_SIGNATURE')
    runtime=os.environ.get('XDG_RUNTIME_DIR')
    if not signature or not runtime or '/' in signature: return None
    return Path(runtime)/'hypr'/signature


def parse_workspace(line):
    """Return the workspace ID from a socket2 event line, or None."""
    event,_,data=line.partition('>>')
    if event=='workspacev2': value=data.split(',',1)[0]
    elif event=='focusedmonv2': value=data.rsplit(',',1)[-1]
    else: return None
    return int(value) if value.lstrip('-').isdigit() else None


def parse_notification(lines):
    """Classify one Notify call block: None to ignore, else 'normal' or 'critical'."""
    body='\n'.join(lines)
    ids=re.findall(r'^\s*uint32 (\d+)',body,re.M)
    if ids and ids[0]!='0': return None  # updates an existing notification
    if re.search(r'string "urgency"\s*\n\s*variant\s+byte 2',body): return 'critical'
    return 'normal'


def dnd_on():
    try:
        out=subprocess.run(['omarchy-shell','notifications','isDnd'],capture_output=True,text=True,timeout=2).stdout.strip()
    except (OSError,subprocess.SubprocessError):
        return False
    return out=='on'


class Listener:
    def __init__(self,stopping):
        self.stopping=stopping; self.thread=None

    def start(self):
        self.thread=threading.Thread(target=self._run,name=type(self).__name__,daemon=True)
        self.thread.start()

    def _run(self):
        delay=1
        while not self.stopping.is_set():
            try:
                self.listen(); delay=1
            except Exception as exc:
                LOG.info("%s unavailable (%s); retrying",type(self).__name__,type(exc).__name__)
            self.stopping.wait(delay); delay=min(delay*2,30)


class WorkspaceListener(Listener):
    def __init__(self,stopping,on_workspace,directory=None):
        super().__init__(stopping); self.on_workspace=on_workspace; self.directory=directory

    def _request(self,directory,command):
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.settimeout(2); client.connect(str(directory/'.socket.sock'))
            client.sendall(command.encode()); data=b''
            while len(data)<65536:
                part=client.recv(8192)
                if not part: break
                data+=part
            return data.decode('utf-8','replace')

    def listen(self):
        directory=self.directory or hyprland_dir()
        if directory is None: raise RuntimeError('Hyprland instance not found')
        active=json.loads(self._request(directory,'j/activeworkspace'))
        self.on_workspace(int(active['id']))
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as events:
            events.settimeout(1); events.connect(str(directory/'.socket2.sock')); buffer=b''
            while not self.stopping.is_set():
                try: part=events.recv(8192)
                except socket.timeout: continue
                if not part: raise ConnectionError('Hyprland closed the event socket')
                buffer+=part
                *lines,buffer=buffer.split(b'\n')
                buffer=buffer[-4096:]
                for line in lines:
                    workspace=parse_workspace(line.decode('utf-8','replace'))
                    if workspace is not None: self.on_workspace(workspace)


class NotificationListener(Listener):
    def __init__(self,stopping,on_notification,command=None,dnd=dnd_on):
        super().__init__(stopping); self.on_notification=on_notification
        self.command=command or NOTIFY_MONITOR; self.dnd=dnd

    def listen(self):
        process=subprocess.Popen(self.command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1)
        try:
            block=None
            def flush():
                kind=parse_notification(block) if block is not None else None
                # Critical notifications still flash while Do Not Disturb is on.
                if kind and (kind=='critical' or not self.dnd()): self.on_notification(kind)
            for line in process.stdout:
                if self.stopping.is_set(): break
                if line.startswith('method call'):
                    flush(); block=[] if 'member=Notify' in line else None
                elif line.startswith(('signal','method return','error')):
                    flush(); block=None
                elif block is not None:
                    block.append(line.rstrip('\n'))
                    # The timeout int32 is the final Notify argument.
                    if line.lstrip().startswith('int32 '): flush(); block=None
                    elif len(block)>400: block=None
        finally:
            process.stdout.close()
            process.terminate()
            try: process.wait(2)
            except subprocess.TimeoutExpired: process.kill()
        if not self.stopping.is_set(): raise ConnectionError('dbus-monitor exited')
