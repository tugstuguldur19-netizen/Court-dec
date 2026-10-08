"""Keep one checker window open.

Loading the dictionaries takes several seconds, so when the checker is
started again (for example from the Office ribbon button) the new process
hands its request to the window that is already running and exits.

The running window listens on a random port on 127.0.0.1 only, and accepts
a request only with the secret token it wrote to the user's settings folder,
so other users of the computer cannot send it anything.
"""

import json
import os
import secrets
import socket
import sys
import threading

from . import paths

_MAX_REQUEST = 64 * 1024
_KNOWN = {"path", "live"}


def _info_path():
    return os.path.join(paths.user_dir(), "instance.json")


def _read_info():
    try:
        with open(_info_path(), encoding="utf-8") as f:
            info = json.load(f)
        if isinstance(info, dict) and isinstance(info.get("port"), int) and info.get("token"):
            return info
    except (OSError, ValueError):
        pass
    return None


def _allow_foreground(pid):
    """Let the running window come to the front (Windows only lets the
    foreground process do that, and this process was just started by it)."""
    if sys.platform == "win32" and pid:
        try:
            import ctypes
            ctypes.windll.user32.AllowSetForegroundWindow(int(pid))
        except Exception:
            pass


def hand_off(request, timeout=3.0):
    """Send request to the running window. True if it took it."""
    info = _read_info()
    if not info:
        return False
    _allow_foreground(info.get("pid"))
    message = dict(request, token=info["token"])
    try:
        with socket.create_connection(("127.0.0.1", info["port"]), timeout=timeout) as s:
            s.sendall(json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n")
            reply = s.makefile("rb").readline(16)
        return reply.strip() == b"ok"
    except (OSError, ValueError):
        return False


class Server:
    """Accepts requests from later starts and passes them to on_request(dict),
    which is called on a background thread."""

    def __init__(self, on_request):
        self.on_request = on_request
        self.token = secrets.token_hex(16)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(4)
        self.port = self.sock.getsockname()[1]
        self._closed = False
        try:
            os.makedirs(paths.user_dir(), exist_ok=True)
            with open(_info_path(), "w", encoding="utf-8") as f:
                json.dump({"port": self.port, "token": self.token, "pid": os.getpid()}, f)
        except OSError:
            pass   # still works as a single window, just without hand-off
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while not self._closed:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                try:
                    conn.settimeout(3)
                    line = conn.makefile("rb").readline(_MAX_REQUEST)
                    req = json.loads(line.decode("utf-8"))
                    if not isinstance(req, dict) or not secrets.compare_digest(str(req.get("token", "")), self.token):
                        conn.sendall(b"denied\n")
                        continue
                    conn.sendall(b"ok\n")
                except (OSError, ValueError):
                    continue
            self.on_request({k: v for k, v in req.items() if k in _KNOWN and isinstance(v, str)})

    def close(self):
        self._closed = True
        try:
            self.sock.close()
        except OSError:
            pass
        info = _read_info()
        if info and info.get("token") == self.token:
            try:
                os.remove(_info_path())
            except OSError:
                pass
