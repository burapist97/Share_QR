"""
QR Paylaş (Windows) - sistem tepsisinde duran, tıklanınca küçük bir pencere açan uygulama.

Çalıştırma (geliştirme):  python qr_paylas_win.py
Paketleme:                ../build.ps1   (PyInstaller + MSIX)
"""

import json
import os
import subprocess
import sys
import threading
import webbrowser

import core
import i18n
import winplat
from i18n import UserError

VERSION = "1.1.0"
WIN_W, WIN_H = 380, 660


def resource(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def settings_path():
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.config")
    folder = os.path.join(root, "QRPaylas")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "settings.json")


def load_settings():
    try:
        with open(settings_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        with open(settings_path(), "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except OSError:
        pass


class Api:
    """JavaScript'ten window.pywebview.api.<ad>() ile çağrılır.
    Not: '_' ile başlayan nitelikler JavaScript'e açılmaz."""

    def __init__(self, app):
        self._app = app

    def _err(self, e):
        if isinstance(e, UserError):
            return {"error": e.message(self._app.lang)}
        return {"error": i18n.t(self._app.lang, "err.generic", msg=str(e) or e.__class__.__name__)}

    # --- başlangıç / ayarlar ---
    def init(self):
        return {
            "version": VERSION,
            "lang": self._app.lang,
            "strings": i18n.STRINGS,
            "settings": load_settings(),
            "services": core.services_info(),
            "networks": core.list_networks(),
        }

    def save_settings(self, data):
        save_settings(data)

    def set_language(self, lang):
        self._app.lang = i18n.norm(lang)
        self._app.update_tray()
        return self._app.lang

    def startup_state(self):
        return winplat.startup_state()

    def set_startup(self, enable):
        state = winplat.set_startup(bool(enable))
        self._app.update_tray()
        return state

    def refresh_networks(self):
        nets = core.list_networks()
        self._app.js("app.networks(%s)" % json.dumps(nets))
        return nets

    # --- dosyalar ---
    def pick_files(self):
        import webview

        paths = self._app.window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=True) or []
        return [core.file_info(p) for p in paths if os.path.exists(p)]

    def share_wifi(self, paths, ip):
        try:
            if not ip:
                raise UserError("err.no_network")
            url = self._app.server.share(paths, ip)
            return {"url": url, "qr": core.qr_svg(url)}
        except Exception as e:
            return self._err(e)

    def stop_wifi(self):
        self._app.server.stop()
        return True

    def share_internet(self, paths, service):
        def progress(p):
            self._app.js("app.progress(%f)" % p)

        try:
            r = core.upload(paths, service, self._app.server.tmpdir, progress)
        except Exception as e:
            return self._err(e)
        r["qr"] = core.qr_svg(r["url"])
        return r

    # --- link → QR ---
    def qr(self, text):
        text = (text or "").strip()
        return core.qr_svg(text) if text else ""

    def save_png(self, text):
        import webview

        text = (text or "").strip()
        if not text:
            return False
        path = self._app.window.create_file_dialog(webview.FileDialog.SAVE, save_filename="qr-code.png",
                                                   file_types=("PNG (*.png)",))
        if isinstance(path, (list, tuple)):
            path = path[0] if path else None
        if not path:
            return False
        if not path.lower().endswith(".png"):
            path += ".png"
        core.qr_png(text, path)
        return True

    # --- diğer ---
    def copy(self, text):
        if sys.platform == "win32":
            subprocess.run(
                ["clip"], input=("﻿" + text).encode("utf-16-le"),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        return True

    def open_url(self, url):
        webbrowser.open(url)

    def hide(self):
        self._app.hide()

    def quit(self):
        self._app.quit()


class App:
    def __init__(self):
        self.lang = i18n.norm(load_settings().get("lang") or i18n.DEFAULT)
        self.server = core.ShareServer()
        self.server.on_download = lambda name: self.js("app.downloaded(%s)" % json.dumps(name))
        self.api = Api(self)
        self.window = None
        self.tray = None
        self.visible = False
        self.quitting = False

    def t(self, key, **kw):
        return i18n.t(self.lang, key, **kw)

    # --- pencere ---
    def js(self, code):
        if self.window:
            try:
                self.window.evaluate_js(code)
            except Exception:
                pass

    def position(self):
        import webview

        try:
            sc = webview.screens[0]
            x = sc.x + sc.width - WIN_W - 12
            y = sc.y + sc.height - WIN_H - 60  # görev çubuğunun üstü
            self.window.move(max(sc.x, x), max(sc.y, y))
        except Exception:
            pass

    def show(self):
        if not self.window:
            return
        self.position()
        self.window.show()
        self.window.restore()
        self.visible = True

    def hide(self):
        if self.window:
            self.window.hide()
        self.visible = False

    def toggle(self, *_):
        self.hide() if self.visible else self.show()

    def on_closing(self):
        # Pencerenin kapatılması uygulamayı kapatmaz, tepsiye gizler
        if self.quitting:
            return True
        threading.Thread(target=self.hide, daemon=True).start()
        return False

    def on_loaded(self):
        from webview.dom import DOMEventHandler

        def on_drop(e):
            files = (e.get("dataTransfer") or {}).get("files") or []
            paths = [f.get("pywebviewFullPath") for f in files if f.get("pywebviewFullPath")]
            infos = [core.file_info(p) for p in paths if os.path.exists(p)]
            if infos:
                self.js("app.dropped(%s)" % json.dumps(infos))

        try:
            self.window.dom.document.events.drop += DOMEventHandler(on_drop, True, True)
        except Exception:
            pass

    def quit(self, *_):
        self.quitting = True
        try:
            self.server.shutdown()
        finally:
            if self.tray:
                self.tray.stop()
            if self.window:
                self.window.destroy()

    # --- sistem tepsisi ---
    def make_tray(self):
        import pystray
        from PIL import Image

        def startup_checked(item):
            return winplat.startup_state().get("enabled", False)

        def toggle_startup(icon, item):
            winplat.set_startup(not startup_checked(item))

        menu = pystray.Menu(
            pystray.MenuItem(lambda item: self.t("tray.open"), self.toggle, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: self.t("tray.startup"), toggle_startup, checked=startup_checked,
                             enabled=lambda item: winplat.startup_state().get("supported", False)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: self.t("tray.quit"), self.quit),
        )
        self.tray = pystray.Icon("QRPaylas", Image.open(resource("assets", "tray.png")), "QR Paylaş", menu)
        self.tray.run_detached()

    def update_tray(self):
        if self.tray:
            try:
                self.tray.update_menu()
            except Exception:
                pass

    # --- başlat ---
    def run(self):
        import webview

        start_hidden = winplat.launched_by_startup()
        self.window = webview.create_window(
            "QR Paylaş",
            resource("ui", "index.html"),
            js_api=self.api,
            width=WIN_W,
            height=WIN_H,
            resizable=False,
            frameless=True,
            easy_drag=False,
            on_top=True,
            hidden=True,
            background_color="#F5F5F7",
        )
        self.window.events.closing += self.on_closing
        self.window.events.loaded += self.on_loaded

        def after_start():
            self.make_tray()
            if not start_hidden:
                self.show()

        webview.start(after_start, http_server=True, private_mode=True, icon=resource("assets", "app.ico"))


def selftest():
    """Derlenmiş exe'nin temel parçalarını pencere açmadan dener (CI için)."""
    import urllib.request

    out = []
    srv = core.ShareServer()
    here = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
    url = srv.share([here], "127.0.0.1")
    for lang, word in (("en", "Download"), ("tr", "İndir"), ("es", "Descargar")):
        req = urllib.request.Request(url, headers={"Accept-Language": lang})
        page = urllib.request.urlopen(req, timeout=5).read().decode()
        assert word in page, "telefon sayfası (%s)" % lang
    dl = url + "/dl/" + list(srv.files)[0]
    assert urllib.request.urlopen(dl, timeout=5).read() == open(here, "rb").read(), "indirme"
    out.append("server ok")
    assert core.qr_svg(url).startswith("<svg"), "qr"
    out.append("qr ok")
    out.append("networks %d" % len(core.list_networks()))
    out.append("startup %s" % winplat.startup_state())
    import webview, pystray, PIL  # noqa: F401  (paketlenmiş mi?)
    for f in (("ui", "index.html"), ("assets", "tray.png"), ("i18n.json",)):
        assert os.path.exists(resource(*f)), "kaynak eksik: %s" % "/".join(f)
    out.append("resources ok")
    srv.shutdown()
    return out


def main():
    if "--selftest" in sys.argv:
        log = os.path.join(os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__), "selftest.log")
        try:
            res = selftest()
            with open(log, "w", encoding="utf-8") as fh:
                fh.write("OK\n" + "\n".join(res) + "\n")
            sys.exit(0)
        except Exception:
            import traceback

            with open(log, "w", encoding="utf-8") as fh:
                fh.write("FAIL\n" + traceback.format_exc())
            sys.exit(1)

    app = App()
    if not winplat.SingleInstance(app.show).acquire():
        return  # zaten açık: mevcut pencere öne getirildi
    app.run()


if __name__ == "__main__":
    main()
