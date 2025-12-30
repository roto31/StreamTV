# StreamTV Menu Bar App

A native macOS menu bar application for managing StreamTV server.

## Setup Instructions

### 1. Create Xcode Project

Since the Xcode project file is complex, it's recommended to create it using Xcode:

1. Open Xcode
2. File → New → Project
3. Choose "macOS" → "App"
4. Product Name: `StreamTV`
5. Bundle Identifier: `com.streamtv.app`
6. Language: Swift
7. Interface: SwiftUI
8. Save in the `StreamTVApp/` directory

### 2. Configure Project Settings

1. Select the project in the navigator
2. Select the "StreamTV" target
3. General tab:
   - Deployment Target: macOS 13.0
   - Bundle Identifier: `com.streamtv.app`
4. Signing & Capabilities:
   - Enable "Automatically manage signing" or configure manual signing
   - Add entitlements file: `StreamTV.entitlements`
5. Build Settings:
   - Swift Language Version: Swift 5.9
   - macOS Deployment Target: 13.0

### 3. Add Files to Project

Add all Swift files to the project:
- `StreamTVApp.swift`
- `ServerManager.swift`
- `PythonManager.swift`
- `FFmpegManager.swift`
- `OllamaChecker.swift`
- `DependencyUpdater.swift`
- `MenuBarView.swift`
- `FirstLaunchView.swift`

### 4. Configure Build Phases

1. Select the target → Build Phases
2. Copy Bundle Resources:
   - Add `Info.plist`
   - Add `Assets.xcassets`
   - Add `streamtv/` folder (as folder reference, not group)
   - Add `requirements.txt`

### 5. Bundle Python Code

The `streamtv/` directory and `requirements.txt` need to be copied into the app bundle:

**Automated Sync (Recommended):**
```bash
cd StreamTVApp
./sync-python-code.sh
```

This script automatically:
- Copies the latest `streamtv/` directory from the root
- Copies the latest `requirements.txt` from the root
- Verifies jsonschema versions are up to date

**Manual Setup:**
1. Copy `streamtv/` directory to `StreamTVApp/StreamTV/StreamTV/`
2. Copy `requirements.txt` to `StreamTVApp/StreamTV/StreamTV/`
3. Add both to "Copy Bundle Resources" build phase in Xcode

**Important:** After syncing, ensure these files are added to Xcode's "Copy Bundle Resources" build phase:
- `streamtv/` (as folder reference, not group)
- `requirements.txt`

### 6. Build

```bash
./build-menu-bar-app.sh
```

## Building

The build script will:
1. Check Xcode version and environment
2. Build the archive
3. Export the app bundle
4. Output the built app to `build/export/StreamTV.app`

## Notarization

To notarize the app for distribution:

```bash
./notarize.sh build/export/StreamTV.app your@email.com app-specific-password TEAM_ID
```

## Distribution

After building and notarizing, create a DMG:

```bash
# Using create-dmg (install via: brew install create-dmg)
create-dmg \
  --volname "StreamTV" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "StreamTV.app" 200 190 \
  --hide-extension "StreamTV.app" \
  --app-drop-link 600 185 \
  "StreamTV.dmg" \
  "build/export/StreamTV.app"

# Or using hdiutil
hdiutil create -volname "StreamTV" \
  -srcfolder "build/export/StreamTV.app" \
  -ov -format UDZO \
  "StreamTV.dmg"
```

## Notes

- The app requires Python 3.8+ and FFmpeg
- Python dependencies are installed in a virtual environment in `~/Library/Application Support/StreamTV/venv`
- Server logs are stored in `~/Library/Application Support/StreamTV/logs/`
- The app runs as a menu bar item (no dock icon) due to `LSUIElement = true`

