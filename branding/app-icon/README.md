# StreamTV application icon

Master artwork for the macOS app (and web favicon / Apple touch icon).

## Concept

Combines the platform’s identity in one mark (v2 — source-aware):

| Aspect | Visual |
|--------|--------|
| Live TV / Plex HDHomeRun | Late-70s/early-80s **wood-cabinet CRT** (RCA XL-100–like form: walnut grain, right-side dial + speaker louvers, champagne bezel) — no brand marks |
| Archive.org (hint, no logo) | Warm sepia **film strip** with sprocket holes on the left of the screen |
| YouTube / online video (hint, no logo) | Cool teal pane + **play triangle** + stream waveform on the right |
| Continuous playout | Soft gold split where archive meets live stream |
| Homelab product | Charcoal macOS squircle — not neon / cartoon / purple AI |

No trademarked YouTube/Archive.org marks or wordmarks — metaphors only.

Style: photorealistic product icon, readable at Dock size.

## Files

| File | Use |
|------|-----|
| `StreamTV-app-icon-1024.png` | Master 1024² |
| `StreamTV.icns` | Finder / DMG volume icon |
| `apple-touch-icon.png` | 180² web |
| `favicon-16.png` / `favicon-32.png` / `favicon.ico` | Browser tab |
| (copied into) `StreamTVMac/.../AppIcon.appiconset/` | Xcode macOS app |

## Regenerate AppIcon sizes

```bash
bash scripts/install_app_icon.sh
```

After changing the master, rebuild/sign the macOS app (or cut a release) so Dock/Finder pick up the new icon.
