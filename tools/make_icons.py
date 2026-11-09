"""
Uygulama ve Store ikonlarını üretir (Pillow).
Çıktı: app/assets/{app.ico, tray.png}  ve  packaging/Assets/*.png (MSIX)

    python tools/make_icons.py
"""

import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
APP_ASSETS = os.path.join(ROOT, "app", "assets")
PKG_ASSETS = os.path.join(ROOT, "packaging", "Assets")

TOP, BOTTOM = (64, 156, 255), (0, 98, 230)  # mavi degrade


def glyph(d, x0, y0, s, color):
    """QR köşe işaretleri + aşağı ok: s boyutlu kare alana çizer."""
    u = s / 10.0

    def finder(cx, cy):
        d.rounded_rectangle([cx, cy, cx + 3 * u, cy + 3 * u], radius=0.8 * u, outline=color, width=max(1, round(0.62 * u)))
        d.rounded_rectangle([cx + 1.05 * u, cy + 1.05 * u, cx + 1.95 * u, cy + 1.95 * u], radius=0.25 * u, fill=color)

    finder(x0 + 0.5 * u, y0 + 0.5 * u)
    finder(x0 + 6.5 * u, y0 + 0.5 * u)
    finder(x0 + 0.5 * u, y0 + 6.5 * u)
    # sağ alt: indirme oku
    w = max(1, round(0.7 * u))
    cx = x0 + 8 * u
    d.line([cx, y0 + 5.6 * u, cx, y0 + 9.0 * u], fill=color, width=w)
    d.line([cx - 1.3 * u, y0 + 7.8 * u, cx, y0 + 9.1 * u, cx + 1.3 * u, y0 + 7.8 * u], fill=color, width=w, joint="curve")


def gradient(w, h):
    g = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        g.putpixel((0, y), tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3)))
    return g.resize((w, h))


def app_icon(size, plate=True, pad=0.0):
    """Yuvarlatılmış kare (squircle benzeri) zemin + beyaz sembol."""
    ss = 4  # kenar yumuşatma için büyük çiz, sonra küçült
    S = size * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    inset = int(S * pad)
    box = S - 2 * inset
    if plate:
        mask = Image.new("L", (S, S), 0)
        ImageDraw.Draw(mask).rounded_rectangle([inset, inset, S - inset - 1, S - inset - 1], radius=int(box * 0.225), fill=255)
        img.paste(gradient(S, S), (0, 0), mask)
        color = (255, 255, 255, 255)
        g = box * 0.56
    else:
        color = (255, 255, 255, 255)
        g = box * 0.86
    d = ImageDraw.Draw(img)
    glyph(d, (S - g) / 2, (S - g) / 2, g, color)
    return img.resize((size, size), Image.LANCZOS)


def on_canvas(w, h, icon_size):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ic = app_icon(icon_size)
    img.paste(ic, ((w - icon_size) // 2, (h - icon_size) // 2), ic)
    return img


def main():
    os.makedirs(APP_ASSETS, exist_ok=True)
    os.makedirs(PKG_ASSETS, exist_ok=True)

    big = app_icon(256)
    big.save(os.path.join(APP_ASSETS, "app.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    app_icon(64).save(os.path.join(APP_ASSETS, "tray.png"))

    # MSIX görselleri (temel ölçek + 200%)
    for scale, suffix in ((1, ".scale-100"), (2, ".scale-200")):
        app_icon(44 * scale).save(os.path.join(PKG_ASSETS, "Square44x44Logo%s.png" % suffix))
        on_canvas(150 * scale, 150 * scale, 96 * scale).save(os.path.join(PKG_ASSETS, "Square150x150Logo%s.png" % suffix))
        on_canvas(310 * scale, 150 * scale, 96 * scale).save(os.path.join(PKG_ASSETS, "Wide310x150Logo%s.png" % suffix))
        app_icon(50 * scale).save(os.path.join(PKG_ASSETS, "StoreLogo%s.png" % suffix))
    # Görev çubuğu / Başlat menüsü için zeminsiz hedef boyutlar
    for n in (16, 24, 32, 48, 256):
        app_icon(n).save(os.path.join(PKG_ASSETS, "Square44x44Logo.targetsize-%d.png" % n))
        app_icon(n).save(os.path.join(PKG_ASSETS, "Square44x44Logo.targetsize-%d_altform-unplated.png" % n))
    # Partner Center'a yüklenecek mağaza ikonu
    app_icon(300).save(os.path.join(ROOT, "store", "store_logo_300.png"))
    print("ikonlar üretildi")


if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "store"), exist_ok=True)
    main()
