# Auto-Healing System

StreamTV includes an intelligent auto-healing system that automatically monitors logs, detects errors, and applies fixes using AI-powered analysis.

## Features

🤖 **AI-Powered Analysis**: Uses Ollama AI to analyze errors and suggest fixes  
📊 **Pattern Detection**: Identifies recurring error patterns automatically  
🔧 **Automatic Fixes**: Applies known fixes for common issues  
📈 **Trend Analysis**: Tracks error trends over time  
💾 **Safe Backups**: Creates backups before applying any fixes  
🔄 **Continuous Monitoring**: Can run continuously to keep your system healthy  

## Requirements

### Ollama Setup

The auto-healer uses [Ollama](https://ollama.ai/) for AI-powered log analysis.

1. **Install Ollama**:
   ```bash
   # macOS
   brew install ollama
   
   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Start Ollama service**:
   ```bash
   ollama serve
   ```

3. **Pull the model** (recommended: llama3.2):
   ```bash
   ollama pull llama3.2:latest
   ```

### Python Dependencies

The auto-healer uses standard StreamTV dependencies (httpx, pyyaml, etc.) which are already installed.

## Configuration

Edit `config.yaml` to configure auto-healing:

```yaml
auto_healer:
  enabled: false  # Set to true to enable
  enable_ai: true  # Use AI for analysis
  ollama_url: http://localhost:11434
  ollama_model: llama3.2:latest
  check_interval: 30  # Minutes between checks
  apply_fixes: false  # true = auto-apply, false = dry-run
  max_fix_attempts: 3  # Max attempts per error
```

## Usage

### One-Time Health Check

Run a single health check (dry-run, no fixes applied):

```bash
python scripts/auto_heal.py
```

### Apply Fixes

Run health check and apply fixes:

```bash
python scripts/auto_heal.py --apply
```

### Continuous Monitoring

Run continuous monitoring (checks every 30 minutes):

```bash
python scripts/auto_heal.py --continuous --interval 30
```

### Disable AI

Use only registered fixes (no AI analysis):

```bash
python scripts/auto_heal.py --no-ai
```

### Custom Ollama Setup

Use custom Ollama URL or model:

```bash
python scripts/auto_heal.py \
  --ollama-url http://remote-server:11434 \
  --ollama-model codellama:latest
```

### JSON Output

Get machine-readable JSON output:

```bash
python scripts/auto_heal.py --json
```

## What It Fixes

### Automatic Fixes (Built-in)

The auto-healer has built-in fixes for common issues:

1. **FFmpeg Timeouts**
   - Increases timeout values for problematic files
   - Adjusts HTTP timeout for slow connections
   - Example: AVI files that need extra time to start

2. **Connection Errors**
   - Increases connection timeout
   - Increases max retries
   - Enables authentication when needed

3. **Archive.org Redirects**
   - Verifies redirect handling is enabled
   - Suggests authentication if needed

4. **HTTP Errors** (404, 500, 502, 503)
   - Suggests enabling authentication
   - Recommends checking service availability

### AI-Suggested Fixes

When AI analysis is enabled, the system can:
- Analyze complex error patterns
- Suggest context-aware fixes
- Identify root causes
- Provide detailed rationale

**Note**: AI-suggested fixes require manual review by default for safety.

## Example Output

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║           StreamTV Auto-Healing System v1.0                    ║
║        Powered by Ollama AI Log Analysis                      ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

Mode: DRY-RUN MODE
AI Analysis: ENABLED
Workspace: /Users/user/StreamTV
Ollama: http://localhost:11434 (llama3.2:latest)

======================================================================
AUTO-HEALER: Starting health check #1
======================================================================
Scanning recent logs for errors...
⚠️  Detected 5 error(s)

Error breakdown by category:
  - timeout: 3 error(s)
  - ffmpeg: 2 error(s)

Analyzing errors with AI...
Attempting to apply fixes...
Processing 3 instance(s) of 'ffmpeg_timeout'
✅ Applied 2 fix(es) for 'ffmpeg_timeout'

======================================================================
AUTO-HEALER: Health check #1 complete
  Status: healing
  Errors detected: 5
  Fixes applied: 2
======================================================================

HEALTH CHECK RESULTS
======================================================================

Status: 🔧 HEALING
Errors Detected: 5
High Priority: 3
Fixes Applied: 2
AI Analyses: 2
Ollama: ✅ Available

Error Breakdown by Category:
  - timeout: 3 error(s)
  - ffmpeg: 2 error(s)

Fixes Applied:
  ✅ ffmpeg_timeout: 2 fix(es)

Recommendations:
  ⏱️  Multiple timeout errors - consider increasing timeout values
  💡 Fixes available but not applied (dry-run mode)

⚠️  DRY RUN MODE: No changes were actually applied
   Run with --apply to apply fixes

======================================================================
```

## Error Detection Patterns

The auto-healer detects these error patterns:

| Pattern | Severity | Category | Description |
|---------|----------|----------|-------------|
| `ffmpeg_timeout` | High | timeout | FFmpeg no data received |
| `ffmpeg_demuxing_error` | Medium | ffmpeg | Demuxing I/O error |
| `connection_refused` | High | connection | Connection refused |
| `http_error` | Medium | connection | HTTP 4xx/5xx errors |
| `archive_org_redirect` | Low | connection | Redirect issues |
| `stream_not_found` | High | streaming | Stream URL not found |
| `database_error` | Medium | database | SQLAlchemy errors |
| `authentication_error` | High | auth | Auth failures |
| `timeout_general` | Medium | timeout | General timeouts |
| `file_not_found` | High | filesystem | Missing files |

## Safety Features

### Backups

All modified files are backed up to `.streamtv_backups/` before changes are applied:

```
.streamtv_backups/
  ├── mpegts_streamer.py.20231204_143022.backup
  ├── config.yaml.20231204_143045.backup
  └── ...
```

### Dry-Run Mode

By default, the auto-healer runs in dry-run mode (no changes applied). This lets you:
- See what would be fixed
- Review AI suggestions
- Verify safety before applying

To actually apply fixes, use `--apply` flag.

### Fix Limitations

Built-in fixes have safety constraints:
- Timeout values have min/max limits
- Numeric values are validated
- Fixes won't apply if values are already optimal

## Integration with StreamTV

### Manual Integration

Add to your startup script or cron job:

```bash
#!/bin/bash
# Check health every hour
while true; do
    python scripts/auto_heal.py --apply
    sleep 3600
done
```

### Automatic Background Monitoring

Enable in config:

```yaml
auto_healer:
  enabled: true
  apply_fixes: true
  check_interval: 30
```

Then the auto-healer will run automatically when StreamTV starts.

## Troubleshooting

### Ollama Not Available

If you see "Ollama not available":

1. Check if Ollama is running:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. Start Ollama if needed:
   ```bash
   ollama serve
   ```

3. Verify model is available:
   ```bash
   ollama list
   ollama pull llama3.2:latest
   ```

### No Fixes Available

If "no fix available" for an error:

1. Check if error is in fix registry (`error_fixer.py`)
2. AI suggestions require manual review by default
3. You may need to add a custom fix pattern

### False Positives

If errors are detected incorrectly:

1. Check error patterns in `error_monitor.py`
2. Adjust pattern regex if needed
3. Set severity appropriately

## Advanced Usage

### Adding Custom Fix Patterns

Edit `streamtv/utils/error_fixer.py` to add custom fixes:

```python
FIX_REGISTRY = {
    'my_custom_error': {
        'type': 'config',
        'target': 'config.yaml',
        'fixes': [
            {
                'description': 'Increase custom timeout',
                'yaml_path': ['my_section', 'timeout'],
                'operation': 'increase',
                'factor': 1.5,
                'max_value': 120
            }
        ]
    }
}
```

### Custom Error Patterns

Edit `streamtv/utils/error_monitor.py` to add custom patterns:

```python
ErrorPattern(
    name="my_custom_error",
    pattern=r"my error pattern.*",
    severity="high",
    category="custom",
    description="Description of error"
)
```

## Best Practices

1. **Run in dry-run first**: Always test with dry-run before applying fixes
2. **Monitor regularly**: Run health checks periodically (every 30-60 minutes)
3. **Review AI suggestions**: AI suggestions are logged but not auto-applied
4. **Keep backups**: Don't delete `.streamtv_backups/` directory
5. **Check Ollama logs**: Monitor Ollama for AI analysis issues
6. **Gradual rollout**: Start with `apply_fixes: false`, then enable after testing

## API Reference

See the source code for detailed API documentation:
- `streamtv/utils/auto_healer.py` - Main coordinator
- `streamtv/utils/error_monitor.py` - Error detection
- `streamtv/utils/error_fixer.py` - Fix application
- `streamtv/utils/ollama_client.py` - AI integration

## Support

For issues or questions:
1. Check logs in `~/Library/Logs/StreamTV/`
2. Review error patterns and fixes
3. Test with `--no-ai` to isolate AI issues
4. Create an issue on GitHub with logs and config

