# StreamTV SwiftUI Installer - Complete Guide

## Overview

The SwiftUI installer provides a **native macOS experience** with a beautiful, modern interface built using Apple's SwiftUI framework. This replaces the Tkinter-based installer with a fully native macOS application.

## Quick Start

### Building the Installer

**Option 1: Using Xcode (Recommended)**

1. **Open Xcode**
2. **File → Open** → Navigate to `StreamTVInstaller/StreamTVInstaller.xcodeproj`
3. If the project doesn't exist, create it:
   - **File → New → Project**
   - Select **macOS** → **App**
   - Product Name: `StreamTV Installer`
   - Interface: **SwiftUI**
   - Language: **Swift**
   - Save in the `StreamTVInstaller/` directory
   - Replace generated files with existing Swift files
4. **Select "My Mac"** as destination
5. **Press `Cmd+B`** to build
6. **Press `Cmd+R`** to run

**Option 2: Using Build Script**

```bash
./build-installer.sh
```

**Option 3: Command Line**

```bash
cd StreamTVInstaller
xcodebuild -project StreamTVInstaller.xcodeproj \
           -scheme "StreamTV Installer" \
           -configuration Release
```

### Running the Installer

**Double-Click Method:**
1. Build the installer (see above)
2. Double-click `Install-StreamTV-SwiftUI.command`
3. The native SwiftUI installer will open

**Direct App Launch:**
1. Navigate to `StreamTVInstaller/build/StreamTV Installer.app`
2. Double-click the app

## Features

### Native macOS Experience

- ✅ **SwiftUI Interface**: Built with Apple's modern UI framework
- ✅ **Native Look & Feel**: Matches macOS Human Interface Guidelines
- ✅ **Smooth Animations**: Native macOS animations and transitions
- ✅ **Dark Mode**: Automatic dark mode support
- ✅ **Accessibility**: Full VoiceOver and accessibility support
- ✅ **SF Symbols**: Uses native macOS icon system

### Visual Status Indicators

Each module shows its status with native SF Symbols:

- **Green Checkmark** (`checkmark.circle.fill`): Success
- **Yellow Warning** (`exclamationmark.triangle.fill`): Issues detected
- **Red Error** (`xmark.circle.fill`): Installation failed
- **Blue Info** (`info.circle.fill`): Information messages

### Installation Features

- ✅ **Module Detection**: Automatically detects existing installations
- ✅ **Update Support**: Updates existing modules when needed
- ✅ **Auto-Fix**: Attempts to fix detected issues automatically
- ✅ **Real-time Progress**: Live progress bar and status updates
- ✅ **Path Independent**: Works from any location

## Project Structure

```
StreamTV/
├── StreamTVInstaller/
│   ├── StreamTVInstaller.swift         # App entry point
│   ├── ContentView.swift                # Main UI view
│   ├── InstallerViewModel.swift         # Installation logic
│   ├── Package.swift                    # Swift Package Manager config
│   ├── Info.plist                       # App metadata
│   ├── StreamTVInstaller.xcodeproj/    # Xcode project
│   └── build/                           # Build output directory
│       └── StreamTV Installer.app       # Built application
├── build-installer.sh                   # Build script
├── Install-StreamTV-SwiftUI.command     # Launcher
└── README_SWIFTUI.md                    # This file
```

## Requirements

- **macOS**: 11.0 (Big Sur) or later
- **Xcode + Command Line Tools**: 16.2 or later (matching SDK/CoreSimulator runtimes)
- **CoreSimulator runtimes**: install the latest tvOS/iOS simulators from **Xcode → Settings → Platforms**
- **Swift**: 5.5 or later
- **xcbeautify**: optional (`brew install xcbeautify`) for prettier `xcodebuild` output

## Installation Modules

The installer handles:

1. **Python** - Checks version, downloads installer if needed
2. **FFmpeg** - Installs via Homebrew or direct download
3. **Virtual Environment** - Creates/updates venv
4. **pip** - Upgrades pip, setuptools, wheel
5. **Dependencies** - Installs/updates Python packages
6. **Configuration** - Sets up config.yaml
7. **Database** - Initializes SQLite database
8. **Channels** - Creates default channels
9. **Launch Scripts** - Creates start scripts and launchd service

## Advantages Over Tkinter

| Feature | SwiftUI Installer | Tkinter Installer |
|---------|-------------------|-------------------|
| Native Look | ✅ Yes | ❌ No |
| Performance | ✅ Fast | ⚠️ Slower |
| Dark Mode | ✅ Automatic | ⚠️ Limited |
| Accessibility | ✅ Full | ⚠️ Basic |
| Animations | ✅ Smooth | ⚠️ Basic |
| SF Symbols | ✅ Yes | ❌ No |
| Build Required | ⚠️ Yes | ✅ No |

## Troubleshooting

### "Xcode not found"

Install Xcode from the App Store, then:
```bash
xcode-select --install
```

### "Cannot find type 'NSApplication'"

Add import to ContentView.swift:
```swift
import AppKit
```

### "Build failed"

1. Clean build: `Cmd+Shift+K` in Xcode
2. Delete derived data
3. Rebuild: `Cmd+B`

### "App won't open"

1. Right-click → Open (to bypass Gatekeeper)
2. Check System Preferences → Security & Privacy
3. For distribution, code sign the app

### Path Detection Issues

The app automatically finds the StreamTV directory:
- When running as app bundle: Looks relative to app location
- When running from source: Uses current directory
- Searches up directory tree to find StreamTV root

## Distribution

### For End Users

1. Build the installer app
2. Create a DMG or ZIP file
3. Users can double-click to install

### Code Signing (Optional)

For distribution outside the App Store:
1. Get Apple Developer certificate
2. In Xcode: Signing & Capabilities → Enable signing
3. Archive and export from Xcode

## Comparison with Python Installer

The SwiftUI installer provides the same functionality as the Python installer but with:
- Better performance
- Native macOS appearance
- Better accessibility
- Automatic dark mode
- Smoother animations

Both installers are available - choose based on your preference!

## Path Independence

The SwiftUI app is fully path-independent:
- Works from any location
- Handles symlinks correctly
- Resolves absolute paths automatically
- Changes working directory as needed

See `PATH_INDEPENDENCE.md` for details.
