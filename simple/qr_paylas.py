#!/usr/bin/env python3
"""
QR Paylaş - Mac veya Windows'tan telefona (Android / iPhone) QR kod ile dosya gönderme.

İki mod:
  * Aynı Wi-Fi  : dosya bilgisayardan doğrudan telefona gider, hiçbir siteye yüklenmez.
  * İnternet    : dosya tmpfiles.org / gofile.io'ya yüklenir (qr_paylas.html), telefon
                  herhangi bir ağdan (mobil veri dahil) indirebilir.

Kullanım:
    python3 qr_paylas.py                     # tarayıcıda sürükle-bırak ekranı açılır
    python3 qr_paylas.py dosya1.pdf foto.jpg # bu dosyalar hemen paylaşılır
    python3 qr_paylas.py --port 9000 klasor/ # klasörler otomatik zip'lenir

Ek kurulum gerekmez (yalnızca Python 3 standart kütüphanesi kullanılır).
"""

import argparse
import html
import json
import os
import secrets
import shutil
import socket
import sys
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlparse

CHUNK = 1024 * 1024  # 1 MB
HERE = os.path.dirname(os.path.abspath(__file__))
INTERNET_HTML = os.path.join(HERE, "qr_paylas.html")
LIB_DIR = os.path.join(HERE, "lib")

# ---------------------------------------------------------------------------
# Paylaşılan dosyaların kaydı
# ---------------------------------------------------------------------------


class FileStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._files = {}  # id -> {"name", "path", "size"}
        self.tmpdir = tempfile.mkdtemp(prefix="qr_paylas_")

    def add(self, path, name=None):
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.isdir(path):
            base = os.path.join(self.tmpdir, secrets.token_hex(4), os.path.basename(path.rstrip("/")))
            os.makedirs(os.path.dirname(base), exist_ok=True)
            path = shutil.make_archive(base, "zip", path)
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        fid = secrets.token_urlsafe(6)
        with self._lock:
            self._files[fid] = {
                "name": name or os.path.basename(path),
                "path": path,
                "size": os.path.getsize(path),
            }
        return fid

    def remove(self, fid):
        with self._lock:
            info = self._files.pop(fid, None)
        if info and info["path"].startswith(self.tmpdir):
            try:
                os.remove(info["path"])
            except OSError:
                pass

    def get(self, fid):
        with self._lock:
            return self._files.get(fid)

    def list(self):
        with self._lock:
            return [dict(id=k, name=v["name"], size=v["size"]) for k, v in self._files.items()]

    def cleanup(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


def get_lan_ip():
    """Bilgisayarın yerel ağdaki IP adresini bulur (internete paket göndermez)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%d %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit))
        n /= 1024.0


# ---------------------------------------------------------------------------
# HTML sayfaları
# ---------------------------------------------------------------------------

BASE_CSS = """
:root{--bg:#f5f6f8;--card:#fff;--text:#1d1f23;--muted:#6b7280;--accent:#2563eb;--border:#e5e7eb}
@media (prefers-color-scheme:dark){:root{--bg:#111318;--card:#1b1e25;--text:#e8eaed;--muted:#9aa0a6;--accent:#60a5fa;--border:#2c313a}}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text)}
main{max-width:760px;margin:0 auto;padding:24px 16px}
h1{font-size:22px;margin:0 0 4px}
p.sub{color:var(--muted);margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;margin-bottom:16px}
ul{list-style:none;padding:0;margin:0}
li{display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--border)}
li:last-child{border-bottom:none}
.name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.size{color:var(--muted);font-size:13px;white-space:nowrap}
a.btn,button{background:var(--accent);color:#fff;border:none;border-radius:10px;padding:10px 16px;font-size:15px;text-decoration:none;cursor:pointer;white-space:nowrap}
button.ghost{background:transparent;color:var(--muted);padding:6px 10px;font-size:18px}
.empty{color:var(--muted);text-align:center;padding:16px 0}
"""

ADMIN_HTML = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QR Paylaş</title>
<style>%(css)s
.tabs{display:flex;gap:4px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:4px;margin-bottom:16px}
.tab{flex:1;background:transparent;color:var(--muted);border-radius:9px;padding:10px 8px;font-size:15px}
.tab small{display:block;font-size:12px;opacity:.8;margin-top:2px}
.tab.on{background:var(--accent);color:#fff}
.panel{display:none}.panel.on{display:block}
iframe{width:100%%;border:none;min-height:520px;display:block;background:transparent}
.grid{display:grid;grid-template-columns:260px 1fr;gap:16px}
@media (max-width:640px){.grid{grid-template-columns:1fr}}
#qr{display:flex;justify-content:center;padding:12px;background:#fff;border-radius:10px}
#qr img,#qr canvas{width:220px;height:220px}
.url{word-break:break-all;font-size:13px;color:var(--muted);text-align:center;margin-top:10px}
#drop{border:2px dashed var(--border);border-radius:12px;padding:28px;text-align:center;color:var(--muted);cursor:pointer;transition:.15s}
#drop.over{border-color:var(--accent);color:var(--accent)}
progress{width:100%%;height:8px;margin-top:10px;display:none}
.note{font-size:13px;color:var(--muted);line-height:1.5;margin:0 0 16px}
</style></head>
<body><main>
<h1>📲 QR Paylaş</h1>
<p class="sub">Dosyayı ekleyin, telefonun kamerasıyla QR kodu okutun. Android ve iPhone'da çalışır.</p>
<div class="tabs" role="tablist">
  <button class="tab" data-tab="lan">📶 Aynı Wi-Fi ağı<small>Dosya bilgisayardan çıkmaz · sınırsız</small></button>
  <button class="tab" data-tab="net">🌐 İnternet üzerinden<small>Telefon başka ağda / mobil veride</small></button>
</div>

<div class="panel" id="panel-net">
  %(net_panel)s
</div>

<div class="panel" id="panel-lan">
<p class="note">🔒 Telefon bu bilgisayarla aynı Wi-Fi ağına bağlı olmalı. Dosyalar hiçbir siteye
yüklenmez; program kapanınca paylaşım biter.</p>
<div class="grid">
  <div class="card">
    <div id="qr"></div>
    <div class="url" id="url">%(url)s</div>
  </div>
  <div class="card">
    <div id="drop">Dosyaları buraya sürükleyin<br>veya tıklayıp seçin
      <input type="file" id="pick" multiple hidden></div>
    <progress id="prog" max="100" value="0"></progress>
  </div>
</div>
<div class="card"><ul id="list"></ul></div>
</div>
</main>
<script src="/lib/qrcode.min.js"></script>
<script>window.QRCode||document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"><\\/script>')</script>
<script>
const PHONE_URL = %(url_json)s;
try { new QRCode(document.getElementById('qr'), {text: PHONE_URL, width: 440, height: 440, correctLevel: QRCode.CorrectLevel.M}); }
catch (e) { document.getElementById('qr').innerHTML = '<img src="/qr.svg" alt="QR">'; }

function fmt(n){const u=['B','KB','MB','GB'];let i=0;while(n>=1024&&i<3){n/=1024;i++}return (i?n.toFixed(1):n)+' '+u[i]}
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}

async function refresh(){
  const r = await fetch('/api/files'); const files = await r.json();
  const ul = document.getElementById('list');
  ul.innerHTML = files.length ? files.map(f =>
    `<li><span class="name">${esc(f.name)}</span><span class="size">${fmt(f.size)}</span>
     <button class="ghost" title="Kaldır" onclick="del('${f.id}')">✕</button></li>`).join('')
    : '<div class="empty">Henüz dosya yok</div>';
}
async function del(id){ await fetch('/api/files/'+id, {method:'DELETE'}); refresh(); }

function upload(files){
  const list=[...files]; if(!list.length) return;
  const prog=document.getElementById('prog'); prog.style.display='block';
  let i=0;
  const next=()=>{
    if(i>=list.length){ prog.style.display='none'; refresh(); return; }
    const f=list[i++]; const xhr=new XMLHttpRequest();
    xhr.open('POST','/api/upload');
    xhr.setRequestHeader('X-Filename', encodeURIComponent(f.name));
    xhr.upload.onprogress=e=>{ if(e.lengthComputable) prog.value=e.loaded/e.total*100; };
    xhr.onload=()=>{ refresh(); next(); };
    xhr.onerror=()=>{ alert('Yükleme başarısız: '+f.name); next(); };
    xhr.send(f);
  };
  next();
}
const drop=document.getElementById('drop'), pick=document.getElementById('pick');
drop.onclick=()=>pick.click();
pick.onchange=()=>{ upload(pick.files); pick.value=''; };
['dragenter','dragover'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('over')}));
['dragleave','drop'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('over')}));
drop.addEventListener('drop',e=>upload(e.dataTransfer.files));
refresh(); setInterval(refresh, 3000);

// --- Sekmeler (son seçilen hatırlanır) ---
function showTab(name){
  document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('on', b.dataset.tab===name));
  document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('on', p.id==='panel-'+name));
  try { localStorage.setItem('qrPaylasTab', name); } catch(e) {}
}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>showTab(b.dataset.tab));
let saved='lan'; try { saved = localStorage.getItem('qrPaylasTab') || 'lan'; } catch(e) {}
showTab(saved);
// İnternet sekmesindeki sayfa kendi yüksekliğini bildirir
window.addEventListener('message', e=>{
  const h = e.data && e.data.qrPaylasHeight; const fr = document.getElementById('netFrame');
  if (h && fr) fr.style.height = (h + 4) + 'px';
});
</script></body></html>
"""

PHONE_HTML = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dosyalar</title>
<style>%(css)s</style></head>
<body><main>
<h1>📥 Dosyalar</h1>
<p class="sub">İndirmek istediğiniz dosyaya dokunun.<br>
iPhone: indirilen dosyalar <b>Dosyalar → İndirilenler</b> klasörüne gider.</p>
<div class="card"><ul>%(items)s</ul></div>
<p class="sub" style="text-align:center"><a href="" style="color:var(--accent)">↻ Yenile</a></p>
</main></body></html>
"""


# ---------------------------------------------------------------------------
# HTTP sunucusu
# ---------------------------------------------------------------------------


def make_handler(store, token, phone_url):
    class Handler(BaseHTTPRequestHandler):
        server_version = "QRPaylas/1.0"

        def log_message(self, fmt, *args):  # sessiz çalış
            pass

        # --- yardımcılar ---
        def is_local(self):
            return self.client_address[0] in ("127.0.0.1", "::1", "::ffff:127.0.0.1")

        def send_body(self, body, ctype="text/html; charset=utf-8", code=200):
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def deny(self):
            self.send_body("Erişim yok", "text/plain; charset=utf-8", 403)

        # --- GET ---
        def do_GET(self):
            path = urlparse(self.path).path

            if path == "/":
                if not self.is_local():
                    return self.deny()
                if os.path.isfile(INTERNET_HTML):
                    net_panel = ('<iframe id="netFrame" src="/internet" title="İnternet üzerinden paylaş" '
                                 'allow="clipboard-write"></iframe>')
                else:
                    net_panel = ('<div class="card empty">İnternet modu için <b>qr_paylas.html</b> dosyası '
                                 'bu programla aynı klasörde olmalı.</div>')
                page = ADMIN_HTML % {
                    "css": BASE_CSS,
                    "net_panel": net_panel,
                    "url": html.escape(phone_url),
                    "url_json": json.dumps(phone_url),
                }
                return self.send_body(page)

            if path == "/internet" and self.is_local() and os.path.isfile(INTERNET_HTML):
                with open(INTERNET_HTML, "rb") as fh:
                    return self.send_body(fh.read())

            if path.startswith("/lib/") and self.is_local():
                lib = os.path.join(LIB_DIR, os.path.basename(path))
                if lib.endswith(".js") and os.path.isfile(lib):
                    with open(lib, "rb") as fh:
                        return self.send_body(fh.read(), "text/javascript; charset=utf-8")

            if path == "/qr.svg" and self.is_local():
                svg = qr_svg(phone_url)
                if svg is None:
                    return self.send_body("", "text/plain", 404)
                return self.send_body(svg, "image/svg+xml")

            if path == "/api/files":
                if not self.is_local():
                    return self.deny()
                return self.send_body(json.dumps(store.list()), "application/json")

            parts = path.strip("/").split("/")
            if not parts or parts[0] != token:
                return self.deny()

            if len(parts) == 1:
                files = store.list()
                if files:
                    items = "".join(
                        '<li><span class="name">%s</span><span class="size">%s</span>'
                        '<a class="btn" href="/%s/dl/%s">İndir</a></li>'
                        % (html.escape(f["name"]), human_size(f["size"]), token, f["id"])
                        for f in files
                    )
                else:
                    items = '<div class="empty">Henüz paylaşılan dosya yok</div>'
                return self.send_body(PHONE_HTML % {"css": BASE_CSS, "items": items})

            if len(parts) == 3 and parts[1] == "dl":
                return self.send_file(parts[2])

            self.send_body("Bulunamadı", "text/plain; charset=utf-8", 404)

        def send_file(self, fid):
            info = store.get(fid)
            if not info or not os.path.isfile(info["path"]):
                return self.send_body("Dosya bulunamadı", "text/plain; charset=utf-8", 404)
            size = os.path.getsize(info["path"])
            start, end = 0, size - 1
            rng = self.headers.get("Range")
            partial = False
            if rng and rng.startswith("bytes="):
                try:
                    a, b = rng[6:].split(",")[0].split("-")
                    if a:
                        start = int(a)
                        end = int(b) if b else size - 1
                    else:
                        start = max(0, size - int(b))
                    end = min(end, size - 1)
                    partial = start <= end
                except ValueError:
                    partial = False
                if not partial:
                    start, end = 0, size - 1
            length = end - start + 1 if size else 0

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
                with open(info["path"], "rb") as fh:
                    fh.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk = fh.read(min(CHUNK, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
                if not partial or start == 0:
                    print("  ⬇  %s  → %s" % (info["name"], self.client_address[0]))
            except (BrokenPipeError, ConnectionResetError):
                pass

        # --- POST (sadece bu bilgisayardan yükleme) ---
        def do_POST(self):
            if urlparse(self.path).path != "/api/upload" or not self.is_local():
                return self.deny()
            name = os.path.basename(unquote(self.headers.get("X-Filename", "dosya"))) or "dosya"
            length = int(self.headers.get("Content-Length", 0))
            folder = os.path.join(store.tmpdir, secrets.token_hex(4))
            os.makedirs(folder)
            dest = os.path.join(folder, name)
            with open(dest, "wb") as fh:
                remaining = length
                while remaining > 0:
                    chunk = self.rfile.read(min(CHUNK, remaining))
                    if not chunk:
                        break
                    fh.write(chunk)
                    remaining -= len(chunk)
            fid = store.add(dest, name)
            print("  +  %s (%s)" % (name, human_size(length)))
            self.send_body(json.dumps({"id": fid}), "application/json")

        def do_DELETE(self):
            parts = urlparse(self.path).path.strip("/").split("/")
            if not self.is_local() or len(parts) != 3 or parts[:2] != ["api", "files"]:
                return self.deny()
            store.remove(parts[2])
            self.send_body("{}", "application/json")

    return Handler


# ---------------------------------------------------------------------------
# İsteğe bağlı: 'qrcode' paketi kuruluysa terminalde / SVG olarak QR üret
# (internet olmadığında da QR görünsün diye). Kurulum: pip3 install qrcode
# ---------------------------------------------------------------------------


def _qr_matrix(text):
    try:
        import qrcode  # type: ignore
    except ImportError:
        return None
    qr = qrcode.QRCode(border=2)
    qr.add_data(text)
    qr.make(fit=True)
    return qr.get_matrix()


def qr_svg(text):
    m = _qr_matrix(text)
    if m is None:
        return None
    n = len(m)
    rects = "".join(
        '<rect x="%d" y="%d" width="1" height="1"/>' % (x, y)
        for y, row in enumerate(m) for x, v in enumerate(row) if v
    )
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" shape-rendering="crispEdges">'
            '<rect width="100%%" height="100%%" fill="#fff"/><g fill="#000">%s</g></svg>' % (n, n, rects))


def print_terminal_qr(text):
    m = _qr_matrix(text)
    if m is None:
        return False
    # Yarım blok karakterleriyle iki satırı tek satıra sığdır
    for y in range(0, len(m), 2):
        line = ""
        for x in range(len(m[0])):
            top = m[y][x]
            bot = m[y + 1][x] if y + 1 < len(m) else False
            line += {(False, False): "█", (True, False): "▄", (False, True): "▀", (True, True): " "}[(top, bot)]
        print("  " + line)
    return True


# ---------------------------------------------------------------------------


def find_free_port(preferred):
    for port in [preferred] + list(range(preferred + 1, preferred + 50)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    raise SystemExit("Boş port bulunamadı.")


def main():
    # Windows konsolunda Türkçe karakter / emoji yüzünden çökmesin
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="Bilgisayardan telefona QR kod ile dosya gönder.")
    ap.add_argument("files", nargs="*", help="Paylaşılacak dosya veya klasörler")
    ap.add_argument("--port", type=int, default=8765, help="Sunucu portu (varsayılan 8765)")
    ap.add_argument("--no-browser", action="store_true", help="Tarayıcıyı otomatik açma")
    args = ap.parse_args()

    store = FileStore()
    for f in args.files:
        try:
            store.add(f)
        except FileNotFoundError:
            print("Bulunamadı, atlanıyor: %s" % f, file=sys.stderr)

    ip = get_lan_ip()
    port = find_free_port(args.port)
    token = secrets.token_urlsafe(8)
    phone_url = "http://%s:%d/%s" % (ip, port, token)
    admin_url = "http://127.0.0.1:%d/" % port

    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(store, token, phone_url))
    server.daemon_threads = True

    print("\n  📲 QR Paylaş çalışıyor\n")
    print("  Telefon adresi : %s" % phone_url)
    print("  Kontrol sayfası: %s\n" % admin_url)
    if ip.startswith("127."):
        print("  ⚠  Wi-Fi bağlantısı bulunamadı! Telefon bu bilgisayara erişemeyebilir.\n")
    if print_terminal_qr(phone_url):
        print()
    print("  Durdurmak için Ctrl+C\n")

    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(admin_url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Kapatılıyor…")
    finally:
        server.server_close()
        store.cleanup()


if __name__ == "__main__":
    main()
