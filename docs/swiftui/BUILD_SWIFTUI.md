# Building the SwiftUI Installer

## Quick Start

### Option 1: Open in Xcode (Easiest)

1. **Open Xcode**
2. **File → Open** → Select `StreamTVInstaller/StreamTVInstaller.xcodeproj`
3. **Select "My Mac"** as the destination
4. **Press `Cmd+B`** to build
5. **Press `Cmd+R`** to run

The app will be built in `StreamTVInstaller/build/` and you can test it immediately.

### Option 2: Build from Command Line

```bash
# Build using xcodebuild
cd StreamTVInstaller
xcodebuild -project StreamTVInstaller.xcodeproj \
           -scheme "StreamTV Installer" \
           -configuration Release \
           -derivedDataPath build
```

### Option 3: Use Build Script

```bash
./build-installer.sh
```

## Project Structure

```
StreamTVInstaller/
├── StreamTVInstaller.swift         # App entry point
├── ContentView.swift                # Main UI view
├── InstallerViewModel.swift         # Installation logic
├── Package.swift                    # Swift Package Manager config
├── Info.plist                       # App metadata
├── StreamTVInstaller.xcodeproj/     # Xcode project
└── build/                           # Build output
    └── StreamTV Installer.app      # Built application
```

## Requirements

- **macOS**: 11.0 (Big Sur) or later
- **Xcode + Command Line Tools**: 16.2 or later (matching SDK/CoreSimulator runtimes)
- **CoreSimulator runtimes**: install the latest tvOS/iOS simulators from **Xcode → Settings → Platforms**
- **Swift**: 5.5 or later
- **xcbeautify**: optional (`brew install xcbeautify`) for prettier `xcodebuild` output; the build script will fall back automatically when it is missing

## Environment prep (Xcode/CLT/CoreSimulator)

1. Install or update Xcode to **16.2+**.
2. Install matching Command Line Tools: `xcode-select --install` (skip if already installed), then run `xcodebuild -runFirstLaunch` once.
3. Ensure CoreSimulator runtimes are installed: open Xcode → **Settings → Platforms** and add the latest tvOS/iOS simulators; verify with `xcrun simctl list`.
4. Optional: install `xcbeautify` (`brew install xcbeautify`) for formatted build logs. `build-installer.sh` automatically uses it when present.

## Creating the Project (If Needed)

If the Xcode project doesn't exist:

1. Open Xcode
2. File → New → Project
3. Select **macOS** → **App**
4. Configure:
   - Product Name: `StreamTV Installer`
   - Team: (your team or None)
   - Organization Identifier: `com.streamtv`
   - Interface: **SwiftUI**
   - Language: **Swift**
5. Save in the `StreamTVInstaller/` directory
6. Replace generated files with existing Swift files in the directory

## Building for Distribution

### Create Release Build

1. In Xcode, select **Product → Archive**
2. Wait for archive to complete
3. Distribute the app from Organizer

### Code Signing (Optional)

For distribution outside the App Store:
1. Get Apple Developer certificate
2. In Xcode: Signing & Capabilities → Enable signing
3. Archive and export

## Troubleshooting

### "No such module 'SwiftUI'"

Make sure you're targeting macOS 11.0 or later:
- In Xcode: Project Settings → Deployment Target → macOS 11.0

### "Cannot find type 'NSWorkspace'"

Add import:
```swift
import AppKit
```

### Build Errors

1. Clean build folder: `Cmd+Shift+K`
2. Delete derived data
3. Rebuild: `Cmd+B`

## Running the Built App

After building:
1. App will be in `StreamTVInstaller/build/StreamTV Installer.app`
2. Double-click to run
3. Or use: `open "StreamTVInstaller/build/StreamTV Installer.app"`

## Path Independence

The SwiftUI app automatically finds the StreamTV directory:
- When running as app bundle: Looks for StreamTV directory relative to app
- When running from source: Uses current directory
- Searches up directory tree to find StreamTV root
