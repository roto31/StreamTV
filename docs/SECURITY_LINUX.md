# Linux Security Guide

This guide covers Linux-specific security considerations for StreamTV.

## AppImage Security

### Code Signing AppImage

Sign AppImage for distribution:

```bash
# Generate GPG key (if not already done)
gpg --gen-key

# Sign AppImage
gpg --armor --detach-sign StreamTV-x86_64.AppImage
mv StreamTV-x86_64.AppImage.sig StreamTV-x86_64.AppImage.sig

# Verify signature
gpg --verify StreamTV-x86_64.AppImage.sig StreamTV-x86_64.AppImage
```

### AppImage Permissions

Set proper permissions:

```bash
# Make executable
chmod +x StreamTV-x86_64.AppImage

# Set ownership
chown user:user StreamTV-x86_64.AppImage
```

## AppArmor Profile

Create AppArmor profile for StreamTV:

```bash
# Create profile file
sudo nano /etc/apparmor.d/usr.bin.streamtv
```

**AppArmor Profile Content:**
```
#include <tunables/global>

/usr/bin/streamtv {
  #include <abstractions/base>
  #include <abstractions/python>

  # Allow reading config files
  /etc/streamtv/** r,
  /home/*/.config/streamtv/** r,
  /home/*/.streamtv/** r,

  # Allow reading application files
  /opt/streamtv/** r,
  /usr/share/streamtv/** r,

  # Allow writing logs
  /var/log/streamtv/** w,
  /home/*/.local/share/streamtv/logs/** w,

  # Allow network access
  network,

  # Allow reading system libraries
  /usr/lib/** rm,
  /lib/** rm,
  /lib64/** rm,

  # Deny access to sensitive files
  deny /etc/shadow r,
  deny /etc/passwd r,
  deny /root/** r,
  deny /home/*/.* r,  # Deny hidden files in home directories
  deny /home/*/.ssh/** r,
  deny /home/*/.gnupg/** r,

  # Allow executing Python
  /usr/bin/python3 ix,
  /usr/bin/python3.* ix,

  # Allow reading Python libraries
  /usr/lib/python3.*/** r,
  /usr/local/lib/python3.*/** r,

  # Capabilities
  capability net_bind_service,
  capability setuid,
  capability setgid,
}
```

**Load and enable profile:**
```bash
# Load profile
sudo apparmor_parser -r /etc/apparmor.d/usr.bin.streamtv

# Enable profile
sudo aa-enforce /usr/bin/streamtv

# Check status
sudo aa-status | grep streamtv
```

## SELinux Policy

Create SELinux policy for StreamTV:

```bash
# Create policy module
sudo nano streamtv.te
```

**SELinux Policy Content:**
```
module streamtv 1.0;

require {
    type unconfined_service_t;
    type unconfined_t;
    class tcp_socket { create bind listen accept };
    class file { read write execute };
    class dir { read write search };
}

# Allow StreamTV to bind to network ports
allow unconfined_service_t self:tcp_socket { create bind listen accept };

# Allow reading config files
allow unconfined_t streamtv_config_t:file { read };
allow unconfined_t streamtv_config_t:dir { read search };

# Allow writing logs
allow unconfined_t streamtv_log_t:file { write append };
allow unconfined_t streamtv_log_t:dir { write add_name };
```

**Compile and install:**
```bash
# Compile policy
checkmodule -M -m -o streamtv.mod streamtv.te
semodule_package -o streamtv.pp -m streamtv.mod

# Install policy
sudo semodule -i streamtv.pp

# Verify
sudo semodule -l | grep streamtv
```

## systemd Service Security

### Secure systemd Service File

Create `/etc/systemd/system/streamtv.service`:

```ini
[Unit]
Description=StreamTV Media Server
After=network.target

[Service]
Type=simple
User=streamtv
Group=streamtv
WorkingDirectory=/opt/streamtv
ExecStart=/usr/bin/python3 -m streamtv.main
Restart=on-failure
RestartSec=5

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/var/lib/streamtv /var/log/streamtv
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictNamespaces=true
LockPersonality=true
MemoryDenyWriteExecute=true
RestrictAddressFamilies=AF_INET AF_INET6
RestrictSUIDSGID=true
RemoveIPC=true

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Environment
Environment="STREAMTV_SECURITY_ACCESS_TOKEN_FILE=/run/secrets/streamtv_token"
EnvironmentFile=-/etc/streamtv/streamtv.conf

[Install]
WantedBy=multi-user.target
```

### Service User Creation

```bash
# Create dedicated user
sudo useradd -r -s /bin/false -d /opt/streamtv streamtv

# Set ownership
sudo chown -R streamtv:streamtv /opt/streamtv
sudo chown -R streamtv:streamtv /var/lib/streamtv
sudo chown -R streamtv:streamtv /var/log/streamtv

# Set permissions
sudo chmod 750 /opt/streamtv
sudo chmod 750 /var/lib/streamtv
sudo chmod 750 /var/log/streamtv
```

### systemd Secrets Management

Use systemd's LoadCredential for secrets:

```ini
[Service]
LoadCredential=streamtv_token:/etc/streamtv/secrets/token
Environment="STREAMTV_SECURITY_ACCESS_TOKEN_FILE=%d/streamtv_token"
```

**Set credential:**
```bash
# Create secrets directory
sudo mkdir -p /etc/streamtv/secrets
sudo chmod 700 /etc/streamtv/secrets

# Store secret
echo "your-token-here" | sudo tee /etc/streamtv/secrets/token
sudo chmod 600 /etc/streamtv/secrets/token
sudo chown streamtv:streamtv /etc/streamtv/secrets/token
```

## Firewall Configuration

### UFW (Ubuntu/Debian)

```bash
# Allow StreamTV port
sudo ufw allow 8410/tcp comment 'StreamTV'

# Allow from specific IP (more secure)
sudo ufw allow from /24 to any port 8410 proto tcp comment 'StreamTV Local'

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### firewalld (RHEL/CentOS/Fedora)

```bash
# Add service
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-port=8410/tcp

# Or restrict to specific zone
sudo firewall-cmd --permanent --zone=internal --add-port=8410/tcp

# Reload firewall
sudo firewall-cmd --reload

# Check status
sudo firewall-cmd --list-all
```

### iptables (Traditional)

```bash
# Allow inbound on port 8410
sudo iptables -A INPUT -p tcp --dport 8410 -j ACCEPT

# Allow from specific network
sudo iptables -A INPUT -p tcp -s /24 --dport 8410 -j ACCEPT

# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

## Keyring Integration

### Using Linux Keyring

```bash
# Install keyring
pip install keyring

# Store secret
python3 -m keyring set StreamTV STREAMTV_SECURITY_ACCESS_TOKEN
# Enter password when prompted

# Retrieve secret
python3 -m keyring get StreamTV STREAMTV_SECURITY_ACCESS_TOKEN
```

**In Python:**
```python
import keyring
import os

# Store secret
keyring.set_password('StreamTV', 'STREAMTV_SECURITY_ACCESS_TOKEN', 'your-token')

# Retrieve secret
token = keyring.get_password('StreamTV', 'STREAMTV_SECURITY_ACCESS_TOKEN')
if token:
    os.environ['STREAMTV_SECURITY_ACCESS_TOKEN'] = token
```

## File Permissions

### Secure Directory Structure

```bash
# Create directories with proper permissions
sudo mkdir -p /opt/streamtv
sudo mkdir -p /var/lib/streamtv
sudo mkdir -p /var/log/streamtv
sudo mkdir -p /etc/streamtv

# Set ownership
sudo chown -R streamtv:streamtv /opt/streamtv
sudo chown -R streamtv:streamtv /var/lib/streamtv
sudo chown -R streamtv:streamtv /var/log/streamtv
sudo chown -R root:streamtv /etc/streamtv

# Set permissions
sudo chmod 750 /opt/streamtv
sudo chmod 750 /var/lib/streamtv
sudo chmod 750 /var/log/streamtv
sudo chmod 750 /etc/streamtv
sudo chmod 640 /etc/streamtv/*.yaml
```

## Logging and Monitoring

### rsyslog Configuration

Create `/etc/rsyslog.d/30-streamtv.conf`:

```
# StreamTV logs
local0.*    /var/log/streamtv/streamtv.log
local0.err  /var/log/streamtv/streamtv-error.log
```

**Restart rsyslog:**
```bash
sudo systemctl restart rsyslog
```

### Log Rotation

Create `/etc/logrotate.d/streamtv`:

```
/var/log/streamtv/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 streamtv streamtv
    sharedscripts
    postrotate
        systemctl reload streamtv > /dev/null 2>&1 || true
    endscript
}
```

## Additional Security Recommendations

1. **Use SELinux or AppArmor**: Enable mandatory access control
2. **Run as non-root**: Use dedicated user account
3. **Limit file permissions**: Use principle of least privilege
4. **Enable firewall**: Restrict network access
5. **Regular updates**: Keep system and dependencies updated
6. **Monitor logs**: Set up log monitoring and alerting
7. **Backup configuration**: Secure backup of config files
8. **Network isolation**: Run on isolated network if possible
9. **Use HTTPS**: Enable TLS for web interface
10. **Regular audits**: Review security logs and access patterns

## Troubleshooting

### AppArmor Issues

```bash
# Check profile status
sudo aa-status

# View profile violations
sudo dmesg | grep apparmor

# Reload profile
sudo apparmor_parser -r /etc/apparmor.d/usr.bin.streamtv
```

### SELinux Issues

```bash
# Check SELinux status
getenforce

# View SELinux violations
sudo ausearch -m avc -ts recent

# Set permissive mode for testing
sudo setenforce 0

# Set enforcing mode
sudo setenforce 1
```

### systemd Service Issues

```bash
# Check service status
sudo systemctl status streamtv

# View logs
sudo journalctl -u streamtv -f

# Check service security settings
systemd-analyze security streamtv.service
```

## Resources

- [AppArmor Documentation](https://gitlab.com/apparmor/apparmor/-/wikis/Documentation)
- [SELinux Documentation](https://selinuxproject.org/page/Main_Page)
- [systemd Security](https://www.freedesktop.org/software/systemd/man/systemd.exec.html#Security)
- [Linux Keyring](https://github.com/jaraco/keyring)

