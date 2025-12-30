# App Store Readiness Checklist

## Code Signing & Notarization

- [x] ExportOptions.plist configured for developer-id distribution
- [x] ExportOptions-AppStore.plist created for App Store submission
- [x] Build script supports `--app-store` flag for App Store export
- [x] Notarization script (`notarize.sh`) configured with `xcrun notarytool`
- [x] Code signing configured in Xcode project (automatic signing)

## Privacy & Permissions

- [x] PrivacyInfo.xcprivacy created with required API usage declarations
- [x] NSUserNotificationsUsageDescription in Info.plist
- [x] NSAppleEventsUsageDescription in Info.plist
- [x] NSAppTransportSecurity configured for local networking
- [x] Entitlements file (StreamTV.entitlements) configured

## App Store Metadata

### Required Information
- [ ] App description (prepare for App Store Connect)
- [ ] App icon (1024x1024 PNG, no transparency)
- [ ] Screenshots (at least one for each supported device)
- [ ] Privacy policy URL
- [ ] Support URL
- [ ] Marketing URL (optional)
- [ ] App category: Utilities
- [ ] Age rating: 4+ (no objectionable content)

### App Information
- Bundle Identifier: `com.streamtv.app` (verify in Xcode)
- Version: 1.0
- Build: 1
- Minimum macOS Version: 13.0
- App Type: Menu Bar App (LSUIElement = true)

## Technical Requirements

- [x] 64-bit architecture support (arm64, x86_64)
- [x] Hardened Runtime (if applicable - menu bar apps may not require)
- [x] Code signing certificate configured
- [x] App sandbox: Disabled (required for menu bar apps with network server)
- [x] Network entitlements: Client and Server enabled
- [x] File access entitlements: User-selected and Downloads

## Build & Distribution

### For App Store Submission:
```bash
cd StreamTVApp
./build-app.sh --app-store
```

This will:
1. Build the app with Release configuration
2. Create an archive
3. Export using App Store export options
4. Output to `build/export/StreamTV.app`

### For Direct Distribution (Developer ID):
```bash
cd StreamTVApp
./build-app.sh
./notarize.sh build/export/StreamTV.app <apple_id> <app_specific_password> <team_id>
```

## App Store Connect Submission

1. **Create App Record**
   - App name: StreamTV
   - Primary language: English
   - Bundle ID: com.streamtv.app
   - SKU: streamtv-macos-001

2. **App Information**
   - Category: Utilities
   - Age rating: 4+
   - Description: [Prepare description]
   - Keywords: IPTV, streaming, Plex, HDHomeRun, media server
   - Support URL: [Your support URL]
   - Marketing URL: [Optional]
   - Privacy Policy URL: [Required]

3. **Pricing & Availability**
   - Price: Free or Paid
   - Availability: All countries or specific regions

4. **App Review Information**
   - Contact information
   - Demo account (if applicable)
   - Notes: Explain that this is a menu bar app that runs a local server

5. **Version Information**
   - Version: 1.0
   - What's New: Initial release
   - Screenshots: At least one required

6. **Build Submission**
   - Upload the exported .app using Transporter or Xcode
   - Or use `xcrun altool` / `xcrun notarytool` for command-line upload

## Important Notes

### Menu Bar Apps
- Menu bar apps (LSUIElement = true) don't appear in the Dock
- App Store review may require explanation of menu bar functionality
- Network server functionality must be clearly documented

### Network Server
- The app runs a local web server on port 8410
- This requires network server entitlements
- App Store review may ask about network usage justification

### Python Dependencies
- The app bundles Python code and installs dependencies in a virtual environment
- This is acceptable for App Store apps
- Ensure all bundled code is properly licensed

### Sandbox Considerations
- App sandbox is disabled (com.apple.security.app-sandbox = false)
- This is common for menu bar apps that need network server functionality
- App Store review may require justification

## Pre-Submission Checklist

- [ ] Test app on clean macOS 13.0+ installation
- [ ] Verify all features work correctly
- [ ] Test menu bar functionality
- [ ] Test server startup and web interface
- [ ] Verify Python dependencies install correctly
- [ ] Test FFmpeg detection and installation prompts
- [ ] Verify notifications work
- [ ] Test "Check for Updates" functionality
- [ ] Prepare app description and screenshots
- [ ] Prepare privacy policy
- [ ] Prepare support documentation
- [ ] Review App Store Review Guidelines
- [ ] Test with TestFlight (optional but recommended)

## Resources

- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Human Interface Guidelines - Menu Bar Apps](https://developer.apple.com/design/human-interface-guidelines/macos/system-capabilities/menu-bar-apps/)
- [App Store Connect Help](https://help.apple.com/app-store-connect/)
- [Notarization Documentation](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)

