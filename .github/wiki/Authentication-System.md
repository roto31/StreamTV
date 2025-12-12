# Authentication System

Advanced authentication features for StreamTV.

## Overview

StreamTV supports multiple authentication methods to secure your installation:

- API Key Authentication
- Passkey Authentication
- Token-based Authentication

## API Key Authentication

### Enable API Key

Edit `config.yaml`:

```yaml
security:
  api_key_required: true
  access_token: "your-secure-token-here"
```

### Using API Key

**As Header:**
```bash
curl -H "Authorization: Bearer your-token" http://localhost:8410/api/channels
```

**As Query Parameter:**
```bash
curl "http://localhost:8410/api/channels?access_token=your-token"
```

**In IPTV URLs:**
```
http://localhost:8410/iptv/channels.m3u?access_token=your-token
```

## Passkey Authentication

StreamTV supports WebAuthn passkey authentication for enhanced security.

### Setup

1. **Enable passkey authentication** in configuration
2. **Register passkeys** through the web interface
3. **Use passkeys** for secure access

### Documentation

See [Passkey Authentication](../docs/PASSKEY_AUTHENTICATION.md) for complete setup instructions.

## Token Management

### Generate Secure Token

```bash
# Generate random token
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Rotate Tokens

1. Generate new token
2. Update `config.yaml`
3. Restart StreamTV
4. Update all clients with new token

## Security Best Practices

1. **Use Strong Tokens**
   - Minimum 32 characters
   - Random and unpredictable
   - Store securely

2. **HTTPS in Production**
   - Use reverse proxy (nginx, Apache)
   - Enable SSL/TLS
   - Protect token transmission

3. **Token Rotation**
   - Rotate tokens regularly
   - Revoke compromised tokens immediately
   - Use different tokens for different clients

4. **Access Control**
   - Limit token scope if possible
   - Monitor token usage
   - Log authentication attempts

## Configuration

### Full Security Configuration

```yaml
security:
  api_key_required: true
  access_token: "your-secure-token"
  cors_enabled: true
  cors_origins:
    - "https://yourdomain.com"
    - "http://localhost:3000"
  passkey_enabled: true
  session_timeout: 3600  # seconds
```

## Troubleshooting

### Token Not Working

- Verify token in `config.yaml`
- Check token is included in request
- Verify `api_key_required` is enabled
- Check token hasn't expired

### CORS Issues

- Add origin to `cors_origins`
- Verify `cors_enabled` is true
- Check browser console for errors

### Passkey Issues

- Verify passkey is registered
- Check browser supports WebAuthn
- Review passkey authentication logs

## Related Documentation

- [Authentication](../docs/AUTHENTICATION.md) - Basic authentication
- [Passkey Authentication](../docs/PASSKEY_AUTHENTICATION.md) - Passkey setup
- [API Security](API-Security) - Securing API endpoints
- [Access Control](Access-Control) - Managing access

