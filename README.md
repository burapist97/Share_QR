# Scanload

Send files from your PC to your iPhone or Android phone with a QR code. No cables, no app on the phone.

[Türkçe](#türkçe)

- **Same Wi-Fi:** Files go straight from your PC to your phone over the local network. Nothing is uploaded, no size limit. You can choose the network adapter.
- **Internet:** Uploads to a temporary service you choose — tmpfiles.org (100 MB, 60 min), Litterbox (1 GB, 24 h), temp.sh (4 GB, 3 days), gofile.io (no limit) — or **Automatic**.
- **Link to QR:** Turns any link or text into a QR code; save it as a PNG.
- Lives in the system tray, opens a small window on click, can open at Windows startup.
- English (default), Turkish, Spanish. Light and dark appearance.

> WeTransfer, Google Drive, and Dropbox aren’t offered because they don’t allow apps to upload without an account.

## Repository layout
```
app/                         Windows app (Python + pywebview)
  scanload.py                tray icon, window, JavaScript bridge (entry point)
  core.py                    local share server, networks, uploads, QR codes
  winplat.py                 open at startup, MSIX detection, single instance
  i18n.json, i18n.py         English, Turkish, Spanish strings
  ui/index.html              the interface
  assets/                    app.ico, tray.png
packaging/
  AppxManifest.xml           MSIX manifest (startup task, firewall rule, languages)
  Assets/                    Start menu and Store tile images
store/
  listing/                   Store texts, one file per language (en-US, tr-TR, es-ES)
  art/                       poster, box art, super hero art, tile icons
  PRIVACY.md                 privacy policy (EN/TR/ES)
  store_logo_300.png         Store logo
  screenshots/{en,tr,es}/    5 Store screenshots per language, 1920×1080
docs/
  MICROSOFT_STORE_REHBERI.md step-by-step Store guide (Turkish)
tools/
  make_icons.py              regenerates every icon
  screenshots/               regenerates the Store screenshots
build.ps1                    exe → self-test → MSIX → portable zip
requirements*.txt            Python packages
.github/workflows/windows.yml  builds on every push; “Run workflow” makes the Store package
simple/                      earlier lightweight versions (Python script / single HTML file)
```

## Build
Every push runs **Actions → Windows build** on a Windows runner and publishes a test build as the `Scanload-test` artifact (`.msix`, portable `.zip`, test certificate).
To build the Store package, use **Run workflow** and enter the three Partner Center values; the result is the `Scanload-STORE` artifact.

Locally (Windows, Python 3.12, Windows SDK):
```powershell
.\build.ps1 -Sign
```
To install the test-signed MSIX, trust the certificate once (admin PowerShell), then double-click the `.msix`:
```powershell
Import-Certificate -FilePath build\test.cer -CertStoreLocation Cert:\LocalMachine\TrustedPeople
```

Run from source:
```powershell
pip install -r requirements.txt
python app\scanload.py
```

## Publish to the Microsoft Store
Step-by-step guide in Turkish: [docs/MICROSOFT_STORE_REHBERI.md](docs/MICROSOFT_STORE_REHBERI.md)

1. Create a developer account at https://partner.microsoft.com (check the current fee there).
2. **Apps and games → New product → MSIX or PWA app**, reserve the name.
3. From **Product management → Product identity**, copy the three values and build:
   ```powershell
   .\build.ps1 -Version 1.1.0.0 -IdentityName "<Package/Identity/Name>" -Publisher "<Package/Identity/Publisher>" -PublisherDisplayName "<Package/Properties/PublisherDisplayName>"
   ```
   Or without a Windows PC: **Actions → Windows build → Run workflow** and enter the same three values.
4. **Packages:** upload `build\Scanload_1.1.0_x64.msix`. The Store signs it; you don’t need a certificate.
5. **Store listings:** copy from `store/listing/` (one file per language) and upload `store/screenshots/` and `store/art/`.
6. **Privacy policy:** publish `store/PRIVACY.md` and paste its URL. Replace `{{CONTACT_EMAIL}}` first.
7. **Submission options → Notes for certification:**
   > The app uses runFullTrust because it runs a small HTTP server so a phone on the same network can download files (TCP 8765–8814 only, only while sharing). It lives in the system tray; click the tray icon to open the window.
8. Submit. Certification usually takes a few days.

## Known limitations
- The window opens in the bottom-right corner; if the taskbar is on another edge, the position may not be ideal.
- Internet mode depends on third-party services; if a service changes its API, the app needs an update.

---

## Türkçe

Bilgisayardan iPhone veya Android telefona QR kod ile dosya gönderin. Kablo yok, telefona uygulama kurmak yok.

- **Aynı Wi-Fi:** Dosyalar yerel ağ üzerinden doğrudan telefona gider; hiçbir yere yüklenmez, boyut sınırı yoktur. Ağ bağdaştırıcısı seçilebilir.
- **İnternet:** Seçtiğiniz geçici servise yükler: tmpfiles.org (100 MB, 60 dk), Litterbox (1 GB, 24 saat), temp.sh (4 GB, 3 gün), gofile.io (sınırsız) veya **Otomatik**.
- **Linkten QR:** Her bağlantıyı veya metni QR koda çevirir; PNG olarak kaydedilebilir.
- Sistem tepsisinde durur, tıklayınca küçük bir pencere açar, Windows ile başlayabilir.
- İngilizce (varsayılan), Türkçe, İspanyolca. Açık ve koyu görünüm.

**Derleme:** Her push'ta GitHub Actions Windows'ta bir test paketi derler (**Scanload-test**). Store paketi için **Actions → Windows build → Run workflow** ile Partner Center değerlerini girin (**Scanload-STORE**).

**Store'a gönderme:** Adım adım Türkçe rehber: [docs/MICROSOFT_STORE_REHBERI.md](docs/MICROSOFT_STORE_REHBERI.md). Mağaza metinleri `store/listing/`, gizlilik politikası `store/PRIVACY.md` içinde (üç dilde).
