"""
Ekran görüntüleri için örnek veri üretir (JSON olarak stdout'a yazar).
make_screenshots.mjs tarafından çağrılır; elle çalıştırmanız gerekmez.
"""

import json
import os
import sys

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "app")
sys.path.insert(0, APP)

import core  # noqa: E402
import i18n  # noqa: E402

MB = 1024 * 1024

# Her dilde gerçekçi örnek dosya ve ağ adları
SAMPLES = {
    "en": {"files": [("Holiday video.mp4", 734 * MB, False), ("Photos", 52 * MB, True), ("Report.pdf", 1.2 * MB, False)],
           "wifi": "Home", "link": "https://example.com/menu"},
    "tr": {"files": [("Tatil videosu.mp4", 734 * MB, False), ("Fotoğraflar", 52 * MB, True), ("Rapor.pdf", 1.2 * MB, False)],
           "wifi": "Ev", "link": "https://example.com/menu"},
    "es": {"files": [("Vídeo vacaciones.mp4", 734 * MB, False), ("Fotos", 52 * MB, True), ("Informe.pdf", 1.2 * MB, False)],
           "wifi": "Casa", "link": "https://example.com/menu"},
}

WIFI_URL = "http://192.168.1.23:8765/p_fvjc6v6Tk"
NET_URL = "https://litter.catbox.moe/k3x9qa.mp4"


def main():
    out = {
        "strings": i18n.STRINGS,
        "services": core.services_info(),
        "qr": {"wifi": core.qr_svg(WIFI_URL), "net": core.qr_svg(NET_URL)},
        "urls": {"wifi": WIFI_URL, "net": NET_URL},
        "langs": {},
    }
    for lang, s in SAMPLES.items():
        files = [{"path": "C:/Users/me/" + n, "name": n, "size": int(sz), "dir": d} for n, sz, d in s["files"]]
        # Telefonda açılan sayfa: klasörler zip olarak görünür
        phone_files = {
            "f%d" % i: {"name": f["name"] + (".zip" if f["dir"] else ""), "size": f["size"]}
            for i, f in enumerate(files)
        }
        out["langs"][lang] = {
            "files": files,
            "wifi": "Wi-Fi · " + s["wifi"],
            "link": s["link"],
            "link_qr": core.qr_svg(s["link"]),
            "phone_html": core.phone_page(lang, "p_fvjc6v6Tk", phone_files),
        }
    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
