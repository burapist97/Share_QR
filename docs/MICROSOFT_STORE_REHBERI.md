# Scanload'u Microsoft Store'a yükleme rehberi

Hiç bilmeyen biri için, baştan sona. Toplam süre: hesap onayı dahil 1–2 saatlik iş, ardından
Microsoft'un incelemesi için birkaç gün bekleme.

> Partner Center'ın menü adları zaman zaman değişir. Aşağıdaki adımlarda gördüğünüz ad
> birebir aynı değilse en yakın seçeneği seçin; mantık aynıdır.

---

## Aşama 0 — Gerekenler

- Bir **Microsoft hesabı** (Outlook, Hotmail veya Xbox hesabı olur; yoksa account.microsoft.com'dan ücretsiz açılır)
- **Kimlik kartı veya pasaport** (kimlik doğrulaması için)
- Telefon kamerası (kimlik doğrulamada selfie çekilir)
- Destek için kullanacağınız bir **e-posta adresi** (mağazada görünür)
- Windows bilgisayar **gerekmez**: paket GitHub'da üretilir, mağaza görselleri de repoda hazır.

---

## Aşama 1 — Geliştirici hesabı açın (ücretsiz)

1. **https://storedeveloper.microsoft.com** adresine gidin.
2. **Individual developer** (Bireysel geliştirici, ücretsiz) seçeneğini seçin.
   *Şirket hesabı ücretlidir ve şirket belgeleri ister; bireysel hesap yeterli.*
3. Microsoft hesabınızla giriş yapın.
4. Adınızı, ülkenizi ve iletişim bilgilerinizi girin. **Yayıncı görünen adı** (Publisher display name)
   mağazada uygulamanın altında görünecek addır; örneğin adınız soyadınız.
5. **Kimlik doğrulaması:** Kimliğinizin fotoğrafını ve bir selfie istenir. Ekrandaki adımları izleyin.
6. Onaylanınca otomatik olarak **Partner Center**'a (partner.microsoft.com) yönlendirilirsiniz.
   Kredi kartı istenmez.

---

## Aşama 2 — Uygulama adını ayırın

1. Partner Center'da **Apps and games** (Uygulamalar ve oyunlar) bölümüne girin.
2. **+ New product** → **MSIX or PWA app** seçin.
3. Ad olarak **Scanload** yazın → **Check availability** → **Reserve product name**.
   - Ad alınmışsa şunları deneyin: *Scanfetch*, *Scanload – Files to Phone*. Seçtiğiniz adı bana
     yazın, uygulamanın içindeki adı da ona göre güncellerim.

---

## Aşama 3 — Üç kimlik değerini alın

1. Uygulamanın sayfasında sol menüden **Product management → Product identity**
   (Ürün yönetimi → Ürün kimliği) açın.
2. Şu üç satırı bir yere kopyalayın:

| Partner Center'daki ad | Örnek |
|---|---|
| **Package/Identity/Name** | `12345AdSoyad.Scanload` |
| **Package/Identity/Publisher** | `CN=1A2B3C4D-1234-5678-9ABC-0123456789AB` |
| **Package/Properties/PublisherDisplayName** | `Ad Soyad` |

Bu değerler gizli değildir ama **birebir** kopyalanmalıdır (boşluk ve büyük/küçük harf dahil).

---

## Aşama 4 — Store paketini üretin (GitHub'da, tıklayarak)

1. **https://github.com/burapist97/Share_QR/actions** adresine gidin.
2. Soldan **Windows build** → sağda **Run workflow** düğmesine tıklayın.
3. Açılan formu doldurun:
   - **Version:** ilk gönderim için `1.1.0.0` (sonraki her güncellemede artırın: `1.1.1.0`, `1.2.0.0`…; son hane hep `0`)
   - **identity_name / publisher / publisher_display_name:** Aşama 3'teki üç değer
4. Yeşil **Run workflow** düğmesine basın. Yaklaşık 2–3 dakika sürer.
5. Bitince (yeşil ✓) çalışmaya tıklayın, sayfanın altındaki **Artifacts** bölümünden
   **Scanload-STORE** dosyasını indirin.
6. İnen zip'i açın. İçindeki **`Scanload_1.1.0_x64.msix`** Store'a yükleyeceğiniz dosyadır.

> Kırmızı ✗ çıkarsa çalışmaya tıklayıp hata satırının ekran görüntüsünü bana gönderin.

---

## Aşama 5 — Gönderim öncesi hazırlık

### 5a. Gizlilik politikası
Uygulama internete dosya yükleyebildiği için Store bir **gizlilik politikası bağlantısı** ister.

1. Repoda `store/PRIVACY.md` dosyasını açın, kalem simgesine (Edit) tıklayın.
2. `{{CONTACT_EMAIL}}` yazan üç yeri destek e-postanızla değiştirin → **Commit changes**.
3. Bağlantı: repoda GitHub Pages açık olduğu için büyük ihtimalle şu adreste yayınlanır:
   **https://burapist97.github.io/Share_QR/store/PRIVACY.html**
   Tarayıcıda açıp sayfanın göründüğünü kontrol edin. Açılmazsa bana yazın.

### 5b. Ekran görüntüleri — hazır
Her dil için 5 adet, 1920 × 1080 PNG, repoda hazır:

| Dil | Klasör |
|---|---|
| English | `store/screenshots/en/` |
| Türkçe | `store/screenshots/tr/` |
| Español | `store/screenshots/es/` |

Her klasörde aynı sırayla: `01-send-files`, `02-scan-qr`, `03-internet`, `04-link-to-qr`, `05-tray-dark`.
İndirmek için GitHub'da dosyaya tıklayın → sağ üstteki **Download raw file** (indirme) simgesi.
Ya da repoyu topluca indirin: repo ana sayfası → yeşil **Code** → **Download ZIP**.

> Uygulama değiştiğinde görseller tek komutla yeniden üretilir:
> `node tools/screenshots/make_screenshots.cjs`

---

## Aşama 6 — Gönderimi doldurun

Uygulama sayfasında **Start your submission** (Gönderimi başlat) deyin. Karşınıza birkaç bölüm çıkar;
her birini doldurup **Save** deyin.

### 1) Pricing and availability (Fiyat ve erişilebilirlik)
- **Markets:** tüm pazarlar (varsayılan)
- **Pricing:** **Free** (Ücretsiz)
- **Visibility:** Public (Herkese açık)

### 2) Properties (Özellikler)
- **Category:** *Productivity* (Verimlilik)
- **Privacy policy URL:** Aşama 5a'daki bağlantı
- **Website:** `https://github.com/burapist97/Share_QR` (isteğe bağlı)
- **Support contact info:** destek e-postanız
- Diğer kutular (sistem gereksinimleri vb.) boş kalabilir.

### 3) Age ratings (Yaş derecelendirmesi)
IARC anketi doldurulur, sonunda otomatik bir yaş sınırı verilir.
- Kategori sorusunda: **All other app types** (Diğer tüm uygulama türleri)
- Şiddet, kumar, cinsellik, kötü dil vb. soruların hepsi: **No**
- **Kullanıcıların içerik paylaşması** veya **internet bağlantısı/etkileşim** hakkında bir soru
  çıkarsa **dürüst** cevap verin: uygulama, kullanıcının kendi dosyasını internete yükleyip
  link oluşturabiliyor. Bu soruya “Yes” demek yayını engellemez, yalnızca mağazada küçük
  bir bilgi notu olarak görünür. Yanlış cevap ise sonradan sorun çıkarır.

### 4) Packages (Paketler)
- Aşama 4'teki **`.msix`** dosyasını sürükleyip bırakın.
- Yükleme doğrulanınca **Windows 10/11 Desktop** işaretli olmalı.
- Burada “Identity/Publisher eşleşmiyor” gibi bir hata çıkarsa Aşama 3 değerlerinde kopyalama
  hatası vardır; Aşama 4'ü düzeltilmiş değerlerle tekrarlayın.

### 5) Store listings (Mağaza sayfası)
Paket üç dili içerdiği için **English (United States)**, **Turkish** ve **Spanish** listeleri
görünür (görünmezse **Manage additional languages** ile ekleyin). Her dil için:
- **Description, Short description, Features, Keywords:** `store/STORE_LISTING.md` dosyasından kopyalayın
- **Screenshots:** o dilin klasöründeki 5 görsel (`store/screenshots/en/` → English, `tr/` → Turkish, `es/` → Spanish), 01'den 05'e sırayla
- **Store logo** (isteğe bağlı): `store/store_logo_300.png`

### 6) Submission options (Gönderim seçenekleri)
- **Publishing hold options:** *Publish as soon as possible* (onaylanınca hemen yayınla)
- **Notes for certification** kutusuna şunu yapıştırın:

  > The app uses runFullTrust because it runs a small local HTTP server so a phone on the same
  > network can download files (TCP 8765–8814 only, only while sharing). It lives in the system
  > tray; click the tray icon to open the window. Test: add any file, choose "Same Wi-Fi",
  > click "Create QR Code" and open the shown address from another device on the same network.

- **Restricted capabilities** sorusu çıkarsa (*runFullTrust* için gerekçe) aynı metnin ilk
  cümlesini yazın.

---

## Aşama 7 — Gönderin ve bekleyin

1. Tüm bölümler “Complete” (Tamamlandı) olunca **Submit to the Store** deyin.
2. Durum sırasıyla *Pre-processing → Certification → Release* olarak ilerler. İnceleme genelde
   **1–3 iş günü** sürer, bazen daha uzun.
3. Sonuç e-postayla gelir.
   - **Onaylanırsa:** birkaç saat içinde mağazada görünür. Partner Center'daki uygulama sayfasında
     mağaza bağlantınız yazar.
   - **Reddedilirse:** rapor gelir (hangi kuralın neden ihlal edildiği yazar). Raporu bana gönderin,
     düzeltip birlikte yeniden gönderelim.

> Gönderim, bütün alanlar dolu görünmesine rağmen “Incomplete” (eksik) kalırsa Partner Center'daki
> **Help + support** üzerinden destek talebi açın; bu bilinen bir Partner Center sorunu.

---

## Sonraki güncellemeler

1. Kodda değişiklik yapılır.
2. Aşama 4'ü **daha yüksek bir sürüm numarasıyla** tekrarlayın (`1.1.1.0` gibi).
3. Partner Center'da uygulamaya girip **Update** (yeni gönderim) → **Packages** bölümünde eski paketi
   kaldırıp yenisini yükleyin → Submit. Diğer bölümler önceki gönderimden kopyalanır.

---

## Sık karşılaşılanlar

| Sorun | Ne yapmalı |
|---|---|
| Kimlik doğrulama reddedildi | Işığı iyi bir yerde, kimliğin tamamı görünür şekilde tekrar deneyin |
| Ad alınmış | Farklı ad ayırın, bana bildirin |
| Paket yüklenirken kimlik/yayıncı hatası | Aşama 3 değerlerini kontrol edip Aşama 4'ü tekrarlayın |
| “Version must be higher” | Sürüm numarasını artırıp Aşama 4'ü tekrarlayın |
| Sertifikasyonda red | Raporu bana gönderin |
