# Apple Passkey Authentication Documentation

StreamTV now supports Apple Passkey (WebAuthn) authentication as a security layer for YouTube OAuth login, providing passwordless, biometric authentication.

## Overview

Apple Passkeys use WebAuthn technology to provide secure, passwordless authentication using:
- **Face ID** (iPhone/iPad with Face ID)
- **Touch ID** (MacBook with Touch ID)
- **Device Passcode** (fallback authentication)

Passkeys are stored securely in iCloud Keychain and sync across your Apple devices.

## How It Works

### Authentication Flow

1. **User initiates YouTube OAuth**
   - User clicks "Start OAuth with Passkey" on YouTube auth page
   - System checks if Passkey is registered

2. **Passkey Verification**
   - If registered: User authenticates with Face ID/Touch ID
   - If not registered: User creates a new Passkey first
   - Passkey verification confirms user identity

3. **Google OAuth**
   - After Passkey verification, user is redirected to Google OAuth
   - User authorizes StreamTV to access YouTube
   - OAuth tokens are stored securely

### Security Benefits

- **Phishing Resistant**: Passkeys use public-key cryptography
- **No Passwords**: Eliminates password-related security risks
- **Biometric Security**: Uses device biometrics (Face ID/Touch ID)
- **Device Bound**: Passkeys are tied to specific devices
- **Private**: Biometric data never leaves your device

## Setup

### Prerequisites

1. **Install webauthn library:**
   ```bash
   pip install webauthn
   ```

2. **Compatible Browser:**
   - Safari 16+ (macOS/iOS) - Full Passkey support
   - Chrome 108+ (macOS/Windows) - WebAuthn support
   - Edge 108+ (macOS/Windows) - WebAuthn support

3. **Device Requirements:**
   - macOS: Touch ID or device passcode
   - iOS/iPadOS: Face ID, Touch ID, or device passcode
   - Windows: Windows Hello (optional)

### Configuration

Passkeys work automatically with default settings. The system uses:
- **RP ID**: `localhost` (for local development)
- **RP Name**: `StreamTV`
- **Credentials Storage**: `data/passkeys.json`

For production, update the RP ID in `streamtv/api/auth.py`:
```python
rp_id = "yourdomain.com"  # Your actual domain
```

## Usage

### Registering a Passkey

1. **Navigate to YouTube Auth:**
   - Go to Settings → YouTube
   - Click "Start OAuth with Passkey"

2. **Create Passkey:**
   - Enter a username (e.g., "youtube_user")
   - Click "Create Passkey"
   - Authenticate with Face ID/Touch ID when prompted
   - Passkey is registered and stored

3. **Authenticate:**
   - Click "Authenticate with Passkey"
   - Use Face ID/Touch ID to verify
   - System proceeds to Google OAuth

### Authenticating with Passkey

1. **Start OAuth Flow:**
   - Click "Start OAuth with Passkey"
   - System checks for registered Passkey

2. **Biometric Authentication:**
   - Browser prompts for Face ID/Touch ID
   - Authenticate using your biometric
   - Passkey verification completes

3. **OAuth Redirect:**
   - After verification, redirect to Google OAuth
   - Complete Google authorization
   - YouTube authentication configured

## API Endpoints

### Passkey Registration

**Start Registration:**
```
POST /api/auth/youtube/oauth/passkey/register
Content-Type: application/json

{
  "username": "youtube_user"
}
```

**Verify Registration:**
```
POST /api/auth/youtube/oauth/passkey/register/verify
Content-Type: application/json

{
  "challenge": "base64url_challenge",
  "credential": {
    "id": "credential_id",
    "rawId": "base64url_raw_id",
    "response": {
      "clientDataJSON": "base64url_client_data",
      "attestationObject": "base64url_attestation"
    },
    "type": "public-key"
  }
}
```

### Passkey Authentication

**Start Authentication:**
```
POST /api/auth/youtube/oauth/passkey/authenticate
Content-Type: application/json

{
  "username": "youtube_user"  // Optional
}
```

**Verify Authentication:**
```
POST /api/auth/youtube/oauth/passkey/authenticate/verify
Content-Type: application/json

{
  "challenge": "base64url_challenge",
  "credential": {
    "id": "credential_id",
    "rawId": "base64url_raw_id",
    "response": {
      "clientDataJSON": "base64url_client_data",
      "authenticatorData": "base64url_authenticator_data",
      "signature": "base64url_signature",
      "userHandle": "base64url_user_handle"  // Optional
    },
    "type": "public-key"
  }
}
```

## Technical Details

### WebAuthn Implementation

StreamTV uses the `webauthn` Python library for Passkey support:

- **Registration**: `generate_registration_options()` and `verify_registration_response()`
- **Authentication**: `generate_authentication_options()` and `verify_authentication_response()`
- **Credential Storage**: JSON file with base64url-encoded public keys

### Challenge Management

- Challenges are stored temporarily (5-minute expiration)
- State tokens prevent CSRF attacks
- Challenges are base64url encoded for transmission

### Credential Storage

- **Location**: `data/passkeys.json`
- **Format**: JSON with username, credential ID, public key, sign count
- **Security**: File should have restricted permissions (chmod 600)

## Browser Compatibility

### Full Passkey Support (Apple)
- **Safari 16+** on macOS/iOS
- Native Passkey UI
- iCloud Keychain sync
- Face ID/Touch ID integration

### WebAuthn Support
- **Chrome 108+** (macOS/Windows)
- **Edge 108+** (macOS/Windows)
- Uses platform authenticators
- May require additional setup

### Not Supported
- Older browsers without WebAuthn
- Browsers without platform authenticators

## Troubleshooting

### Passkey Registration Fails

**Symptoms**: "Registration verification failed"

**Solutions:**
1. Ensure browser supports WebAuthn
2. Check device has biometric authentication enabled
3. Verify iCloud Keychain is enabled (for Safari)
4. Check browser console for errors
5. Ensure HTTPS or localhost (WebAuthn requirement)

### Passkey Authentication Fails

**Symptoms**: "Authentication verification failed"

**Solutions:**
1. Verify Passkey is registered
2. Check credential ID matches stored credential
3. Ensure challenge hasn't expired (5 minutes)
4. Verify origin matches RP ID
5. Check browser console for errors

### WebAuthn Not Available

**Symptoms**: "Passkey support not available"

**Solutions:**
1. Install webauthn library: `pip install webauthn`
2. Restart StreamTV server
3. Check logs for import errors

### Browser Doesn't Support Passkeys

**Symptoms**: "WebAuthn Not Supported" message

**Solutions:**
1. Use Safari 16+ on macOS/iOS
2. Use Chrome 108+ or Edge 108+
3. Enable platform authenticators in browser settings
4. Use HTTPS (required for WebAuthn on non-localhost)

## Security Considerations

### Best Practices

1. **Use HTTPS in Production**
   - WebAuthn requires secure context (HTTPS or localhost)
   - Passkeys won't work over HTTP on remote servers

2. **Restrict File Permissions**
   ```bash
   chmod 600 data/passkeys.json
   ```

3. **Backup Credentials**
   - Passkeys are stored in `data/passkeys.json`
   - Backup this file for credential recovery
   - Keep backups secure

4. **RP ID Configuration**
   - Use exact domain name for RP ID
   - Don't use IP addresses (not supported)
   - Match the domain users access StreamTV from

### Limitations

- **Localhost Only**: Default configuration works on localhost
- **Single Device**: Each Passkey is device-specific
- **No Recovery**: Lost device = lost Passkey (unless synced via iCloud)
- **Browser Dependent**: Requires modern browser with WebAuthn support

## Integration with YouTube OAuth

The Passkey flow is integrated into YouTube OAuth:

1. **User clicks "Start OAuth with Passkey"**
2. **System checks for Passkey**
   - If registered: Proceed to authentication
   - If not: Show registration option
3. **Passkey Authentication**
   - User authenticates with Face ID/Touch ID
   - System verifies Passkey
4. **OAuth Redirect**
   - After Passkey verification, redirect to Google OAuth
   - User authorizes YouTube access
   - Tokens stored securely

## Related Documentation

- [Authentication System](./AUTHENTICATION_SYSTEM.md) - Complete authentication guide
- [Apple Passkeys Documentation](https://developer.apple.com/documentation/AuthenticationServices/connecting-to-a-service-with-passkeys) - Official Apple documentation
- [WebAuthn Specification](https://www.w3.org/TR/webauthn-2/) - W3C WebAuthn standard

---

*Last Updated: 2025-01-28*

