# StreamTV Packaging Guide

StreamTV ships **macOS** (native app + legacy installer) and **Linux** packaging overlays under `packaging/`. Other platform packaging was removed; the project is MIT-licensed for community ports.

## Quick start

```bash
make build-all      # macOS + Linux installers
make build-macos    # macOS legacy installer
make build-linux    # Linux installer
```

Distribution assemblies for release:

```bash
python3 scripts/build_distributions.py macos linux
# Output: dist/StreamTV-macos, dist/StreamTV-linux
```

## macOS (native app — recommended)

Signed DMGs publish to [GitHub Releases](https://github.com/roto31/StreamTV/releases).

**Release build (CI):**

```bash
git tag v1.3.0 && git push origin v1.3.0
```

**Local unsigned build:**

```bash
bash scripts/release_build_macos_app.sh --no-notarize --no-dmg
```

**Develop in Xcode:**

```bash
cd StreamTVMac && ./sync-python-code.sh && open StreamTVMac.xcodeproj
```

See [docs/macos-native-app.md](docs/macos-native-app.md).

## macOS (legacy installer)

```bash
make build-macos
# Output: StreamTVInstaller/build/StreamTV Installer.app
```

Overlay files: `packaging/macos/`

## Linux

```bash
make build-linux
# Output: dist-linux/
```

Overlay files: `packaging/linux/`

## Build targets

| Target | Description |
|--------|-------------|
| `make build-macos` | macOS legacy installer |
| `make build-linux` | Linux installer |
| `make build-all` | Both platforms |
| `make package-desktop` | Collect artifacts into `dist/` |
| `make clean` | Remove build artifacts |

## Output directories

- `StreamTVInstaller/build/` — macOS app bundle
- `dist-linux/` — Linux executable
- `dist/StreamTV-macos`, `dist/StreamTV-linux` — assembled distributions

## Community ports
