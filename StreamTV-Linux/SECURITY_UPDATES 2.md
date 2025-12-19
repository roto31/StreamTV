# StreamTV Security Updates

**Date:** 2024  
**Version:** Security Hardening Release  
**Status:** ✅ Implemented

## Overview

This document outlines the comprehensive security improvements implemented across the StreamTV platform to address critical vulnerabilities and enhance overall security posture.

---

## Critical Security Fixes

### 1. API Key Authentication Improvements

**Issue:** Query parameter token support exposed API keys in URLs, browser history, and server logs.

**Fix:**
- Removed query parameter token support by default (`allow_query_param=False`)
- API keys now only accepted via secure headers:
  - `Authorization: Bearer <token>` (preferred)
  - `X-API-Key: <token>` (preferred)
- Added warning logs when query parameters are used (if explicitly enabled)
- Improved token extraction logic with better security practices

**Files Modified:**
- `streamtv/middleware/security.py` - `APIKeyMiddleware` class
- `streamtv/main.py` - Middleware configuration

**Impact:** Prevents API key exposure in URLs, logs, and browser history.

---

### 2. Content Security Policy (CSP) Hardening

**Issue:** CSP allowed `'unsafe-inline'` for scripts, reducing XSS protection.

**Fix:**
- Removed `'unsafe-inline'` from `script-src` directive
- Implemented CSP nonce support for inline scripts
- Added additional CSP directives:
  - `base-uri 'self'` - Prevents base tag injection
  - `form-action 'self'` - Prevents form action hijacking
- Maintained `'unsafe-inline'` for styles (required for dynamic styling)
- Added HSTS header for HTTPS connections

**Files Modified:**
- `streamtv/middleware/security.py` - `SecurityHeadersMiddleware` class

**Impact:** Significantly improved XSS protection while maintaining functionality.

---

### 3. CSRF Protection Implementation

**Issue:** No CSRF protection for form submissions, allowing cross-site request forgery attacks.

**Fix:**
- Implemented `CSRFProtectionMiddleware` for all form submissions
- CSRF tokens generated and validated for POST/PUT/DELETE/PATCH requests
- Tokens stored in secure HttpOnly cookies with SameSite=Strict
- API endpoints exempted (use API key authentication instead)
- IPTV and documentation endpoints exempted for compatibility

**Files Modified:**
- `streamtv/middleware/security.py` - New `CSRFProtectionMiddleware` class
- `streamtv/main.py` - Middleware registration

**Impact:** Prevents CSRF attacks on web forms and user actions.

---

### 4. Enhanced File Upload Security

**Issue:** Basic file upload validation allowed potential security risks.

**Fix:**
- Comprehensive file validation before processing:
  - Filename validation (extension, path traversal prevention)
  - File size limits (5 MB maximum)
  - MIME type detection and validation
  - YAML syntax validation with safe loader
  - Detection of unsafe YAML tags (`!!python`, `!!python/object`)
  - UTF-8 encoding validation
- Chunked file reading to prevent memory exhaustion
- Secure file deletion (overwrite before deletion)
- Enhanced error logging and security warnings

**Files Modified:**
- `streamtv/api/import_api.py` - File upload endpoints

**Impact:** Prevents malicious file uploads, code injection, and resource exhaustion attacks.

---

### 5. Configuration Security Enhancements

**Issue:** Sensitive credentials stored in plain text in `config.yaml` files.

**Fix:**
- Added environment variable support for sensitive values:
  - `STREAMTV_SECURITY_ACCESS_TOKEN` - API access token
  - `STREAMTV_PLEX_TOKEN` - Plex authentication token
  - `STREAMTV_YOUTUBE_API_KEY` - YouTube API key
  - `STREAMTV_YOUTUBE_OAUTH_CLIENT_ID` - OAuth client ID
  - `STREAMTV_YOUTUBE_OAUTH_CLIENT_SECRET` - OAuth client secret
  - `STREAMTV_YOUTUBE_OAUTH_REFRESH_TOKEN` - OAuth refresh token
  - `STREAMTV_METADATA_TVDB_API_KEY` - TVDB API key
  - `STREAMTV_METADATA_TVDB_READ_TOKEN` - TVDB read token
  - `STREAMTV_METADATA_TMDB_API_KEY` - TMDB API key
- Environment variables take precedence over YAML values
- Added configuration class improvements for better security

**Files Modified:**
- `streamtv/config.py` - Configuration classes and initialization

**Impact:** Allows secure credential management without exposing secrets in configuration files.

---

## Security Middleware Stack

The platform now includes a comprehensive security middleware stack:

1. **CORS Middleware** - Restricts cross-origin requests
2. **Security Headers Middleware** - Adds CSP, HSTS, and other security headers
3. **CSRF Protection Middleware** - Protects against cross-site request forgery
4. **API Key Middleware** - Enforces API key authentication

**Middleware Order:**
```
CORS → Security Headers → CSRF Protection → API Key Auth → Routes
```

---

## Security Headers Implemented

The following security headers are now included in all responses:

- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking
- `Referrer-Policy: no-referrer` - Controls referrer information
- `Permissions-Policy` - Restricts browser features
- `Cross-Origin-Opener-Policy: same-origin` - Isolates browsing context
- `Cross-Origin-Resource-Policy: same-origin` - Prevents cross-origin reads
- `Content-Security-Policy` - Comprehensive CSP with nonce support
- `Strict-Transport-Security` - HSTS for HTTPS (when enabled)

---

## API Key Configuration

### Current Configuration

The platform requires API key authentication by default. To configure:

**Option 1: Environment Variable (Recommended)**
```bash
export STREAMTV_SECURITY_ACCESS_TOKEN="your-secure-token-here"
```

**Option 2: config.yaml**
```yaml
security:
  api_key_required: true
  access_token: "your-secure-token-here"
```

### Generating Secure Tokens

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Using API Keys

**Header Method (Preferred):**
```bash
curl -H "Authorization: Bearer your-token" http://localhost:8410/api/channels
curl -H "X-API-Key: your-token" http://localhost:8410/api/channels
```

**Note:** Query parameter support (`?access_token=...`) is disabled by default for security.

---

## File Upload Security

### Validation Checks

All file uploads are validated for:

1. **File Extension** - Must be `.yaml` or `.yml`
2. **File Size** - Maximum 5 MB
3. **Path Traversal** - Filenames cannot contain `..`, `/`, or `\`
4. **MIME Type** - Validated against allowed types
5. **YAML Syntax** - Valid YAML syntax required
6. **Unsafe Tags** - Blocks `!!python` and `!!python/object` tags
7. **Encoding** - Must be UTF-8

### Secure File Handling

- Files read in chunks to prevent memory exhaustion
- Temporary files overwritten before deletion
- Comprehensive error logging for security monitoring

---

## CSRF Protection

### How It Works

1. Server generates CSRF token on first request
2. Token stored in secure HttpOnly cookie
3. Token must be included in subsequent POST/PUT/DELETE requests
4. Token validated against cookie value

### Exempt Endpoints

The following endpoints are exempt from CSRF protection:

- `/api/*` - API endpoints (use API key authentication)
- `/iptv/*` - IPTV endpoints
- `/docs`, `/redoc`, `/openapi.json` - API documentation

### Using CSRF Tokens

**JavaScript Example:**
```javascript
// Get CSRF token from cookie
const csrfToken = document.cookie
  .split('; ')
  .find(row => row.startsWith('csrf_token='))
  ?.split('=')[1];

// Include in request
fetch('/api/endpoint', {
  method: 'POST',
  headers: {
    'X-CSRF-Token': csrfToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
});
```

---

## Environment Variables

### Security-Related Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `STREAMTV_SECURITY_ACCESS_TOKEN` | API access token | `your-token-here` |
| `STREAMTV_PLEX_TOKEN` | Plex authentication token | `plex-token` |
| `STREAMTV_YOUTUBE_API_KEY` | YouTube Data API key | `api-key` |
| `STREAMTV_YOUTUBE_OAUTH_CLIENT_ID` | OAuth client ID | `client-id` |
| `STREAMTV_YOUTUBE_OAUTH_CLIENT_SECRET` | OAuth client secret | `client-secret` |
| `STREAMTV_YOUTUBE_OAUTH_REFRESH_TOKEN` | OAuth refresh token | `refresh-token` |
| `STREAMTV_METADATA_TVDB_API_KEY` | TVDB API key | `tvdb-key` |
| `STREAMTV_METADATA_TVDB_READ_TOKEN` | TVDB read token | `tvdb-token` |
| `STREAMTV_METADATA_TMDB_API_KEY` | TMDB API key | `tmdb-key` |

### Setting Environment Variables

**Linux/macOS:**
```bash
export STREAMTV_SECURITY_ACCESS_TOKEN="your-token"
```

**Windows (PowerShell):**
```powershell
$env:STREAMTV_SECURITY_ACCESS_TOKEN="your-token"
```

**Windows (CMD):**
```cmd
set STREAMTV_SECURITY_ACCESS_TOKEN=your-token
```

---

## Migration Guide

### For Existing Installations

1. **Generate API Token:**
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update Configuration:**
   - Set `security.access_token` in `config.yaml`, OR
   - Set `STREAMTV_SECURITY_ACCESS_TOKEN` environment variable

3. **Update API Clients:**
   - Remove query parameter tokens (`?access_token=...`)
   - Use header-based authentication (`Authorization: Bearer <token>` or `X-API-Key: <token>`)

4. **Test Authentication:**
   ```bash
   curl -H "Authorization: Bearer your-token" http://localhost:8410/api/health/detailed
   ```

5. **Restart Server:**
   ```bash
   # Stop existing server
   # Start with updated configuration
   ```

---

## Security Best Practices

### Recommended Practices

1. **Use Environment Variables** - Store sensitive credentials in environment variables, not config files
2. **Rotate Tokens Regularly** - Change API tokens periodically
3. **Use HTTPS in Production** - Enable HTTPS/TLS for production deployments
4. **Restrict File Permissions** - Set `chmod 600` on `config.yaml` if used
5. **Monitor Logs** - Review security warnings in logs regularly
6. **Keep Dependencies Updated** - Regularly update Python packages
7. **Use Strong Tokens** - Generate tokens with at least 32 characters
8. **Limit API Access** - Use firewall rules to restrict API access

### Production Deployment Checklist

- [ ] API key authentication enabled
- [ ] Secure API token generated and configured
- [ ] Environment variables set for sensitive data
- [ ] HTTPS/TLS enabled (reverse proxy recommended)
- [ ] File permissions restricted on config files
- [ ] Firewall rules configured
- [ ] Logging enabled and monitored
- [ ] Regular security updates scheduled

---

## Testing Security Features

### Test API Key Authentication

```bash
# Should fail without token
curl -X POST http://localhost:8410/api/channels

# Should succeed with token
curl -X POST \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  http://localhost:8410/api/channels
```

### Test CSRF Protection

```bash
# Should fail without CSRF token
curl -X POST http://localhost:8410/some-form-endpoint

# Should succeed with CSRF token
curl -X POST \
  -H "X-CSRF-Token: token-from-cookie" \
  -H "Cookie: csrf_token=token-from-cookie" \
  http://localhost:8410/some-form-endpoint
```

### Test File Upload Security

```bash
# Should fail - invalid extension
curl -X POST \
  -F "file=@malicious.exe" \
  http://localhost:8410/api/import/channels/yaml

# Should fail - file too large
curl -X POST \
  -F "file=@huge-file.yaml" \
  http://localhost:8410/api/import/channels/yaml
```

---

## Known Limitations

1. **CSP Nonces** - Some legacy inline scripts may need refactoring to use nonces
2. **CSRF Tokens** - Simplified implementation; full session management recommended for production
3. **File Upload** - `python-magic` library optional; MIME type detection may be skipped if not installed
4. **HTTPS** - Not enforced by application; use reverse proxy (nginx, Caddy) for HTTPS

---

## Security Contact

For security issues or concerns, please review the security policy in `SECURITY.md`.

---

## Changelog

### 2024 - Security Hardening Release

- ✅ Removed query parameter API key support
- ✅ Implemented CSP with nonce support
- ✅ Added CSRF protection middleware
- ✅ Enhanced file upload validation
- ✅ Added environment variable support for credentials
- ✅ Improved security headers
- ✅ Added HSTS support
- ✅ Enhanced error logging and security warnings

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [CSRF Protection](https://owasp.org/www-community/attacks/csrf)
