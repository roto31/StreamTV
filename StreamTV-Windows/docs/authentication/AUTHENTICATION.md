# Archive.org Authentication Guide

StreamTV supports authentication with Archive.org to access restricted content that requires a login.

## Configuration

To enable Archive.org authentication, edit your `config.yaml`:

```yaml
archive_org:
  enabled: true
  preferred_format: "h264"
  username: "your_username"  # Your Archive.org username
  password: "your_password"   # Your Archive.org password
  use_authentication: true    # Enable authentication
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit credentials**: Make sure `config.yaml` is in `.gitignore` (it already is)
2. **Use environment variables**: For production, consider using environment variables instead of storing passwords in config files
3. **File permissions**: Ensure `config.yaml` has restricted permissions (e.g., `chmod 600 config.yaml`)

## How It Works

1. **Initial Login**: When authentication is enabled, StreamTV will automatically log in to Archive.org on first use
2. **Session Management**: The adapter maintains session cookies for authenticated requests
3. **Automatic Re-authentication**: If a session expires, StreamTV will automatically attempt to re-authenticate
4. **Transparent Usage**: Once configured, authentication works transparently - all Archive.org requests will use authenticated sessions

## Testing Authentication

You can test if authentication is working by:

1. Adding a restricted Archive.org item:
```bash
curl -X POST http://localhost:8410/api/media \
  -H "Content-Type: application/json" \
  -d '{
    "source": "archive_org",
    "url": "https://archive.org/details/RESTRICTED_ITEM_IDENTIFIER"
  }'
```

2. If authentication is working, you should be able to access the item. If not, you'll get a permission error.

## Troubleshooting

### Login Fails

**Symptoms**: Logs show "Archive.org login failed" or "Invalid credentials"

**Solutions**:
- Verify your username and password are correct
- Check that `use_authentication` is set to `true`
- Ensure Archive.org account is active and not locked
- Check network connectivity to Archive.org

### Session Expires

**Symptoms**: Initially works, then starts getting 403 errors

**Solutions**:
- StreamTV should automatically re-authenticate, but if issues persist:
- Restart the StreamTV server
- Verify credentials are still valid
- Check Archive.org service status

### Access Denied Errors

**Symptoms**: Getting 403 or PermissionError even with authentication

**Solutions**:
- Verify the item actually requires authentication (some items may be completely restricted)
- Check that your Archive.org account has access to the item
- Some items may require special permissions or membership

## Environment Variables (Alternative)

Instead of storing credentials in `config.yaml`, you can use environment variables:

```bash
export ARCHIVE_ORG_USERNAME="your_username"
export ARCHIVE_ORG_PASSWORD="your_password"
```

Then update your config to read from environment:

```python
# In config.py (would need modification)
username: os.getenv("ARCHIVE_ORG_USERNAME")
password: os.getenv("ARCHIVE_ORG_PASSWORD")
```

## Disabling Authentication

To disable authentication:

```yaml
archive_org:
  use_authentication: false
```

Or simply remove/comment out the username and password fields.

## Logs

Authentication events are logged at INFO level:
- Successful authentication: "Successfully authenticated with Archive.org"
- Failed authentication: "Archive.org login failed: Invalid credentials"
- Session expiration: "Archive.org session expired, re-authenticating..."

Check your logs (default: `streamtv.log` or console output) for authentication status.
