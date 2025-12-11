# StreamTV SwiftUI Installer for macOS

## Overview

The SwiftUI installer provides a **native macOS experience** with a beautiful, modern interface built using Apple's SwiftUI framework.

## Features

### Native macOS Experience

- **SwiftUI Interface**: Built with Apple's modern UI framework
- **Native Look & Feel**: Matches macOS design guidelines
- **Smooth Animations**: Native macOS animations and transitions
- **Accessibility**: Full VoiceOver and accessibility support
- **Dark Mode**: Automatic dark mode support

### Visual Status Indicators

Each module shows its status with native macOS icons:

- **Green Checkmark**: Module installed/updated successfully
- **Yellow Warning**: Module has issues but installation continued
- **Red Error**: Module installation failed

### Module Detection

The installer automatically detects:
- **Existing installations**: Checks if modules are already installed
- **Updates needed**: Identifies modules that need updating
- **Corrupted installations**: Detects and offers to fix corrupted modules

### Auto-Fix Capabilities

When issues are detected, the installer can:
- Recreate corrupted virtual environments
- Reinstall missing dependencies
- Fix configuration file issues
- Repair database corruption

## Building the Installer

### Option 1: Using Xcode (Recommended)

1. Open `StreamTVInstaller/StreamTVInstaller.xcodeproj` in Xcode
2. Select "My Mac" as the destination
3. Press `Cmd+B` to build
4. Press `Cmd+R` to run
5. The app will be built in `StreamTVInstaller/build/StreamTV Installer.app`

### Option 2: Using Build Script

```bash
./build-installer.sh
```

This will:
- Build the SwiftUI app
- Create a standalone `.app` bundle
- Place it in the `build/` directory

### Option 3: Using Swift Package Manager

```bash
cd StreamTVInstaller
swift build -c release
```

## Running the Installer

### Double-Click Method

1. **Build the installer** (see above)
2. **Double-click** `Install-StreamTV-SwiftUI.command`
3. The SwiftUI installer will open automatically
4. Click **"Start Installation"**
5. Wait for installation to complete
6. Click **"Fix Issues"** if any problems are detected (optional)

### Direct App Launch

1. Navigate to `StreamTVInstaller/build/StreamTV Installer.app`
2. **Double-click** the app
3. The installer will open

### From Terminal

```bash
open "build/StreamTV Installer.app"
```

## Requirements

- **macOS**: 11.0 (Big Sur) or later
- **Xcode**: 13.0 or later (for building)
- **Swift**: 5.5 or later

## What Gets Installed

The installer automatically:
- ✓ Checks for Python (opens installer if needed)
- ✓ Checks for FFmpeg (installs via Homebrew or direct download)
- ✓ Creates virtual environment
- ✓ Installs all Python packages
- ✓ Sets up configuration
- ✓ Initializes database
- ✓ Sets up workspace directories for your channels
- ✓ Creates launch scripts and launchd service

## Advantages Over Tkinter

### Native Experience
- **Better Performance**: Native SwiftUI is faster than Tkinter
- **Modern UI**: Follows macOS Human Interface Guidelines
- **Better Integration**: Works seamlessly with macOS features

### User Experience
- **Smooth Animations**: Native macOS animations
- **Dark Mode**: Automatic dark mode support
- **Accessibility**: Full VoiceOver support
- **Native Dialogs**: Uses macOS native alert dialogs

### Development
- **Type Safety**: Swift's type system prevents errors
- **Modern Language**: Swift is Apple's modern language
- **Better Tooling**: Xcode provides excellent debugging

## Troubleshooting

### "Xcode not found"

To build the SwiftUI installer, you need Xcode:
1. Install Xcode from the App Store
2. Open Xcode and accept the license
3. Install command line tools: `xcode-select --install`

### "Build failed"

If the build fails:
1. Make sure Xcode is up to date
2. Check that all Swift files are in `StreamTVInstaller/` directory
3. Try cleaning the build: `rm -rf build/`
4. Rebuild using Xcode

### "App won't open"

If the app won't open:
1. Right-click the app → Open (to bypass Gatekeeper)
2. Check System Preferences → Security & Privacy
3. Make sure the app is notarized (for distribution)

### "Python/FFmpeg installation issues"

The SwiftUI installer uses the same installation logic as the Python installer. See the main README for troubleshooting.

## Distribution

### For End Users

1. Build the installer app
2. Create a DMG or ZIP file
3. Users can double-click to install

### Code Signing (Optional)

For distribution outside the App Store:
1. Get an Apple Developer certificate
2. Sign the app in Xcode
3. Notarize the app for Gatekeeper

## Comparison with Python Installer

| Feature | SwiftUI Installer | Python Installer |
|---------|------------------|------------------|
| Native Look | ✅ Yes | ❌ No |
| Performance | ✅ Fast | ⚠️ Slower |
| Dark Mode | ✅ Automatic | ⚠️ Limited |
| Accessibility | ✅ Full | ⚠️ Basic |
| Build Required | ⚠️ Yes | ✅ No |
| Distribution | ⚠️ Needs build | ✅ Direct |

## Path Independence

The SwiftUI installer is fully path-independent:
- Works from any location
- Handles symlinks correctly
- Resolves absolute paths automatically

See `PATH_INDEPENDENCE.md` for details.

