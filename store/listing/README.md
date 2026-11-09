# Store listing / Mağaza sayfası

Partner Center → **Store listings** → choose the language → copy from the matching file:

| Partner Center language | File | Screenshots |
|---|---|---|
| English (United States) | [en-US.md](en-US.md) | [`store/screenshots/en/`](../screenshots/en/) |
| Turkish (Türkiye) | [tr-TR.md](tr-TR.md) | [`store/screenshots/tr/`](../screenshots/tr/) |
| Spanish (Spain) | [es-ES.md](es-ES.md) | [`store/screenshots/es/`](../screenshots/es/) |

Artwork for every language is in [`store/art/`](../art/): poster (9:16), box art (1:1), super hero art (16:9) and tile icons.

Regenerate images:
```bash
node tools/screenshots/make_screenshots.cjs
```
```bash
node tools/screenshots/make_store_art.cjs
```
