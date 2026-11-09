"""
QR Paylaş - çekirdek: paylaşım sunucusu, ağ listesi, internet yüklemeleri, QR üretimi.
GUI'den bağımsızdır; Linux/Mac'te de test edilebilir.
"""

import html
import http.client
import io
import json
import os
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, urlparse

from i18n import UserError, from_accept_language, t

CHUNK = 1024 * 1024
PORT_RANGE = (8765, 8814)  # AppxManifest'teki güvenlik duvarı kuralıyla aynı aralık
MB = 1024 * 1024
GB = 1024 * MB


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%d %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit)).replace(".0 ", " ")
        n /= 1024.0


def file_info(path):
    path = os.path.abspath(path)
    is_dir = os.path.isdir(path)
    return {
        "path": path,
        "name": os.path.basename(path.rstrip("\\/")),
        "size": dir_size(path) if is_dir else os.path.getsize(path),
        "dir": is_dir,
    }


def dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


# ---------------------------------------------------------------------------
# QR
# ---------------------------------------------------------------------------


def qr_svg(text):
    """QR kodu ölçeklenebilir SVG metni olarak döndürür."""
    import segno

    buf = io.BytesIO()
    segno.make(text, error="m", micro=False).save(
        buf, kind="svg", scale=1, border=2, dark="#000", light="#fff",
        xmldecl=False, svgns=True, omitsize=True,
    )
    return buf.getvalue().decode("utf-8")


def qr_png(text, path, scale=16):
    import segno

    segno.make(text, error="m", micro=False).save(path, kind="png", scale=scale, border=3)


# ---------------------------------------------------------------------------
# Ağlar
# ---------------------------------------------------------------------------


def default_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def wifi_ssid():
    """Windows'ta bağlı Wi-Fi ağının adını döndürür (yoksa None)."""
    if sys.platform != "win32":
        return None
    try:
        out = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            timeout=4,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
        text = out.decode("oem", "replace")  # netsh konsol kod sayfasıyla yazar
        m = re.search(r"^\s*SSID\s*:\s*(.+?)\s*$", text, re.M)
        return m.group(1) if m else None
    except Exception:
        return None


def list_networks():
    """Paylaşım yapılabilecek ağ bağdaştırıcılarını listeler."""
    nets = []
    try:
        import psutil

        stats = psutil.net_if_stats()
        for name, addrs in psutil.net_if_addrs().items():
            if name in stats and not stats[name].isup:
                continue
            for a in addrs:
                if a.family != socket.AF_INET:
                    continue
                ip = a.address
                if ip.startswith("127.") or ip.startswith("169.254."):
                    continue
                nets.append({"name": name, "ip": ip})
    except ImportError:
        pass

    dip = default_ip()
    if dip and not any(n["ip"] == dip for n in nets):
        nets.append({"name": "LAN", "ip": dip})

    ssid = wifi_ssid()
    for n in nets:
        low = n["name"].lower()
        n["wifi"] = any(k in low for k in ("wi-fi", "wifi", "wlan", "wireless", "kablosuz", "inalámbrica"))
        n["virtual"] = any(k in low for k in ("vethernet", "virtual", "vmware", "virtualbox", "hyper-v", "wsl",
                                              "docker", "loopback", "tailscale", "zerotier", "vpn"))
        n["label"] = ("Wi-Fi · %s" % ssid) if (n["wifi"] and ssid) else n["name"]
        n["default"] = n["ip"] == dip

    # Önce varsayılan, sonra Wi-Fi, sanal bağdaştırıcılar en sonda
    nets.sort(key=lambda n: (not n["default"], not n["wifi"], n["virtual"], n["name"]))
    return nets


# ---------------------------------------------------------------------------
# Yerel ağ paylaşım sunucusu (telefon bu sunucudan indirir)
# ---------------------------------------------------------------------------

PHONE_CSS = """
:root{--bg:#f6f6f8;--card:#fff;--text:#1d1d1f;--muted:#86868b;--line:rgba(0,0,0,.06);--accent:#0a7cff;--tint:rgba(10,124,255,.1)}
@media (prefers-color-scheme:dark){:root{--bg:#111113;--card:#1c1c1f;--text:#f5f5f7;--muted:#98989d;--line:rgba(255,255,255,.07);--accent:#4aa0ff;--tint:rgba(74,160,255,.16)}}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.4 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
main{max-width:560px;margin:0 auto;padding:max(28px,env(safe-area-inset-top)) 20px 40px}
.badge{width:52px;height:52px;border-radius:16px;background:var(--tint);display:grid;place-items:center;margin-bottom:16px}
.badge svg{width:26px;height:26px;fill:var(--accent)}
h1{font-size:30px;font-weight:700;letter-spacing:-.4px;margin:0 0 6px}
.sub{color:var(--muted);font-size:15px;margin:0 0 24px}
.card{background:var(--card);border-radius:20px;padding:6px 0;box-shadow:0 1px 2px rgba(0,0,0,.03),0 8px 24px rgba(0,0,0,.04)}
.row{display:flex;align-items:center;gap:14px;padding:12px 18px}
.row+.row{border-top:1px solid var(--line)}
.ic{width:40px;height:40px;border-radius:12px;background:var(--tint);display:grid;place-items:center;flex:none}
.ic svg{width:20px;height:20px;fill:var(--accent)}
.meta{flex:1;min-width:0}
.name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:500}
.size{color:var(--muted);font-size:13px}
.get{background:var(--accent);color:#fff;font-weight:600;font-size:15px;border-radius:999px;padding:8px 18px;text-decoration:none}
.info{margin-top:22px;background:var(--card);border-radius:20px;padding:16px 18px;font-size:14px;color:var(--muted)}
.info b{display:block;color:var(--text);font-weight:600;margin-bottom:6px}
.info div{margin:2px 0}
.foot{color:var(--muted);font-size:13px;text-align:center;margin-top:22px}
.empty{padding:28px 18px;color:var(--muted);text-align:center}
"""

ICON_DOC = '<svg viewBox="0 0 24 24"><path d="M7 2.5h6.6c.4 0 .8.2 1.1.4l4.4 4.4c.3.3.4.7.4 1.1V19a2.5 2.5 0 0 1-2.5 2.5H7A2.5 2.5 0 0 1 4.5 19V5A2.5 2.5 0 0 1 7 2.5zm6 1.8V8a1 1 0 0 0 1 1h3.7z"/></svg>'
ICON_DOWN = '<svg viewBox="0 0 24 24"><path d="M12 3a1 1 0 0 1 1 1v9.6l3.3-3.3a1 1 0 1 1 1.4 1.4l-5 5a1 1 0 0 1-1.4 0l-5-5a1 1 0 1 1 1.4-1.4l3.3 3.3V4a1 1 0 0 1 1-1zM5 19h14a1 1 0 1 1 0 2H5a1 1 0 1 1 0-2z"/></svg>'
ICON_LOCK = '<svg viewBox="0 0 24 24"><path d="M12 2.5A4.5 4.5 0 0 0 7.5 7v3H7a2 2 0 0 0-2 2v7.5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V12a2 2 0 0 0-2-2h-.5V7A4.5 4.5 0 0 0 12 2.5zm-2.5 7.5V7a2.5 2.5 0 0 1 5 0v3z"/></svg>'


def phone_page(lang, token, files):
    def T(k, **kw):
        return html.escape(t(lang, k, **kw))

    if files is None:
        body = '<div class="badge">%s</div><h1>%s</h1><p class="sub">%s</p>' % (
            ICON_LOCK, T("phone.title"), T("phone.ended"))
    else:
        if files:
            rows = "".join(
                '<div class="row"><div class="ic">%s</div><div class="meta"><div class="name">%s</div>'
                '<div class="size">%s</div></div><a class="get" href="/%s/dl/%s">%s</a></div>'
                % (ICON_DOC, html.escape(f["name"]), human_size(f["size"]), token, fid, T("phone.download"))
                for fid, f in files.items()
            )
        else:
            rows = '<div class="empty">%s</div>' % T("phone.empty")
        body = (
            '<div class="badge">%s</div><h1>%s</h1><p class="sub">%s</p><div class="card">%s</div>'
            '<div class="info"><b>%s</b><div>%s</div><div>%s</div></div><p class="foot">%s</p>'
            % (ICON_DOWN, T("phone.title"), T("phone.count.one" if len(files) == 1 else "phone.count.other", n=len(files)), rows,
               T("phone.hint.title"), T("phone.hint.ios"), T("phone.hint.android"), T("phone.foot"))
        )
    return (
        '<!doctype html><html lang="%s"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<meta name="color-scheme" content="light dark"><title>QR Paylaş</title><style>%s</style></head>'
        '<body><main>%s</main></body></html>' % (lang, PHONE_CSS, body)
    )


class ShareServer:
    """Seçilen dosyaları rastgele bir anahtarla yerel ağda sunar."""

    def __init__(self):
        self.files = {}  # id -> {"name", "path", "size"}
        self.token = None
        self.httpd = None
        self.port = None
        self.tmpdir = tempfile.mkdtemp(prefix="qr_paylas_")
        self.on_download = None
        self._lock = threading.Lock()

    def share(self, paths, ip):
        self.ensure_running()
        entries = {}
        for p in paths:
            p = os.path.abspath(p)
            if os.path.isdir(p):
                p = self._zip_dir(p)
            if os.path.isfile(p):
                entries[secrets.token_urlsafe(6)] = {"name": os.path.basename(p), "path": p, "size": os.path.getsize(p)}
        with self._lock:
            self.files = entries
            self.token = secrets.token_urlsafe(8)
        return "http://%s:%d/%s" % (ip, self.port, self.token)

    def stop(self):
        """Paylaşımı bitirir ve sunucuyu kapatır (port artık dinlenmez)."""
        with self._lock:
            self.files = {}
            self.token = None
        if self.httpd:
            httpd, self.httpd = self.httpd, None
            httpd.shutdown()
            httpd.server_close()

    def _zip_dir(self, folder):
        base = os.path.join(self.tmpdir, secrets.token_hex(4), os.path.basename(folder.rstrip("\\/")))
        os.makedirs(os.path.dirname(base), exist_ok=True)
        return shutil.make_archive(base, "zip", folder)

    def ensure_running(self):
        if self.httpd:
            return
        for port in range(PORT_RANGE[0], PORT_RANGE[1] + 1):
            try:
                self.httpd = ThreadingHTTPServer(("0.0.0.0", port), self._handler())
                self.httpd.daemon_threads = True
                self.port = port
                break
            except OSError:
                continue
        if not self.httpd:
            raise UserError("err.port")
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def shutdown(self):
        self.stop()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _handler(self):
        srv = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "QRPaylas"

            def log_message(self, *a):
                pass

            def send_text(self, body, ctype="text/html; charset=utf-8", code=200):
                body = body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                lang = from_accept_language(self.headers.get("Accept-Language"))
                parts = urlparse(self.path).path.strip("/").split("/")
                with srv._lock:
                    token, files = srv.token, dict(srv.files)
                if not token or not parts or parts[0] != token:
                    return self.send_text(phone_page(lang, None, None), code=403)
                if len(parts) == 1:
                    return self.send_text(phone_page(lang, token, files))
                if len(parts) == 3 and parts[1] == "dl" and parts[2] in files:
                    return self.send_file(files[parts[2]])
                self.send_text("Not found", "text/plain; charset=utf-8", 404)

            def send_file(self, info):
                path = info["path"]
                if not os.path.isfile(path):
                    return self.send_text("Not found", "text/plain; charset=utf-8", 404)
                size = os.path.getsize(path)
                start, end, partial = 0, size - 1, False
                rng = self.headers.get("Range", "")
                m = re.match(r"bytes=(\d*)-(\d*)$", rng.split(",")[0].strip())
                if m and (m.group(1) or m.group(2)):
                    if m.group(1):
                        start = int(m.group(1))
                        end = int(m.group(2)) if m.group(2) else size - 1
                    else:
                        start = max(0, size - int(m.group(2)))
                    end = min(end, size - 1)
                    partial = start <= end
                    if not partial:
                        start, end = 0, size - 1
                length = max(0, end - start + 1)
                ascii_name = info["name"].encode("ascii", "replace").decode().replace('"', "_")
                self.send_response(206 if partial else 200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                if partial:
                    self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
                self.send_header(
                    "Content-Disposition",
                    "attachment; filename=\"%s\"; filename*=UTF-8''%s" % (ascii_name, quote(info["name"])),
                )
                self.end_headers()
                try:
                    with open(path, "rb") as fh:
                        fh.seek(start)
                        remaining = length
                        while remaining > 0:
                            chunk = fh.read(min(CHUNK, remaining))
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                    if srv.on_download and start == 0:
                        srv.on_download(info["name"])
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

        return Handler


# ---------------------------------------------------------------------------
# İnternet üzerinden paylaşım
# ---------------------------------------------------------------------------
# Not: WeTransfer, Google Drive, Dropbox vb. hesapsız (anonim) yüklemeye izin veren
# herkese açık bir API sunmadığı için eklenmedi.

SERVICES = {
    "tmpfiles":  {"name": "tmpfiles.org", "limit": 100 * MB, "direct": True},
    "litterbox": {"name": "Litterbox",    "limit": 1 * GB,   "direct": True},
    "tempsh":    {"name": "temp.sh",      "limit": 4 * GB,   "direct": False},
    "gofile":    {"name": "gofile.io",    "limit": None,     "direct": False},
}


def services_info():
    """Arayüz için servis listesi."""
    out = [{"id": "auto", "name": None, "limit_h": None, "direct": None}]
    for sid, s in SERVICES.items():
        out.append({"id": sid, "name": s["name"],
                    "limit_h": human_size(s["limit"]) if s["limit"] else None, "direct": s["direct"]})
    return out


def pick_auto(size):
    if size <= SERVICES["tmpfiles"]["limit"]:
        return "tmpfiles"
    if size <= SERVICES["litterbox"]["limit"]:
        return "litterbox"
    return "gofile"


def prepare_upload(paths, tmpdir):
    """Tek dosya ise kendisini, birden fazla dosya/klasör ise bir zip döndürür.
    Döndürür: (yol, ad, geçici_mi) — yalnızca geçici_mi True ise sonradan silinir."""
    paths = [os.path.abspath(p) for p in paths]
    if len(paths) == 1 and os.path.isfile(paths[0]):
        return paths[0], os.path.basename(paths[0]), False
    name = "files.zip" if len(paths) > 1 else os.path.basename(paths[0].rstrip("\\/")) + ".zip"
    out = os.path.join(tmpdir, secrets.token_hex(4) + "_" + name)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as z:
        for p in paths:
            if os.path.isdir(p):
                base = os.path.dirname(p.rstrip("\\/"))
                for root, _, files in os.walk(p):
                    for f in files:
                        full = os.path.join(root, f)
                        z.write(full, os.path.relpath(full, base))
            elif os.path.isfile(p):
                z.write(p, os.path.basename(p))
    return out, name, True


def multipart_upload(host, path, file_path, file_name, field="file", fields=None, progress=None, timeout=60):
    """Dosyayı bellekte tutmadan multipart/form-data olarak yükler; yanıt metnini döndürür."""
    boundary = "----QRPaylas" + secrets.token_hex(12)
    pre = b""
    for k, v in (fields or {}).items():
        pre += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, k, v)).encode()
    safe_name = file_name.encode("ascii", "replace").decode().replace('"', "_").replace("?", "_")
    pre += (
        "--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
        "Content-Type: application/octet-stream\r\n\r\n" % (boundary, field, safe_name)
    ).encode("utf-8")
    tail = ("\r\n--%s--\r\n" % boundary).encode()
    size = os.path.getsize(file_path)

    conn = None
    try:
        conn = http.client.HTTPSConnection(host, timeout=timeout, context=ssl.create_default_context())
        conn.putrequest("POST", path)
        conn.putheader("Content-Type", "multipart/form-data; boundary=%s" % boundary)
        conn.putheader("Content-Length", str(len(pre) + size + len(tail)))
        conn.putheader("User-Agent", "QRPaylas/1.1")
        conn.endheaders()
        conn.send(pre)
        sent = 0
        with open(file_path, "rb") as fh:
            while True:
                chunk = fh.read(CHUNK)
                if not chunk:
                    break
                conn.send(chunk)
                sent += len(chunk)
                if progress:
                    progress(sent / float(size or 1))
        conn.send(tail)
        resp = conn.getresponse()
        status = resp.status
        body = resp.read().decode("utf-8", "replace")
    except (OSError, http.client.HTTPException):
        raise UserError("err.offline")
    finally:
        if conn:
            conn.close()
    if status >= 400:
        raise UserError("err.server", code=status)
    return body


def _json(body):
    try:
        return json.loads(body)
    except ValueError:
        raise UserError("err.bad_response")


def _url(body):
    url = body.strip()
    if not re.match(r"^https?://\S+$", url):
        raise UserError("err.bad_response")
    return url.replace("http://", "https://", 1)


def upload(paths, service, tmpdir, progress=None):
    """Dosyaları seçilen servise yükler. Döndürür: {"url","service","site","name","size","direct"}"""
    file_path, name, is_temp = prepare_upload(paths, tmpdir)
    try:
        size = os.path.getsize(file_path)
        if service == "auto":
            service = pick_auto(size)
        info = SERVICES[service]
        if info["limit"] and size > info["limit"]:
            raise UserError("err.too_big", site=info["name"], limit=human_size(info["limit"]), size=human_size(size))

        if service == "tmpfiles":
            res = _json(multipart_upload("tmpfiles.org", "/api/v1/upload", file_path, name, progress=progress))
            try:
                page = res["data"]["url"].replace("http://", "https://")
            except (KeyError, TypeError):
                raise UserError("err.bad_response")
            url = page.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)
        elif service == "litterbox":
            url = _url(multipart_upload(
                "litterbox.catbox.moe", "/resources/internals/api.php", file_path, name,
                field="fileToUpload", fields={"reqtype": "fileupload", "time": "24h"}, progress=progress))
        elif service == "tempsh":
            url = _url(multipart_upload("temp.sh", "/upload", file_path, name, progress=progress))
        elif service == "gofile":
            res = _json(multipart_upload("upload.gofile.io", "/uploadfile", file_path, name, progress=progress))
            if not isinstance(res, dict) or res.get("status") != "ok":
                raise UserError("err.bad_response")
            url = res["data"]["downloadPage"]
        else:
            raise ValueError(service)
    finally:
        if is_temp:  # kullanıcının kendi dosyası asla silinmez
            try:
                os.remove(file_path)
            except OSError:
                pass
    return {"url": url, "service": service, "site": info["name"], "name": name, "size": size, "direct": info["direct"]}
