# YAML Validation

Guide to validating YAML configuration and schedule files.

## Overview

StreamTV uses JSON schemas to validate YAML files, ensuring they're correctly formatted and contain all required fields.

## Validation Schemas

Schemas are located in the `schemas/` directory:

- `channel.schema.json` - Channel configuration validation
- `schedule.schema.json` - Schedule file validation

## Validating Schedule Files

### Using Python

```python
from streamtv.validation import validate_schedule_file

result = validate_schedule_file("schedules/my-channel.yml")
if result.is_valid:
    print("Schedule file is valid!")
else:
    print(f"Errors: {result.errors}")
```

### Using Command Line

```bash
python3 -m streamtv.validation schedules/my-channel.yml
```

### Using API

```bash
curl -X POST http://localhost:8410/api/validate/schedule \
  -H "Content-Type: application/json" \
  -d @schedules/my-channel.yml
```

## Common Validation Errors

### Missing Required Fields

**Error:**
```
Missing required field: 'name'
```

**Fix:**
```yaml
name: My Channel  # Add this field
```

### Invalid Field Type

**Error:**
```
Field 'port' must be integer, got string
```

**Fix:**
```yaml
server:
  port: 8410  # Remove quotes for numbers
```

### Invalid Enum Value

**Error:**
```
Field 'order' must be one of: chronological, shuffle
```

**Fix:**
```yaml
content:
  - key: my_content
    collection: My Collection
    order: chronological  # Use valid value
```

### Invalid Duration Format

**Error:**
```
Field 'duration' must match format HH:MM:SS
```

**Fix:**
```yaml
- duration: "00:03:00"  # Use HH:MM:SS format
```

## Schema Reference

### Schedule Schema

```json
{
  "type": "object",
  "required": ["name", "content", "sequence", "playout"],
  "properties": {
    "name": {"type": "string"},
    "description": {"type": "string"},
    "content": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["key", "collection", "order"],
        "properties": {
          "key": {"type": "string"},
          "collection": {"type": "string"},
          "order": {"enum": ["chronological", "shuffle"]}
        }
      }
    }
  }
}
```

## Validation Best Practices

1. **Validate Before Deploying**
   - Always validate YAML files before using
   - Catch errors early

2. **Use IDE Plugins**
   - Install YAML validation plugins
   - Get real-time feedback

3. **Automate Validation**
   - Add to CI/CD pipeline
   - Validate on commit

4. **Keep Schemas Updated**
   - Update schemas with new features
   - Document schema changes

## IDE Integration

### VS Code

Install YAML extension:
```bash
code --install-extension redhat.vscode-yaml
```

Configure schema:
```json
{
  "yaml.schemas": {
    "schemas/schedule.schema.json": "schedules/*.yml"
  }
}
```

### PyCharm

1. Settings → Languages & Frameworks → Schemas and DTDs
2. Add schema mapping
3. Map `schemas/schedule.schema.json` to `schedules/*.yml`

## Related Documentation

- [YAML Validation Guide](../docs/YAML_VALIDATION.md) - Detailed validation documentation
- [Schedules](Schedules) - Schedule file format
- [Configuration](Configuration) - Configuration validation
- [Schedule Creator](Schedule-Creator) - Interactive creator with validation

