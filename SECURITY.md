# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Which versions are eligible for receiving such patches depends on the CVSS v3.0 Rating:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

Please report (suspected) security vulnerabilities via the messaging platform on github. You will receive a response within 48 hours. If the issue is confirmed, we will release a patch as soon as possible depending on complexity but historically within a few days.

### Reporting Process

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email the security team with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Include

- Type of vulnerability (e.g., XSS, CSRF, SQL injection)
- Full paths of source file(s) related to the vulnerability
- Location of the affected code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

## Security Best Practices

### For Users

- Keep StreamTV updated to the latest version
- Use strong authentication when available
- Run StreamTV behind a firewall when possible
- Review and restrict API access
- Use HTTPS when exposing StreamTV to the internet
- Regularly review logs for suspicious activity

### For Developers

- Follow secure coding practices
- Review dependencies for known vulnerabilities
- Use parameterized queries (SQLAlchemy handles this)
- Validate and sanitize all user input
- Keep dependencies updated
- Review authentication and authorization logic

## Security Updates

Security updates will be:
- Released as patch versions (e.g., 1.0.1, 1.0.2)
- Documented in CHANGELOG.md
- Announced in GitHub releases
- Backported to supported versions

## Known Security Considerations

### Authentication
- OAuth tokens are stored securely
- Passkeys use WebAuthn standards
- API tokens should be kept secret

### Network
- StreamTV listens on localhost by default
- Exposing to the internet requires proper security measures
- Use reverse proxy with SSL/TLS for production

### Dependencies
- Regular dependency updates are recommended
- Known vulnerabilities are addressed promptly

## Disclosure Policy

When we receive a security bug report, we will:

1. Confirm the issue and determine affected versions
2. Audit code to find any potential similar problems
3. Prepare fixes for all releases still under support
4. Publish a security advisory and release patches

We credit security researchers who responsibly disclose vulnerabilities.

## Security Contact

For security concerns, please contact: **[security@example.com]**

*(Replace with your actual security contact email)*
