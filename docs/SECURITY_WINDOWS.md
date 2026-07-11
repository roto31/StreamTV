# Windows Security Guide

This guide covers Windows-specific security considerations for StreamTV.

## Code Signing

### Obtaining a Code Signing Certificate

1. **Purchase a code signing certificate** from a trusted Certificate Authority (CA):
   - DigiCert
   - Sectigo (formerly Comodo)
   - GlobalSign

2. **Install the certificate** in Windows Certificate Store:
   ```powershell
   # Import certificate
   Import-PfxCertificate -FilePath "certificate.pfx" -CertStoreLocation Cert:\LocalMachine\My
   ```

### Signing the Executable

**Using signtool:**
```powershell
# Sign the executable
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com /d "StreamTV" /du "https://streamtv.example.com" StreamTV.exe

# Verify signature
signtool verify /pa /v StreamTV.exe
```

**Using PyInstaller with signing:**
```python
# In PyInstaller spec file or build script
import subprocess

def sign_executable(exe_path):
    subprocess.run([
        'signtool', 'sign',
        '/f', 'certificate.pfx',
        '/p', 'password',
        '/t', 'http://timestamp.digicert.com',
        '/d', 'StreamTV',
        exe_path
    ])
```

## PyInstaller Security Configuration

### Secure PyInstaller Build

Create a `streamtv.spec` file with security settings:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['streamtv/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('streamtv', 'streamtv'),
        ('schemas', 'schemas'),
        ('config.example.yaml', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'pandas', 'numpy',  # Exclude unnecessary packages
        'tkinter', 'PyQt5', 'PyQt6',  # Exclude GUI frameworks if not needed
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='StreamTV',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Use UPX compression (optional)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Sign the executable after build
import subprocess
subprocess.run([
    'signtool', 'sign',
    '/f', 'certificate.pfx',
    '/p', 'password',
    '/t', 'http://timestamp.digicert.com',
    '/d', 'StreamTV',
    exe.name
])
```

### Security Best Practices for PyInstaller

1. **Exclude unnecessary packages** to reduce attack surface
2. **Use UPX compression** with caution (may trigger antivirus false positives)
3. **Enable console mode** only for debugging builds
4. **Strip debug symbols** in release builds
5. **Verify all bundled dependencies** for known vulnerabilities

## Windows Firewall Configuration

### Allow StreamTV Through Firewall

**Using PowerShell:**
```powershell
# Allow inbound connections on port 8410
New-NetFirewallRule -DisplayName "StreamTV" -Direction Inbound -LocalPort 8410 -Protocol TCP -Action Allow

# Allow outbound connections (if needed)
New-NetFirewallRule -DisplayName "StreamTV Outbound" -Direction Outbound -LocalPort 8410 -Protocol TCP -Action Allow
```

**Using netsh:**
```cmd
netsh advfirewall firewall add rule name="StreamTV" dir=in action=allow protocol=TCP localport=8410
```

### Restrict Firewall Rules

For better security, restrict to specific IP ranges:

```powershell
# Allow only from local network
New-NetFirewallRule -DisplayName "StreamTV Local" -Direction Inbound -LocalPort 8410 -Protocol TCP -Action Allow -RemoteAddress /16,10.0.0.0/8,172.16.0.0/12
```

## Windows Defender Exclusions

If Windows Defender flags StreamTV, add exclusions:

**Using PowerShell:**
```powershell
# Add folder exclusion
Add-MpPreference -ExclusionPath "C:\Program Files\StreamTV"

# Add process exclusion
Add-MpPreference -ExclusionProcess "StreamTV.exe"
```

**Using Windows Security UI:**
1. Open Windows Security
2. Go to Virus & threat protection
3. Click "Manage settings"
4. Under Exclusions, click "Add or remove exclusions"
5. Add StreamTV folder and executable

## Windows Service Security

If running StreamTV as a Windows service:

### Create Service with Limited Privileges

```powershell
# Create service account (recommended)
$password = ConvertTo-SecureString "SecurePassword123!" -AsPlainText -Force
New-LocalUser -Name "StreamTVService" -Password $password -Description "StreamTV Service Account" -UserMayNotChangePassword
Add-LocalGroupMember -Group "Users" -Member "StreamTVService"

# Install service with service account
sc.exe create StreamTV binPath= "C:\Program Files\StreamTV\StreamTV.exe" obj= ".\StreamTVService" password= "SecurePassword123!"
sc.exe config StreamTV start= auto
```

### Service Security Settings

```powershell
# Set service to run with minimal privileges
sc.exe config StreamTV type= own
sc.exe config StreamTV error= normal
sc.exe config StreamTV start= auto

# Set service recovery options
sc.exe failure StreamTV reset= 86400 actions= restart/5000/restart/5000/restart/5000
```

## Credential Management

### Using Windows Credential Manager

Store secrets in Windows Credential Manager:

```powershell
# Store credential
cmdkey /add:StreamTV_STREAMTV_SECURITY_ACCESS_TOKEN /user:StreamTV /pass:your-token-here

# List credentials
cmdkey /list

# Delete credential
cmdkey /delete:StreamTV_STREAMTV_SECURITY_ACCESS_TOKEN
```

### Using Python with Windows Credentials

```python
try:
    import win32cred
    import win32con
    
    def get_credential(target_name):
        try:
            credential = win32cred.CredRead(target_name, win32cred.CRED_TYPE_GENERIC, 0)
            return credential['CredentialBlob'].decode('utf-16le')
        except Exception as e:
            print(f"Error reading credential: {e}")
            return None
    
    # Retrieve credential
    token = get_credential('StreamTV_STREAMTV_SECURITY_ACCESS_TOKEN')
    if token:
        import os
        os.environ['STREAMTV_SECURITY_ACCESS_TOKEN'] = token
except ImportError:
    print("Install pywin32: pip install pywin32")
```

## Antivirus Considerations

### False Positives

PyInstaller executables may trigger false positives:

1. **Submit to antivirus vendors** for whitelisting
2. **Use code signing** to reduce false positives
3. **Exclude from real-time scanning** during development
4. **Use reputable build tools** and keep them updated

### Testing with Antivirus

Before distribution:
1. Test with Windows Defender
2. Test with common third-party antivirus (Avast, AVG, Kaspersky)
3. Submit to VirusTotal for scanning
4. Address any legitimate security concerns

## Windows Update and Patching

### Keep System Updated

```powershell
# Check for Windows updates
Get-WindowsUpdate

# Install updates
Install-WindowsUpdate -AcceptAll -AutoReboot
```

### Application Updates

Implement secure update mechanism:
- Use HTTPS for update downloads
- Verify update signatures
- Use secure channels for update notifications

## Event Logging

### Configure Windows Event Log

```powershell
# Create custom event log source
New-EventLog -LogName Application -Source "StreamTV"

# Write to event log
Write-EventLog -LogName Application -Source "StreamTV" -EventId 1001 -EntryType Information -Message "StreamTV started"
```

## Additional Security Recommendations

1. **Run with least privilege**: Don't run as Administrator
2. **Use AppLocker**: Restrict which applications can run
3. **Enable BitLocker**: Encrypt system drive
4. **Use Windows Firewall**: Block unnecessary ports
5. **Regular security audits**: Review logs and access patterns
6. **Backup configuration**: Secure backup of config files
7. **Network isolation**: Run on isolated network if possible

## Troubleshooting

### Code Signing Issues

- Ensure certificate is valid and not expired
- Check certificate chain is complete
- Verify timestamp server is accessible

### Firewall Issues

- Check Windows Firewall logs
- Verify rule is enabled
- Test with firewall temporarily disabled

### Service Issues

- Check service account permissions
- Review Windows Event Viewer logs
- Verify service dependencies

## Resources

- [Microsoft Code Signing](https://docs.microsoft.com/en-us/windows/win32/seccrypto/cryptography-tools)
- [Windows Firewall Documentation](https://docs.microsoft.com/en-us/windows/security/threat-protection/windows-firewall/windows-firewall-with-advanced-security)
- [PyInstaller Security](https://pyinstaller.readthedocs.io/en/stable/usage.html#security)

