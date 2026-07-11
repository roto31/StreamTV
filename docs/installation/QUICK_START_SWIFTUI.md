# StreamTV SwiftUI Installer - Quick Start

## 🚀 Building the Native macOS Installer

### Step 1: Build the Installer

**Option A: Using Xcode (Recommended)**
1. Open `StreamTVInstaller/StreamTVInstaller.xcodeproj` in Xcode
2. Select "My Mac" as destination
3. Press `Cmd+B` to build
4. The app will be in `StreamTVInstaller/build/StreamTV Installer.app`

**Option B: Using Build Script**
```bash
./build-installer.sh
```

### Step 2: Run the Installer

**Double-Click Method:**
1. Double-click `Install-StreamTV-SwiftUI.command`
2. The native SwiftUI installer will open
3. Click **"Start Installation"**

**Direct App Launch:**
1. Navigate to `StreamTVInstaller/build/StreamTV Installer.app`
2. Double-click the app

## ✨ Features

- **Native macOS Experience**: Built with SwiftUI
- **Beautiful Interface**: Follows macOS design guidelines
- **Smooth Animations**: Native macOS animations
- **Dark Mode**: Automatic dark mode support
- **Accessibility**: Full VoiceOver support

## 📋 What Gets Installed

Same as the Python installer:
- ✓ Python (opens installer if needed)
- ✓ FFmpeg (installs via Homebrew or direct download)
- ✓ Virtual environment
- ✓ Python dependencies
- ✓ Configuration
- ✓ Database
- ✓ Default channels
- ✓ Launch scripts

## ❓ Troubleshooting

### "Xcode not found"
Install Xcode from the App Store, then:
```bash
xcode-select --install
```

### "Build failed"
1. Make sure Xcode is up to date
2. Clean build: `rm -rf build/`
3. Rebuild in Xcode

### "App won't open"
Right-click → Open (to bypass Gatekeeper)

## 🎯 Advantages

- **Better Performance**: Native SwiftUI is faster
- **Modern UI**: Follows macOS Human Interface Guidelines
- **Better Integration**: Works seamlessly with macOS

