# Troubleshooting Scripts Documentation

StreamTV includes interactive troubleshooting scripts that use SwiftDialog to help diagnose and resolve issues. These scripts provide a user-friendly interface for common problems.

## Prerequisites

### SwiftDialog Installation

The troubleshooting scripts require SwiftDialog, a macOS dialog tool.

**Install via Homebrew:**
```bash
brew install --cask swiftdialog
```

**Manual Installation:**
1. Download from: https://github.com/swiftDialog/swiftDialog/releases
2. Install the `.pkg` file
3. Verify installation: `dialog --version`

## Available Scripts

### 1. Main Troubleshooting Script

**Location:** `scripts/troubleshoot_streamtv.sh`

**Purpose:** Comprehensive troubleshooting for all StreamTV issues

**Usage:**
```bash
cd "/path/to/StreamTV"
./scripts/troubleshoot_streamtv.sh
```

**Features:**
- Server status checking
- Channel issue diagnosis
- Streaming problem resolution
- Plex integration help
- Database troubleshooting
- Configuration validation
- Log viewing

**Menu Options:**

1. **Server Status**
   - Checks if StreamTV server is running
   - Tests server connectivity
   - Option to start server if not running

2. **Channel Issues**
   - Channel won't play
   - Channel starts from beginning
   - Channel has no content
   - Channel import failed
   - Other channel issues

3. **Streaming Issues**
   - Video won't play
   - Video keeps buffering
   - FFmpeg errors
   - Stream stops after first video
   - Other streaming issues

4. **Plex Integration**
   - Plex can't find tuner
   - Channels not appearing
   - Stream won't play
   - Guide not loading
   - Other Plex issues

5. **Database Issues**
   - Database integrity checks
   - Backup database
   - Reset database
   - View database info

6. **Configuration Issues**
   - Validate configuration
   - View configuration
   - Reset configuration
   - Edit configuration

7. **View Logs**
   - View StreamTV logs
   - Filter by error type
   - Real-time log monitoring

### 2. Plex-Specific Troubleshooting Script

**Location:** `scripts/troubleshoot_plex.sh`

**Purpose:** Specialized troubleshooting for Plex integration errors

**Usage:**
```bash
cd "/path/to/StreamTV"
./scripts/troubleshoot_plex.sh
```

**Features:**
- Error message input field
- Automatic error analysis
- Plex-specific diagnostics
- StreamTV log filtering
- Plex log access

**How It Works:**

1. **Error Input:**
   - Dialog appears asking for Plex error message
   - Paste the error from Plex interface
   - Click "Analyze"

2. **Error Analysis:**
   - Script analyzes error message
   - Identifies common error patterns
   - Provides diagnosis and solution

3. **Diagnostic Actions:**
   - Runs appropriate diagnostic checks
   - Tests relevant endpoints
   - Checks configuration
   - Views relevant logs

**Common Plex Errors Handled:**

- **"Could not tune channel"**
  - Checks FFmpeg installation
  - Verifies stream format
  - Tests network connectivity

- **"Problem fetching channel mappings"**
  - Validates XMLTV format
  - Checks channel ID matching
  - Tests XMLTV endpoint

- **"Rolling media grab failed"**
  - Checks stream continuity
  - Verifies MPEG-TS format
  - Tests stream stability

- **"Tuner not found"**
  - Tests discovery endpoint
  - Checks SSDP status
  - Verifies network configuration

- **"Invalid or missing file"**
  - Validates XMLTV structure
  - Checks required fields
  - Verifies encoding

- **"Timeout" errors**
  - Tests server response
  - Checks network latency
  - Verifies stream speed

- **"scan_all_pmts" errors**
  - Explains Plex transcoding issue
  - Provides workaround
  - Checks Plex FFmpeg version

## Using the Scripts

### Basic Usage

1. **Open Terminal**
   ```bash
   cd "/path/to/StreamTV"
   ```

2. **Run Script**
   ```bash
   ./scripts/troubleshoot_streamtv.sh
   ```

3. **Follow Prompts**
   - Select issue category
   - Provide requested information
   - Follow suggested solutions

### Advanced Usage

#### Running Specific Diagnostics

**Check Server Status Only:**
```bash
# Edit script to jump to specific section
# Or use curl directly:
curl http://localhost:8410/health
```

**Test Plex Discovery:**
```bash
# Get your IP address
ipconfig getifaddr en0

# Test discovery URL
curl http://YOUR_IP:8410/hdhomerun/discover.json
```

#### Custom Error Analysis

**For Plex Errors:**
1. Copy error message from Plex
2. Run: `./scripts/troubleshoot_plex.sh`
3. Paste error when prompted
4. Follow analysis results

**For StreamTV Errors:**
1. Check logs: `tail -f streamtv.log`
2. Copy relevant error
3. Run main troubleshooting script
4. Select appropriate category

## Script Output

### Log Files

Scripts create log files for tracking:

**Location:** `troubleshooting.log`

**Format:**
```
2025-01-28 10:30:00: Channel Issue - Channel 1980 won't play
2025-01-28 10:35:00: Plex Error - Could not tune channel
2025-01-28 10:40:00: Streaming Issue - FFmpeg errors
```

### Diagnostic Results

Scripts provide:
- ✅ Success indicators
- ❌ Error indicators
- Diagnostic messages
- Suggested solutions
- Next steps

## Troubleshooting the Scripts

### Script Won't Run

**Issue:** Permission denied
```bash
chmod +x scripts/troubleshoot_streamtv.sh
chmod +x scripts/troubleshoot_plex.sh
```

**Issue:** SwiftDialog not found
```bash
# Install SwiftDialog
brew install --cask swiftdialog

# Verify installation
dialog --version
```

### Script Errors

**Issue:** Dialog command not found
- Ensure SwiftDialog is installed
- Check PATH includes dialog binary
- Try full path: `/usr/local/bin/dialog`

**Issue:** Script syntax errors
- Check shell: `echo $SHELL` (should be zsh)
- Run with debug: `zsh -x scripts/troubleshoot_streamtv.sh`

## Integration with Documentation

### Related Documentation

- **[Beginner Guide](./BEGINNER_GUIDE.md)** - Basic troubleshooting
- **[Intermediate Guide](./INTERMEDIATE_GUIDE.md)** - Advanced troubleshooting
- **[Expert Guide](./EXPERT_GUIDE.md)** - Deep technical troubleshooting
- **[HDHomeRun Guide](./HDHOMERUN.md)** - Plex integration details

### When to Use Scripts vs Manual Troubleshooting

**Use Scripts When:**
- You're not sure what the problem is
- You want guided troubleshooting
- You need error message analysis
- You want automated diagnostics

**Use Manual Troubleshooting When:**
- You know the exact issue
- Scripts don't cover your problem
- You need custom diagnostics
- You're debugging code

## Contributing

### Adding New Diagnostics

To add new diagnostic checks:

1. **Edit Script:**
   ```bash
   # Add new function
   troubleshoot_new_issue() {
       # Diagnostic logic
   }
   ```

2. **Add to Menu:**
   ```bash
   # Update menu options
   --selectvalues "...,New Issue,..."
   ```

3. **Test:**
   ```bash
   ./scripts/troubleshoot_streamtv.sh
   ```

### Error Pattern Recognition

To add new error patterns:

1. **Edit Plex Script:**
   ```bash
   # Add pattern check
   elif echo "$error_message" | grep -qi "new error pattern"; then
       diagnosis="New Error Type"
       solution="Solution description"
       action="check_something"
   ```

2. **Add Diagnostic Function:**
   ```bash
   check_something() {
       # Diagnostic checks
   }
   ```

## Examples

### Example 1: Server Not Running

**Scenario:** User can't access web interface

**Steps:**
1. Run: `./scripts/troubleshoot_streamtv.sh`
2. Select: "Server Status"
3. Script detects server not running
4. Click: "Start Server"
5. Server starts automatically

### Example 2: Plex Can't Find Tuner

**Scenario:** Plex shows "Tuner not found" error

**Steps:**
1. Run: `./scripts/troubleshoot_plex.sh`
2. Paste error: "Tuner not found"
3. Script analyzes error
4. Select: "Run diagnostic check"
5. Script tests discovery endpoint
6. Provides discovery URL and setup steps

### Example 3: Channel Won't Play

**Scenario:** Channel exists but won't play

**Steps:**
1. Run: `./scripts/troubleshoot_streamtv.sh`
2. Select: "Channel Issues"
3. Select: "Channel won't play"
4. Enter channel number
5. Script checks:
   - Channel exists
   - Channel enabled
   - Channel has content
   - Stream status
6. Provides diagnosis and solution

## Best Practices

1. **Always Check Logs First**
   - Scripts can help, but logs have details
   - Use "View Logs" option in scripts

2. **Save Error Messages**
   - Copy exact error text
   - Paste into script when prompted
   - Error messages help diagnosis

3. **Follow Suggested Solutions**
   - Scripts provide step-by-step solutions
   - Follow in order
   - Test after each step

4. **Document Your Issues**
   - Scripts log to `troubleshooting.log`
   - Keep notes of what worked
   - Share solutions with community

## Support

For additional help:
- Check documentation guides
- Review log files
- Test with curl commands
- Check GitHub issues

---

*Last Updated: 2025-01-28*

