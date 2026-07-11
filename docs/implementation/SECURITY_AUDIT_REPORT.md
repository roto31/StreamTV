# Security Audit Report - StreamTV

**Date:** 2025-01-27
**Auditor:** AI Security Analysis
**Reference Guide:** [Palo Alto Networks Application Security Guide](https://www.paloaltonetworks.com/cyberpedia/application-security)

## Executive Summary

This security audit was conducted to verify the security posture of the StreamTV application according to application security best practices. The audit identified **1 CRITICAL**, **2 HIGH**, **4 MEDIUM**, and **3 LOW** severity security issues that require attention.

### Risk Summary
- **CRITICAL:** 1 issue
- **HIGH:** 2 issues
- **MEDIUM:** 4 issues
- **LOW:** 3 issues

---

## CRITICAL Issues

### 1. Plaintext Credentials in Configuration File ⚠️ CRITICAL

**Location:** `config.yaml` (lines 22-23)

**Issue:**
```yaml
archive_org:
  username: roto31
  password: Airforc1
```

Plaintext credentials are stored in the configuration file, which poses a severe security risk if the file is:
- Committed to version control
- Accessed by unauthorized users
- Exposed through file system permissions
- Logged or backed up

**Impact:**
- Complete compromise of Archive.org account
- Potential access to user's personal data
- Violation of security best practices

**Recommendation:**
1. **IMMEDIATE ACTION:** Remove credentials from `config.yaml` immediately
2. Use macOS Keychain for credential storage (already implemented but not being used)
3. Ensure `config.yaml` is in `.gitignore` (✅ Already configured)
4. Set proper file permissions: `chmod 600 config.yaml`
5. For non-macOS platforms, use encrypted configuration or environment variables

**Code Reference:**
- `streamtv/utils/macos_credentials.py` - Keychain storage is available
- `streamtv/api/auth.py` - Credentials should be stored in Keychain on macOS

---

## HIGH Severity Issues

### 2. Overly Permissive CORS Configuration ⚠️ HIGH

**Location:** `streamtv/main.py` (lines 93-99)

**Issue:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact:**
- Any website can make requests to the API
- Enables Cross-Site Request Forgery (CSRF) attacks
- Allows unauthorized access from malicious websites
- Combined with `allow_credentials=True`, this is particularly dangerous

**Recommendation:**
1. Restrict `allow_origins` to specific trusted domains
2. Remove wildcard (`*`) when `allow_credentials=True`
3. Use environment-based configuration:
   ```python
   allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:8410").split(",")
   app.add_middleware(
       CORSMiddleware,
       allow_origins=allowed_origins,
       allow_credentials=True,
       allow_methods=["GET", "POST", "PUT", "DELETE"],
       allow_headers=["Content-Type", "Authorization"],
   )
   ```

### 3. Optional API Key Authentication ⚠️ HIGH

**Location:** `config.yaml` (line 25)

**Issue:**
```yaml
security:
  api_key_required: false  # ⚠️ Authentication disabled by default
  access_token: null
```

**Impact:**
- API endpoints are publicly accessible without authentication
- No protection against unauthorized access
- Sensitive operations (channel management, media import) are unprotected

**Recommendation:**
1. Enable API key authentication by default in production
2. Require authentication for all write operations (POST, PUT, DELETE)
3. Implement role-based access control (RBAC) if needed
4. Add authentication middleware to protect sensitive endpoints

**Code Reference:**
- Authentication check should be implemented in `streamtv/api/` endpoints
- See `.github/wiki/Authentication-System.md` for implementation details

---

## MEDIUM Severity Issues

### 4. Information Disclosure in Error Messages ⚠️ MEDIUM

**Location:** Multiple files in `streamtv/api/`

**Issue:**
Error messages expose internal details:
```python
raise HTTPException(status_code=500, detail=str(e))  # Exposes full exception
```

**Examples Found:**
- `streamtv/api/auth.py:109` - `detail=str(e)`
- `streamtv/api/auth.py:198` - `detail=str(e)`
- `streamtv/api/import_api.py:69` - `detail=f"Error importing channels: {str(e)}"`

**Impact:**
- Reveals internal system structure
- May expose file paths, database structure, or implementation details
- Aids attackers in crafting targeted attacks

**Recommendation:**
1. Use generic error messages in production:
   ```python
   logger.error(f"Error: {e}", exc_info=True)  # Log full details
   raise HTTPException(status_code=500, detail="An internal error occurred")
   ```
2. Only show detailed errors in development/debug mode
3. Sanitize error messages before returning to clients

### 5. Insufficient File Upload Validation ⚠️ MEDIUM

**Location:** `streamtv/api/auth.py:157-198`, `streamtv/api/import_api.py:20-75`

**Issue:**
File uploads have minimal validation:
- Only checks file extension (`.yaml`, `.yml`)
- Basic content validation for cookies file
- No file size limits
- No MIME type verification
- No virus/malware scanning

**Impact:**
- Potential for malicious file uploads
- DoS attacks through large file uploads
- Path traversal vulnerabilities if file paths are used unsafely

**Recommendation:**
1. Implement file size limits:
   ```python
   MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
   if file.size > MAX_FILE_SIZE:
       raise HTTPException(400, "File too large")
   ```
2. Verify MIME types, not just extensions
3. Sanitize file names to prevent path traversal
4. Store uploaded files outside web root
5. Scan files for malicious content if possible

### 6. No Rate Limiting ⚠️ MEDIUM

**Location:** Application-wide

**Issue:**
No rate limiting implemented on API endpoints, allowing:
- Brute force attacks on authentication endpoints
- DoS attacks through excessive requests
- Resource exhaustion

**Impact:**
- Account enumeration
- Brute force credential attacks
- Service unavailability

**Recommendation:**
1. Implement rate limiting middleware:
   ```python
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
   ```
2. Set appropriate limits:
   - Authentication endpoints: 5 requests/minute
   - General API: 100 requests/minute
   - File uploads: 10 requests/hour

### 7. Missing HTTPS/TLS Enforcement ⚠️ MEDIUM

**Location:** `streamtv/main.py`, `config.yaml`

**Issue:**
- No HTTPS/TLS enforcement
- Default configuration uses HTTP (`base_url: http://localhost:8410`)
- No redirect from HTTP to HTTPS
- Credentials transmitted in plaintext over network

**Impact:**
- Man-in-the-middle attacks
- Credential interception
- Session hijacking

**Recommendation:**
1. Use HTTPS in production (reverse proxy with nginx/Apache)
2. Add HTTPS enforcement middleware
3. Use secure cookies if implementing session management
4. Update `base_url` to use `https://` in production

---

## LOW Severity Issues

### 8. Hardcoded RP ID for WebAuthn ⚠️ LOW

**Location:** `streamtv/api/auth.py:29`

**Issue:**
```python
rp_id = "localhost"  # Hardcoded, should use config
```

**Impact:**
- WebAuthn may not work correctly in production
- Limited to localhost usage

**Recommendation:**
```python
rp_id = config.server.host if config.server.host != "0.0.0.0" else "localhost"
# Or better: use actual domain from config
rp_id = config.server.base_url.replace("http://", "").replace("https://", "").split("/")[0]
```

### 9. No Input Size Limits on Request Bodies ⚠️ LOW

**Location:** Application-wide

**Issue:**
No explicit limits on request body sizes, which could lead to:
- Memory exhaustion
- DoS attacks

**Recommendation:**
1. Configure FastAPI request size limits
2. Set appropriate limits per endpoint type

### 10. Cookie File Path Validation ⚠️ LOW

**Location:** `streamtv/api/auth.py:176`

**Issue:**
Basic validation only checks for "youtube.com" or "# Netscape" in content, which is insufficient.

**Recommendation:**
1. Validate proper Netscape cookie file format
2. Verify cookie file structure
3. Check file permissions after upload

---

## Positive Security Findings ✅

### 1. SQL Injection Protection ✅
- Uses SQLAlchemy ORM with parameterized queries
- No raw SQL string concatenation found
- Proper use of ORM methods (`db.query()`, `.filter()`)

### 2. Secrets Management ✅
- macOS Keychain integration implemented
- `.gitignore` properly excludes `config.yaml`
- Passkey authentication support available

### 3. Input Validation ✅
- YAML schema validation implemented
- Pydantic models for request validation
- File extension validation (though could be improved)

### 4. Authentication Framework ✅
- Multiple authentication methods supported (API key, Passkey, OAuth)
- Token-based authentication available
- WebAuthn/Passkey implementation present

### 5. Dependency Management ✅
- Requirements file present (`requirements.txt`)
- Uses established libraries (FastAPI, SQLAlchemy, etc.)

---

## Recommendations Summary

### Immediate Actions (Critical/High)
1. **URGENT:** Remove plaintext credentials from `config.yaml` and use Keychain
2. Restrict CORS to specific origins
3. Enable API key authentication by default
4. Implement rate limiting on authentication endpoints

### Short-term (Medium Priority)
1. Sanitize error messages in production
2. Add file upload size limits and validation
3. Implement HTTPS/TLS in production
4. Add comprehensive file upload security checks

### Long-term (Low Priority)
1. Fix WebAuthn RP ID configuration
2. Add request body size limits
3. Improve cookie file validation
4. Implement comprehensive logging and monitoring
5. Add security headers (CSP, HSTS, X-Frame-Options, etc.)

---

## Compliance Checklist

Based on the [Palo Alto Networks Application Security Guide](https://www.paloaltonetworks.com/cyberpedia/application-security):

### ✅ Implemented
- [x] Secure coding practices (ORM usage)
- [x] Authentication mechanisms (multiple methods)
- [x] Secrets management (Keychain on macOS)
- [x] Input validation (Pydantic, schema validation)
- [x] Dependency management (requirements.txt)

### ❌ Needs Improvement
- [ ] HTTPS/TLS enforcement
- [ ] Rate limiting
- [ ] CORS configuration
- [ ] Error handling (information disclosure)
- [ ] File upload security
- [ ] Security headers
- [ ] Logging and monitoring
- [ ] Security testing in CI/CD

---

## Testing Recommendations

1. **Penetration Testing:**
   - Test authentication bypass attempts
   - Test file upload vulnerabilities
   - Test rate limiting effectiveness
   - Test CORS misconfiguration

2. **Security Scanning:**
   - Run dependency vulnerability scanner (e.g., `safety`, `pip-audit`)
   - Static code analysis (e.g., `bandit`, `semgrep`)
   - Dynamic application security testing (DAST)

3. **Code Review:**
   - Review all authentication flows
   - Review file upload handlers
   - Review error handling
   - Review configuration management

---

## Conclusion

The StreamTV application has a solid foundation with good security practices in some areas (SQL injection protection, authentication framework, secrets management). However, **critical issues** with plaintext credentials and **high-severity** CORS/authentication configuration issues must be addressed immediately.

The application would benefit from:
- Enhanced security configuration
- Production-ready security hardening
- Comprehensive security testing
- Security monitoring and logging

**Priority:** Address CRITICAL and HIGH issues before deploying to production.

---

## References

- [Palo Alto Networks Application Security Guide](https://www.paloaltonetworks.com/cyberpedia/application-security)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security.html)

---

**Report Generated:** 2025-01-27
**Next Review:** After critical issues are resolved
