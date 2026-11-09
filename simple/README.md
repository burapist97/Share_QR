# 📲 QR Paylaş — Bilgisayardan telefona QR ile dosya gönder

Mac veya Windows'tan Android veya iPhone'a dosya gönderir. Bilgisayarda bir sayfa açılır,
dosyaları sürükleyip bırakırsınız, telefonun kamerasıyla QR kodu okutup indirirsiniz.
Telefona uygulama kurmak gerekmez.

## İki mod

| | 📶 Aynı Wi-Fi ağı (varsayılan) | 🌐 İnternet üzerinden |
|---|---|---|
| Ne zaman | Telefon ve bilgisayar aynı Wi-Fi'da | Telefon başka ağda / mobil veride |
| Dosya nereye gider | Doğrudan telefona, hiçbir siteye yüklenmez | tmpfiles.org (≤100 MB) veya gofile.io (>100 MB) |
| Boyut sınırı | Yok | Pratikte yok |
| Gizli belgeler için | ✅ Uygun | ❌ Kullanmayın (linki bilen indirebilir) |

Mod, sayfanın üstündeki sekmelerden seçilir; son seçiminiz hatırlanır.

## Kurulum: Python 3
- **Mac:** Genelde hazırdır. Değilse ilk çalıştırmada macOS kurmayı önerir.
- **Windows:** https://www.python.org/downloads/ adresinden kurun. Kurulumda
  **"Add python.exe to PATH"** kutusunu işaretleyin.

## Çalıştırma
- **Mac:** `QR Paylaş (Mac).command` dosyasına çift tıklayın.
  ("Tanımlanamayan geliştirici" uyarısı çıkarsa: sağ tık → **Aç**.)
- **Windows:** `QR Paylas (Windows).bat` dosyasına çift tıklayın.
- Güvenlik duvarı "ağ erişimine izin verilsin mi?" diye sorarsa **İzin Ver** deyin
  (Windows'ta "Özel ağlar" seçili olsun). Yoksa telefon bağlanamaz.

Terminalden de çalışır:
```bash
python3 qr_paylas.py ~/Desktop/rapor.pdf ~/Pictures/tatil   # klasörler otomatik .zip yapılır
```

Program açık kaldığı sürece paylaşım sürer; pencereyi kapatınca biter, geçici dosyalar silinir.

## Python'suz kullanım
`qr_paylas.html` dosyasını tek başına çift tıklayarak da açabilirsiniz; bu durumda yalnızca
**İnternet üzerinden** modu çalışır. (`lib/` klasörü yanında durmalı; yoksa kütüphaneler internetten yüklenir.)

## Telefonda dosyalar nereye iner?
- **iPhone:** Dosyalar uygulaması → İndirilenler
- **Android:** İndirilenler / Downloads

## Klasördeki dosyalar
- `qr_paylas.py`: uygulama (sunucu + Aynı Wi-Fi modu)
- `qr_paylas.html`: İnternet modu (tek başına da açılabilir)
- `QR Paylaş (Mac).command`, `QR Paylas (Windows).bat`: çift tıklayarak başlatma
- `lib/`: QR kod ve zip kütüphaneleri (MIT lisanslı), internetsiz çalışmak için
