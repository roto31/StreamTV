# Secrets Management Guide

This guide explains how to securely manage API keys, tokens, and other sensitive configuration values in StreamTV.

## Overview

StreamTV supports multiple methods for managing secrets, with environment variables being the recommended approach for production deployments.

## Security Best Practices

1. **Never commit secrets to version control**
   - Do not add `.env` files to git
   - Do not commit `config.yaml` with real secrets
   - Use `.env.example` as a template only

2. **Use environment variables for sensitive values**
   - Environment variables take precedence over config file values
   - They are not logged or exposed in error messages
   - They can be managed through platform-specific secure storage

3. **Rotate secrets regularly**
   - Change API keys and tokens periodically
   - Revoke old tokens when rotating
   - Monitor for unauthorized access

## Platform-Specific Secrets Management

### macOS - Keychain Access

Store secrets in macOS Keychain for secure, encrypted storage:

```bash
# Add a secret to Keychain
security add-generic-password \
  -a StreamTV \
  -s STREAMTV_SECURITY_ACCESS_TOKEN \
  -w "your-token-here" \
  -U

# Retrieve a secret from Keychain (for use in scripts)
security find-generic-password \
  -a StreamTV \
  -s STREAMTV_SECURITY_ACCESS_TOKEN \
  -w
```

**Using Keychain in Python:**
```python
import subprocess
import os

def get_keychain_password(service, account):
    """Retrieve password from macOS Keychain"""
    try:
        result = subprocess.run(
            ['security', 'find-generic-password', '-a', account, '-s', service, '-w'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

# Usage
token = get_keychain_password('STREAMTV_SECURITY_ACCESS_TOKEN', 'StreamTV')
if token:
    os.environ['STREAMTV_SECURITY_ACCESS_TOKEN'] = token
```

### Linux - Keyring

Use the `keyring` library for secure storage on Linux:

```bash
# Install keyring
pip install keyring

# Store a secret
python -m keyring set StreamTV STREAMTV_SECURITY_ACCESS_TOKEN
# Enter password when prompted

# Retrieve a secret
python -m keyring get StreamTV STREAMTV_SECURITY_ACCESS_TOKEN
```

**Using Keyring in Python:**
```python
import keyring
import os

# Store a secret
keyring.set_password('StreamTV', 'STREAMTV_SECURITY_ACCESS_TOKEN', 'your-token')

# Retrieve a secret
token = keyring.get_password('StreamTV', 'STREAMTV_SECURITY_ACCESS_TOKEN')
if token:
    os.environ['STREAMTV_SECURITY_ACCESS_TOKEN'] = token
```

```cmd
# Store a secret
cmdkey /add:StreamTV_STREAMTV_SECURITY_ACCESS_TOKEN /user:StreamTV /pass:your-token-here

# List credentials
cmdkey /list

# Delete a credential
cmdkey /delete:StreamTV_STREAMTV_SECURITY_ACCESS_TOKEN
```

**Using Credential Manager in Python:**
```python
import subprocess
import os

def get_windows_credential(target_name):
    try:
        result = subprocess.run(
            ['cmdkey', '/list', target_name],
            capture_output=True,
            text=True,
            check=True
        )
        # Parse the output to extract password
        # Note: cmdkey doesn't directly return passwords for security
        # You may need to use win32cred module instead
        return None
    except subprocess.CalledProcessError:
        return None

# Better approach: Use win32cred module
try:
    import win32cred
    import win32con

    def get_credential(target_name):
        try:
            credential = win32cred.CredRead(target_name, win32cred.CRED_TYPE_GENERIC, 0)
            return credential['CredentialBlob'].decode('utf-16le')
        except Exception:
            return None

    token = get_credential('StreamTV_STREAMTV_SECURITY_ACCESS_TOKEN')
    if token:
        os.environ['STREAMTV_SECURITY_ACCESS_TOKEN'] = token
except ImportError:
```

## Environment Variables

### Setting Environment Variables

**Linux/macOS:**
```bash
# Temporary (current session only)
export STREAMTV_SECURITY_ACCESS_TOKEN="your-token-here"

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export STREAMTV_SECURITY_ACCESS_TOKEN="your-token-here"' >> ~/.bashrc
source ~/.bashrc
```

### Using .env Files

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your values:
   ```bash
   STREAMTV_SECURITY_ACCESS_TOKEN=your-actual-token-here
   STREAMTV_PLEX_TOKEN=your-plex-token-here
   ```

3. Load environment variables (if not using a tool that auto-loads .env):
   ```bash
   # Using python-dotenv
   pip install python-dotenv

   # In your code:
   from dotenv import load_dotenv
   load_dotenv()
   ```

**Important:** Add `.env` to `.gitignore` to prevent committing secrets:
```
.env
.env.local
.env.*.local
```

## Available Environment Variables

See `.env.example` for a complete list of all available environment variables.

Key security-related variables:
- `STREAMTV_SECURITY_ACCESS_TOKEN` - API authentication token
- `STREAMTV_PLEX_TOKEN` - Plex authentication token
- `STREAMTV_YOUTUBE_API_KEY` - YouTube Data API key
- `STREAMTV_YOUTUBE_OAUTH_CLIENT_SECRET` - YouTube OAuth client secret
- `STREAMTV_YOUTUBE_OAUTH_REFRESH_TOKEN` - YouTube OAuth refresh token
- `STREAMTV_ARCHIVE_ORG_PASSWORD` - Archive.org password
- `STREAMTV_PBS_PASSWORD` - PBS password
- `STREAMTV_METADATA_TVDB_API_KEY` - TVDB API key
- `STREAMTV_METADATA_TVDB_READ_TOKEN` - TVDB read token
- `STREAMTV_METADATA_TMDB_API_KEY` - TMDB API key

## Secret Rotation

### Rotating API Keys

1. Generate new API key/token from the service provider
2. Update the secret in your secure storage (Keychain/keyring/Credential Manager)
3. Update environment variables or `.env` file
4. Restart StreamTV
5. Revoke old API key/token from the service provider

### Verifying Secrets

After setting secrets, verify they're being used:

```bash
# Check if environment variable is set
echo $STREAMTV_SECURITY_ACCESS_TOKEN

# Check StreamTV logs for warnings
# If secrets are in config.yaml, you'll see warnings like:
# SECURITY WARNING: Sensitive values found in config file...
```

## Troubleshooting

### Secrets Not Being Used

If environment variables aren't being recognized:

1. Verify the variable name matches exactly (case-sensitive on Linux)
2. Check that the variable is exported: `echo $STREAMTV_SECURITY_ACCESS_TOKEN`
3. Restart StreamTV after setting environment variables
4. Check StreamTV logs for configuration warnings

### Keychain/Keyring Access Issues

**macOS:**
- Ensure Keychain Access app has necessary permissions
- Check that the service name matches exactly

**Linux:**
- Install keyring backend: `pip install keyring`
- For headless systems, use file-based keyring: `pip install keyrings.alt`

## Additional Resources

- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [12 Factor App - Config](https://12factor.net/config)
