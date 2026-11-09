"""
Windows'a özgü işler: Windows ile başlatma, paket (MSIX) tespiti, tek kopya çalıştırma.
Windows dışında güvenli şekilde "desteklenmiyor" döner.
"""

import asyncio
import os
import socket
import sys
import threading

APP_NAME = "ShareQR"
STARTUP_TASK_ID = "ShareQRStartup"  # AppxManifest.xml ile aynı olmalı
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
INSTANCE_PORT = 47613  # tek kopya kontrolü için yalnızca 127.0.0.1


def is_windows():
    return sys.platform == "win32"


def is_packaged():
    """Uygulama MSIX paketi olarak (Store'dan) mı çalışıyor?"""
    if not is_windows():
        return False
    import ctypes

    length = ctypes.c_uint32(0)
    rc = ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
    return rc != 15700  # APPMODEL_ERROR_NO_PACKAGE


def launched_by_startup():
    """Windows açılışında otomatik mi başlatıldık? (o zaman pencere açmadan tepsiye otur)"""
    if "--startup" in sys.argv:
        return True
    if not is_packaged():
        return False
    try:
        from winrt.windows.applicationmodel import AppInstance

        args = AppInstance.get_activated_event_args()
        return args is not None and int(args.kind) == 1020  # ActivationKind.StartupTask
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Windows ile başlat
# ---------------------------------------------------------------------------


def _exe_command():
    if getattr(sys, "frozen", False):
        return '"%s" --startup' % sys.executable
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    main = os.path.abspath(sys.argv[0])
    return '"%s" "%s" --startup' % (pyw if os.path.exists(pyw) else sys.executable, main)


async def _task():
    from winrt.windows.applicationmodel import StartupTask

    return await StartupTask.get_async(STARTUP_TASK_ID)


def _run(coro):
    return asyncio.run(coro)


# StartupTaskState: 0 Disabled, 1 DisabledByUser, 2 Enabled, 3 DisabledByPolicy, 4 EnabledByPolicy
def startup_state():
    """Döndürür: {"supported", "enabled", "locked", "note"}  (note: çeviri anahtarı veya boş)"""
    if not is_windows():
        return {"supported": False, "enabled": False, "locked": False, "note": "Windows only"}
    if is_packaged():
        try:
            state = int(_run(_task()).state)
        except Exception as e:  # winrt yoksa / hata
            return {"supported": False, "enabled": False, "locked": False, "note": str(e)}
        if state == 1:
            return {"supported": True, "enabled": False, "locked": True, "note": "settings.startup.user"}
        if state in (3, 4):
            return {"supported": True, "enabled": state == 4, "locked": True, "note": "settings.startup.policy"}
        return {"supported": True, "enabled": state == 2, "locked": False, "note": ""}

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            enabled = True
    except OSError:
        enabled = False
    return {"supported": True, "enabled": enabled, "locked": False, "note": ""}


def set_startup(enable):
    if not is_windows():
        return startup_state()
    if is_packaged():
        async def change():
            task = await _task()
            if enable:
                await task.request_enable_async()
            else:
                task.disable()

        try:
            _run(change())
        except Exception:
            pass
        return startup_state()

    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
        if enable:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, _exe_command())
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except OSError:
                pass
    return startup_state()


# ---------------------------------------------------------------------------
# Tek kopya: ikinci kez açılırsa mevcut pencereyi göster
# ---------------------------------------------------------------------------


class SingleInstance:
    def __init__(self, on_show):
        self.on_show = on_show
        self.sock = None

    def acquire(self):
        """İlk kopyaysa True döner ve dinlemeye başlar; değilse ilk kopyaya 'göster' der, False döner."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            s.bind(("127.0.0.1", INSTANCE_PORT))
        except OSError:
            s.close()
            try:
                with socket.create_connection(("127.0.0.1", INSTANCE_PORT), timeout=2) as c:
                    c.sendall(b"show")
            except OSError:
                pass
            return False
        s.listen(2)
        self.sock = s
        threading.Thread(target=self._loop, daemon=True).start()
        return True

    def _loop(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                try:
                    if conn.recv(16) == b"show":
                        self.on_show()
                except OSError:
                    pass
