/*
 * Microsoft Store mağaza görsellerini üretir (dilden bağımsız):
 *   store/art/poster-9x16-1440x2160.png   9:16 Poster art (Windows 10/11 ana logo)
 *   store/art/box-1x1-2160x2160.png       1:1 Box art
 *   store/art/hero-16x9-3840x2160.png     16:9 Super hero art (kural gereği ürün adı YOK)
 *   store/art/tile-300.png / tile-150.png / tile-71.png   Store display images
 *
 *   node tools/screenshots/make_store_art.cjs
 */
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const OUT = path.join(ROOT, 'store', 'art');
fs.mkdirSync(OUT, { recursive: true });

// İkonları uygulamanın kendi ikon çizicisiyle (tools/make_icons.py) üret
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'scanload-art-'));
execFileSync('python3', ['-c', `
import sys; sys.path.insert(0, ${JSON.stringify(path.join(ROOT, 'tools'))})
from make_icons import app_icon
app_icon(1024).save(${JSON.stringify(path.join(TMP, 'icon.png'))})
app_icon(1024, plate=False).save(${JSON.stringify(path.join(TMP, 'glyph.png'))})
for n in (300, 150, 71):
    app_icon(n).save(${JSON.stringify(OUT)} + '/tile-%d.png' % n)
`]);
const b64 = f => 'data:image/png;base64,' + fs.readFileSync(path.join(TMP, f)).toString('base64');
const ICON = b64('icon.png'), GLYPH = b64('glyph.png');

const BASE = `*{margin:0;box-sizing:border-box}body{overflow:hidden;font-family:"Inter Display",Inter,sans-serif;-webkit-font-smoothing:antialiased}`;
const BG = `radial-gradient(120% 90% at 30% 15%,#6fb3ff 0%,#2f8bff 38%,#0a63d8 75%,#0752b8 100%)`;

// Poster / Box: ikon + ad (dilden bağımsız)
const brand = (w, h, icon, font, gap) => `<!doctype html><html><head><meta charset="utf-8"><style>${BASE}
  body{width:${w}px;height:${h}px;background:${BG};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:${gap}px;position:relative}
  .glow{position:absolute;width:${w * 1.1}px;height:${w * 1.1}px;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.22),transparent 60%);top:${h / 2 - w * .75}px}
  img{width:${icon}px;height:${icon}px;border-radius:${icon * .225}px;box-shadow:0 ${icon * .08}px ${icon * .22}px rgba(0,30,90,.35),0 0 0 ${icon * .012}px rgba(255,255,255,.35);position:relative}
  h1{font-weight:600;font-size:${font}px;letter-spacing:${-font * .025}px;color:#fff;position:relative}
</style></head><body><div class="glow"></div><img src="${ICON}"><h1>Scanload</h1></body></html>`;

// Hero: bilgisayardan telefona giden dosyalar — yazı yok
const hero = () => {
  const file = (x, y, s, rot, kind) => {
    const icons = {
      doc: '<path d="M7 2.5h6.6l5.9 5.9V19a2.5 2.5 0 0 1-2.5 2.5H7A2.5 2.5 0 0 1 4.5 19V5A2.5 2.5 0 0 1 7 2.5zm6 1.8V8a1 1 0 0 0 1 1h3.7z"/>',
      photo: '<path d="M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm0 12.5V18h14v-3l-4-4-5 5-2.5-2.5zM8.5 7a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"/>',
      video: '<path d="M4 5h12a2 2 0 0 1 2 2v2.5l4-2.5v10l-4-2.5V17a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"/>',
      music: '<path d="M19 3v12.5a3 3 0 1 1-2-2.8V7.3l-8 1.8v8.4a3 3 0 1 1-2-2.8V5.5z"/>',
    };
    return `<div class="chip" style="left:${x}px;top:${y}px;width:${s}px;height:${s}px;transform:rotate(${rot}deg)">
      <svg viewBox="0 0 24 24">${icons[kind]}</svg></div>`;
  };
  return `<!doctype html><html><head><meta charset="utf-8"><style>${BASE}
  body{width:3840px;height:2160px;background:${BG};position:relative}
  .glow{position:absolute;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.18),transparent 62%)}
  .laptop{position:absolute;left:520px;top:520px;width:1500px;height:980px;border-radius:64px;background:rgba(255,255,255,.16);
    box-shadow:inset 0 0 0 4px rgba(255,255,255,.35),0 60px 160px rgba(0,30,90,.35);-webkit-backdrop-filter:blur(30px);backdrop-filter:blur(30px)}
  .laptop .qr{position:absolute;left:50%;top:50%;width:620px;height:620px;transform:translate(-50%,-50%);border-radius:96px;background:#fff;
    box-shadow:0 40px 100px rgba(0,30,90,.3);display:grid;place-items:center}
  .laptop .qr img{width:470px;height:470px;filter:brightness(0) saturate(100%) invert(31%) sepia(97%) saturate(2400%) hue-rotate(205deg) brightness(97%)}
  .base{position:absolute;left:400px;top:1530px;width:1740px;height:70px;border-radius:0 0 50px 50px;background:rgba(255,255,255,.28);box-shadow:inset 0 0 0 4px rgba(255,255,255,.3)}
  .phone{position:absolute;left:2780px;top:470px;width:600px;height:1220px;border-radius:110px;background:rgba(255,255,255,.95);
    box-shadow:0 0 0 22px rgba(255,255,255,.25),0 60px 160px rgba(0,30,90,.4)}
  .phone .row{position:absolute;left:60px;right:60px;height:150px;border-radius:40px;background:#eef5ff;display:flex;align-items:center;gap:36px;padding:0 36px}
  .phone .row i{width:84px;height:84px;border-radius:26px;background:#d8e8ff;flex:none}
  .phone .row b{flex:1;height:26px;border-radius:13px;background:#cfdcef}
  .phone .row u{width:120px;height:56px;border-radius:28px;background:#0a7cff;flex:none}
  .phone .down{position:absolute;left:50%;top:150px;transform:translateX(-50%);width:170px;height:170px;border-radius:52px;background:#e3efff;display:grid;place-items:center}
  .phone .down svg{width:100px;height:100px;fill:#0a7cff}
  .path{position:absolute;left:2040px;top:640px;width:760px;height:520px;border-top:10px dashed rgba(255,255,255,.55);border-radius:50% 50% 0 0}
  .chip{position:absolute;border-radius:28%;background:#fff;display:grid;place-items:center;box-shadow:0 30px 70px rgba(0,30,90,.3)}
  .chip svg{width:52%;height:52%;fill:#0a7cff}
</style></head><body>
  <div class="glow" style="left:-600px;top:-900px;width:2600px;height:2600px"></div>
  <div class="glow" style="left:2300px;top:900px;width:2200px;height:2200px"></div>
  <div class="laptop"><div class="qr"><img src="${GLYPH}"></div></div><div class="base"></div>
  <div class="path"></div>
  ${file(2140, 470, 200, -10, 'photo')}${file(2420, 330, 170, 8, 'video')}${file(2290, 760, 150, -4, 'doc')}${file(2560, 610, 130, 12, 'music')}
  <div class="phone">
    <div class="down"><svg viewBox="0 0 24 24"><path d="M12 3a1 1 0 0 1 1 1v9.6l3.3-3.3a1 1 0 1 1 1.4 1.4l-5 5a1 1 0 0 1-1.4 0l-5-5a1 1 0 1 1 1.4-1.4l3.3 3.3V4a1 1 0 0 1 1-1zM5 19h14a1 1 0 1 1 0 2H5a1 1 0 1 1 0-2z"/></svg></div>
    <div class="row" style="top:420px"><i></i><b></b><u></u></div>
    <div class="row" style="top:610px"><i></i><b></b><u></u></div>
    <div class="row" style="top:800px"><i></i><b></b><u></u></div>
  </div>
</body></html>`;
};

(async () => {
  const browser = await chromium.launch();
  const jobs = [
    ['poster-9x16-1440x2160.png', 1440, 2160, brand(1440, 2160, 620, 190, 110)],
    ['box-1x1-2160x2160.png', 2160, 2160, brand(2160, 2160, 820, 230, 120)],
    ['hero-16x9-3840x2160.png', 3840, 2160, hero()],
  ];
  for (const [name, w, h, html] of jobs) {
    const p = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    await p.setContent(html);
    await p.waitForTimeout(200);
    await p.screenshot({ path: path.join(OUT, name) });
    await p.close();
    console.log('store/art/' + name);
  }
  ['tile-300.png', 'tile-150.png', 'tile-71.png'].forEach(n => console.log('store/art/' + n));
  await browser.close();
  fs.rmSync(TMP, { recursive: true, force: true });
})();
