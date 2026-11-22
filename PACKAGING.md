# Packaging

StreamTV ships **macOS only** (native app + installer overlay under `packaging/macos/`).
There is **no Linux product**, packaging overlay, or maintained Linux fork.

## Build

```bash
make build-macos
# or
python3 scripts/build_distributions.py macos
# Output: dist/StreamTV-macos
```

## macOS

- Overlay: `packaging/macos/`
- Native app: `StreamTVMac/`
- Signed DMG: see [docs/macos-release-ci.md](docs/macos-release-ci.md)

## Notes

- `python3 scripts/build_distributions.py` builds the macOS distribution only.
- Do not reintroduce `packaging/linux/` or a `StreamTV-linux` product fork without an explicit owner decision.
