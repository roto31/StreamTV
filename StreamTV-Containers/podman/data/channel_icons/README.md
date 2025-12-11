# Channel Icons

Place your channel icon images in this directory.

## Supported Formats

- PNG (recommended)
- JPG/JPEG
- GIF

## Naming Convention

Icons can be named:
- `channel_{number}.png` (e.g., `channel_1.png`, `channel_2.png`)
- Or any name you prefer - you'll reference it in your channel configuration

## Usage

Reference icons in your channel configuration YAML file:

```yaml
channels:
  - number: "1"
    name: "My Channel"
    icon: "data/channel_icons/channel_1.png"
```
