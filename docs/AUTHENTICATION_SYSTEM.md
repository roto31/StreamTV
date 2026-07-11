# Authentication System Documentation

StreamTV includes comprehensive authentication support for both Archive.org and YouTube using a web-based interface.

## Overview

The authentication system provides:
- **Web interface login pages** for both services
- **Automatic credential storage** in macOS Keychain (Archive.org)
- **Automatic re-authentication** when sessions expire
- **Secure credential management** with proper storage and handling

## Archive.org Authentication

### Web Interface Login

**Access:** Settings → Archive.org (in sidebar) or `/api/auth/archive-org`

**Features:**
- Login form with username and password fields
- Shows current authentication status
- Logout button to remove credentials
- Automatic credential storage in Keychain (on macOS)

### Automatic Re-authentication

- Checks authentication status on server startup
- Re-prompts via SwiftDialog if authentication fails
- Automatically re-authenticates when accessing restricted content
- Handles session expiration gracefully

### API Endpoints

- `GET /api/auth/archive-org` - Login page
- `POST /api/auth/archive-org` - Login with credentials
- `DELETE /api/auth/archive-org` - Logout
- `GET /api/auth/archive-org/status` - Check authentication status

## YouTube Authentication

### Web Interface Login

**Access:** Settings → YouTube (in sidebar) or `/api/auth/youtube`

**Features:**
- Upload cookies file (cookies.txt format)
- Shows current authentication status
- Instructions for exporting cookies
- Remove authentication button

### Cookie File Method

**How to Export Cookies:**
1. Install browser extension:
   - Chrome/Edge: "Get cookies.txt LOCALLY"
   - Firefox: "cookies.txt"
2. Visit youtube.com and login
3. Click extension icon
4. Export cookies to cookies.txt file
5. Upload file via web interface

**File Format:**
- Netscape cookies format
- Must contain YouTube cookies
- Stored in `data/cookies/youtube_cookies.txt`

### API Endpoints

- `GET /api/auth/youtube` - Login page
- `POST /api/auth/youtube/cookies` - Upload cookies file
- `GET /api/auth/youtube/status` - Check authentication status
- `DELETE /api/auth/youtube` - Remove authentication

## Configuration

### Archive.org Config

```yaml
archive_org:
  enabled: true
  preferred_format: "h264"
  username: "your_username"  # Set via login
  password: "your_password"   # Set via login
  use_authentication: true     # Enabled after login
```

### YouTube Config

```yaml
youtube:
  enabled: true
  quality: "best"
  extract_audio: false
  cookies_file: "data/cookies/youtube_cookies.txt"  # Set via login
  use_authentication: true  # Enabled after login
```

## Security

### Credential Storage

**Archive.org:**
- macOS: Stored in macOS Keychain (secure)
- Other platforms: Stored in config.yaml (encrypted recommended)

**YouTube:**
- Cookies file stored in `data/cookies/` directory
- File permissions should be restricted (chmod 600)

### Best Practices

1. **Never commit credentials** - config.yaml is in .gitignore
2. **Restrict file permissions** - Use `chmod 600` for config.yaml and cookies files
3. **Use Keychain on macOS** - Automatic secure storage
4. **Rotate credentials** - Change passwords periodically
5. **Monitor authentication** - Check logs for authentication failures

## Troubleshooting

### Archive.org Login Fails

**Symptoms:** "Invalid credentials" or "Login failed"

**Solutions:**
1. Verify username and password are correct
2. Check Archive.org account is active
3. Try logging in via web interface
4. Check network connectivity
5. Review logs for detailed error messages

### YouTube Cookies Not Working

**Symptoms:** "Authentication required" or "Access denied"

**Solutions:**
1. Verify cookies file is valid Netscape format
2. Ensure cookies file contains YouTube cookies
3. Re-export cookies after logging into YouTube
4. Check cookies file path is correct
5. Verify file permissions allow reading

### Authentication Expires

**Symptoms:** Works initially, then fails

**Solutions:**
1. Use web interface to re-login
3. Check if credentials are still valid
4. Archive.org sessions may expire - re-authentication is automatic

## Usage Examples

### Login via Web Interface

1. **Archive.org:**
   - Go to Settings → Archive.org
   - Enter username and password
   - Click "Login"
   - Credentials stored automatically

2. **YouTube:**
   - Go to Settings → YouTube
   - Export cookies from browser
   - Upload cookies.txt file
   - Authentication configured automatically

### Check Authentication Status

```bash
# Archive.org status
curl http://localhost:8410/api/auth/archive-org/status

# YouTube status
curl http://localhost:8410/api/auth/youtube/status
```

### Logout

```bash
# Archive.org logout
curl -X DELETE http://localhost:8410/api/auth/archive-org

# YouTube logout
curl -X DELETE http://localhost:8410/api/auth/youtube
```

## Implementation Details

### Authentication Checker

**File:** `streamtv/utils/auth_checker.py`

**Function:**
- `check_and_renew_archive_org_auth()` - Check and re-prompt if needed

### API Endpoints

**File:** `streamtv/api/auth.py`

**Endpoints:**
- Archive.org login/logout/status
- YouTube cookies upload/status/remove
- Web interface pages

### Adapter Updates

**Archive.org Adapter:**
- Automatic re-authentication on 403/401 errors
- Session cookie management
- Authentication status checking

**YouTube Adapter:**
- Cookies file support via yt-dlp
- Automatic cookie usage for authenticated requests

## Apple Passkey Integration

StreamTV includes Apple Passkey (WebAuthn) support for enhanced security when authenticating with YouTube OAuth.

### Features

- **Biometric Authentication**: Use Face ID or Touch ID
- **Passwordless**: No passwords required
- **Secure**: Public-key cryptography, phishing-resistant
- **Integrated**: Works seamlessly with YouTube OAuth flow

### Usage

1. Navigate to Settings → YouTube
2. Click "Start OAuth with Passkey"
3. Register a Passkey (first time) or authenticate with existing Passkey
4. After Passkey verification, proceed to Google OAuth

See [Passkey Authentication Documentation](./PASSKEY_AUTHENTICATION.md) for complete details.

## Related Documentation

- [Passkey Authentication](./PASSKEY_AUTHENTICATION.md) - Complete Passkey guide
- [Beginner Guide](./BEGINNER_GUIDE.md) - Basic usage
- [Intermediate Guide](./INTERMEDIATE_GUIDE.md) - Configuration details
- [Expert Guide](./EXPERT_GUIDE.md) - Implementation details
- [Troubleshooting Scripts](./TROUBLESHOOTING_SCRIPTS.md) - Automated troubleshooting

---

*Last Updated: 2025-01-28*

