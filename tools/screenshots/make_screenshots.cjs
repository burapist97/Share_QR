/*
 * Microsoft Store ekran görüntülerini üretir: 3 dil × 5 görsel, 1920×1080 PNG.
 * Uygulamanın gerçek arayüzü (app/ui/index.html) örnek verilerle açılır ve fotoğraflanır.
 *
 *   node tools/screenshots/make_screenshots.cjs
 *
 * Gerekenler: Node.js + Playwright (Chromium), Python 3 + segno.
 * Çıktı: store/screenshots/<dil>/0N-*.png
 */
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const UI = 'file://' + path.join(ROOT, 'app', 'ui', 'index.html');
const OUT = path.join(ROOT, 'store', 'screenshots');
const D = JSON.parse(execFileSync('python3', [path.join(__dirname, 'mock_data.py')], { maxBuffer: 64 << 20 }).toString());

const CAPTIONS = {
  en: [
    ['Send files from your PC to your phone', 'Drop files, scan the code, and they’re on your phone. Works with iPhone and Android. Nothing to install on the phone.'],
    ['Scan it with your camera', 'Your phone opens a simple download page. On the same Wi-Fi, files go straight to your phone and never leave your network.'],
    ['On another network? Use the internet', 'Choose tmpfiles.org, Litterbox, temp.sh, or gofile.io, or let Share QR choose by file size.'],
    ['Turn any link into a QR code', 'Websites, addresses, notes. The code updates as you type, and you can save it as a PNG.'],
    ['Always one click away', 'Share QR waits in the system tray and can open at startup. Light and dark appearance, in English, Turkish, and Spanish.'],
  ],
  tr: [
    ['Bilgisayardan telefona dosya gönderin', 'Dosyaları bırakın, kodu okutun, dosyalar telefonunuzda. iPhone ve Android ile çalışır; telefona hiçbir şey kurmanız gerekmez.'],
    ['Kamerayla okutun, indirin', 'Telefonunuzda sade bir indirme sayfası açılır. Aynı Wi-Fi’da dosyalar doğrudan telefona gider, ağınızdan dışarı çıkmaz.'],
    ['Başka ağda mısınız? İnternetten gönderin', 'tmpfiles.org, Litterbox, temp.sh veya gofile.io’yu seçin ya da Share QR dosya boyutuna göre seçsin.'],
    ['Her bağlantıyı QR koda çevirin', 'Web siteleri, adresler, notlar. Kod siz yazdıkça güncellenir; PNG olarak kaydedebilirsiniz.'],
    ['Her an bir tık uzağınızda', 'Sistem tepsisinde bekler, isterseniz Windows ile açılır. Açık ve koyu tema; İngilizce, Türkçe ve İspanyolca.'],
  ],
  es: [
    ['Envía archivos del ordenador al móvil', 'Suelta los archivos, escanea el código y ya están en tu móvil. Funciona con iPhone y Android, sin instalar nada en el móvil.'],
    ['Escanéalo con la cámara', 'El móvil abre una página de descarga sencilla. En la misma Wi-Fi, los archivos van directos al móvil y no salen de tu red.'],
    ['¿Otra red? Envía por internet', 'Elige tmpfiles.org, Litterbox, temp.sh o gofile.io, o deja que Share QR elija según el tamaño del archivo.'],
    ['Convierte cualquier enlace en un código QR', 'Webs, direcciones, notas. El código se actualiza mientras escribes y puedes guardarlo como PNG.'],
    ['Siempre a un clic', 'Espera en la bandeja del sistema y puede abrirse al iniciar Windows. Tema claro y oscuro, en inglés, turco y español.'],
  ],
};
const NAMES = ['01-send-files', '02-scan-qr', '03-internet', '04-link-to-qr', '05-tray-dark'];

// Uygulamanın Python tarafının yerine geçen sahte API (yalnızca görüntü almak için)
function mockApi(lang) {
  const L = D.langs[lang];
  return `window.pywebview={api:{
    init:async()=>({version:'1.1.0',lang:${JSON.stringify(lang)},strings:${JSON.stringify(D.strings)},services:${JSON.stringify(D.services)},
      settings:{},networks:[{ip:'192.168.1.23',label:${JSON.stringify(L.wifi)},name:'Wi-Fi'}]}),
    save_settings:async()=>{}, refresh_networks:async()=>{}, set_language:async l=>l,
    pick_files:async()=>${JSON.stringify(L.files)},
    share_wifi:async()=>({url:${JSON.stringify(D.urls.wifi)},qr:${JSON.stringify(D.qr.wifi)}}),
    share_internet:async()=>({url:${JSON.stringify(D.urls.net)},qr:${JSON.stringify(D.qr.net)},site:'Litterbox',service:'litterbox',size:${L.files[0].size},direct:true}),
    qr:async()=>${JSON.stringify(L.link_qr)}, save_png:async()=>true, stop_wifi:async()=>true,
    startup_state:async()=>({supported:true,enabled:true,note:''}), set_startup:async e=>({supported:true,enabled:e}),
    hide:async()=>{}, quit:async()=>{}, copy:async()=>{} }};`;
}
const FONT_CSS = 'body,button,select,textarea{font-family:Inter,-apple-system,"Segoe UI",sans-serif!important}';

async function captureWindow(browser, lang, scheme, steps) {
  const p = await browser.newPage({ viewport: { width: 380, height: 660 }, colorScheme: scheme, deviceScaleFactor: 2 });
  await p.addInitScript(mockApi(lang));
  await p.goto(UI);
  await p.addStyleTag({ content: FONT_CSS + '*{transition:none!important;animation:none!important}' });
  await p.waitForTimeout(300);
  await steps(p);
  await p.waitForTimeout(400);
  const buf = await p.screenshot();
  await p.close();
  return buf;
}

async function capturePhone(browser, lang) {
  const p = await browser.newPage({ viewport: { width: 390, height: 780 }, colorScheme: 'light', deviceScaleFactor: 2 });
  await p.setContent(D.langs[lang].phone_html);
  await p.addStyleTag({ content: 'body{font-family:Inter,sans-serif!important}' });
  const buf = await p.screenshot();
  await p.close();
  return buf;
}

const img = b => 'data:image/png;base64,' + b.toString('base64');

function compose({ title, sub, dark, windows, phone }) {
  const bg = dark
    ? 'radial-gradient(1200px 800px at 75% 40%,#1b2740 0%,#0f1218 60%,#0b0d11 100%)'
    : 'radial-gradient(1200px 800px at 75% 40%,#e3eeff 0%,#f3f5f9 55%,#f7f7f9 100%)';
  const fg = dark ? '#f5f5f7' : '#1d1d1f', mut = dark ? '#a1a1a6' : '#6e6e73';
  const wins = windows.map(w => `<img class="win" src="${img(w.buf)}" style="left:${w.x}px;top:${w.y}px;height:${w.h}px;z-index:${w.z || 1}">`).join('');
  const ph = phone ? `<div class="phone" style="left:${phone.x}px;top:${phone.y}px"><img src="${img(phone.buf)}"></div>` : '';
  return `<!doctype html><html><head><meta charset="utf-8"><style>
    *{margin:0;box-sizing:border-box}
    body{width:1920px;height:1080px;overflow:hidden;background:${bg};font-family:Inter,sans-serif;color:${fg};position:relative;-webkit-font-smoothing:antialiased}
    .text{position:absolute;left:150px;top:0;bottom:0;width:780px;display:flex;flex-direction:column;justify-content:center}
    .brand{display:flex;align-items:center;gap:14px;font:600 26px Inter;margin-bottom:38px;color:${fg}}
    .logo{width:48px;height:48px;border-radius:14px;background:linear-gradient(180deg,#4a9cff,#0a6ee6);display:grid;place-items:center;box-shadow:0 6px 16px rgba(10,110,230,.25)}
    .logo svg{width:28px;height:28px;fill:#fff}
    h1{font:600 62px/1.1 "Inter Display",Inter;letter-spacing:-1.4px;margin-bottom:26px}
    p{font:400 27px/1.5 Inter;color:${mut};max-width:640px}
    .win{position:absolute;border-radius:24px;box-shadow:0 2px 6px rgba(0,0,0,${dark ? .5 : .06}),0 40px 90px rgba(${dark ? '0,0,0,.6' : '30,50,90,.18'})}
    .phone{position:absolute;width:336px;padding:12px;border-radius:54px;background:#16161a;box-shadow:0 0 0 2px #2c2c30 inset,0 40px 90px rgba(30,50,90,.28);z-index:3}
    .phone img{display:block;width:312px;border-radius:42px}
  </style></head><body>
    <div class="text">
      <div class="brand"><div class="logo"><svg viewBox="0 0 16 16"><path d="M2 2h4.5v4.5H2zm1.4 1.4v1.7h1.7V3.4zM9.5 2H14v4.5H9.5zm1.4 1.4v1.7h1.7V3.4zM2 9.5h4.5V14H2zm1.4 1.4v1.7h1.7v-1.7zM12 9v3.3l1.1-1.1.9.9-2.6 2.6-2.6-2.6.9-.9 1.1 1.1V9z"/></svg></div>Share QR</div>
      <h1>${title}</h1><p>${sub}</p>
    </div>${wins}${ph}
  </body></html>`;
}

(async () => {
  const browser = await chromium.launch();
  const stage = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  for (const lang of Object.keys(CAPTIONS)) {
    fs.mkdirSync(path.join(OUT, lang), { recursive: true });
    const C = CAPTIONS[lang];
    const pick = async p => { await p.click('#pickBtn'); await p.waitForTimeout(150); };

    const sMain = await captureWindow(browser, lang, 'light', pick);
    const sResult = await captureWindow(browser, lang, 'light', async p => { await pick(p); await p.click('#goBtn'); });
    const sNet = await captureWindow(browser, lang, 'light', async p => {
      await pick(p); await p.click('#mode button[data-v=net]'); await p.selectOption('#svcSel', 'litterbox');
      await p.dispatchEvent('#svcSel', 'change'); });
    const sLink = await captureWindow(browser, lang, 'light', async p => {
      await p.click('#tabs button[data-v=link]'); await p.fill('#linkText', D.langs[lang].link);
      await p.evaluate(() => document.activeElement && document.activeElement.blur()); });
    const sDarkMain = await captureWindow(browser, lang, 'dark', pick);
    const sDarkSet = await captureWindow(browser, lang, 'dark', async p => { await p.click('#settingsBtn'); });
    const sPhone = await capturePhone(browser, lang);

    const H = 900, W = Math.round(H * 380 / 660);
    const shots = [
      { windows: [{ buf: sMain, x: 1180, y: 90, h: H }] },
      { windows: [{ buf: sResult, x: 930, y: 110, h: 860 }], phone: { buf: sPhone, x: 1470, y: 240 } },
      { windows: [{ buf: sNet, x: 1180, y: 90, h: H }] },
      { windows: [{ buf: sLink, x: 1180, y: 90, h: H }] },
      { dark: true, windows: [{ buf: sDarkMain, x: 960, y: 150, h: 760 }, { buf: sDarkSet, x: 1430, y: 200, h: 760 }] },
    ];
    for (let i = 0; i < shots.length; i++) {
      await stage.setContent(compose({ title: C[i][0], sub: C[i][1], ...shots[i] }));
      await stage.waitForTimeout(150);
      const file = path.join(OUT, lang, NAMES[i] + '.png');
      await stage.screenshot({ path: file });
      console.log(path.relative(ROOT, file));
    }
  }
  await browser.close();
})();
