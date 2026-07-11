# YAML Validation with JSON Schemas

This platform uses JSON schemas to validate YAML configuration files, providing type checking, format validation, and error reporting while maintaining YAML as the primary human-readable format.

## Overview

- **Primary Format**: YAML (human-readable, supports comments)
- **Validation**: JSON Schema (strict type checking)
- **API Responses**: JSON (standard web format)
- **Database Metadata**: JSON (flexible schema)

## Schema Files

### Channel Schema (`schemas/channel.schema.json`)

Validates channel configuration YAML files (`channel-*.yml`):

```yaml
channels:
  - number: '1980'
    name: Channel Name
    streams:
      - id: stream_id
        collection: Collection Name
        url: https://...
```

**Validates:**
- Required fields: `number`, `name`, `streams`
- Stream properties: `id`, `collection`, `url`, `type`, `year`, etc.
- Date format: `broadcast_date` must be `YYYY-MM-DD`
- Runtime format: `runtime` must be ISO 8601 duration (e.g., `PT3M44S`)
- URL format: `url` must be valid URI
- Source enum: `source` must be `youtube`, `archive`, or `archive_org`

### Schedule Schema (`schemas/schedule.schema.json`)

Validates schedule YAML files (`schedules/*.yml`) compatible with ErsatzTV:

```yaml
name: Schedule Name
content:
  - key: content_key
    collection: Collection Name
sequence:
  - key: sequence_key
    items:
      - duration: "00:01:00"
        content: content_key
playout:
  - sequence: sequence_key
  - repeat: true
```

**Validates:**
- Required fields: `name`, `content`, `sequence`, `playout`
- Content definitions: `key`, `collection`, `order`
- Sequence items: Supports all ErsatzTV directives
- Duration format: `HH:MM:SS`
- Import support: Validates imported YAML files

## Usage

### Programmatic Validation

```python
from pathlib import Path
from streamtv.validation import YAMLValidator, ValidationError

validator = YAMLValidator()

# Validate channel file
try:
    result = validator.validate_channel_file(Path("channel-1980-complete.yml"))
    if result['valid']:
        print("✓ Valid")
    else:
        print(f"Errors: {result['errors']}")
except ValidationError as e:
    print(f"Validation failed: {e.message}")
```

### API Validation Endpoints

#### Validate Channel YAML
```bash
POST /import/validate/channel
Content-Type: multipart/form-data

# Upload YAML file
curl -X POST http://localhost:8410/import/validate/channel \
  -F "yaml_file=@channel-1980-complete.yml"
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "filename": "channel-1980-complete.yml"
}
```

#### Validate Schedule YAML
```bash
POST /import/validate/schedule
Content-Type: multipart/form-data

# Upload YAML file
curl -X POST http://localhost:8410/import/validate/schedule \
  -F "yaml_file=@schedules/mn-olympics-1980.yml"
```

### Import with Validation

Channel imports automatically validate by default:

```python
from streamtv.importers import import_channels_from_yaml

# Import with validation (default)
channels = import_channels_from_yaml(Path("channel-1980-complete.yml"))

# Import without validation (if needed)
channels = import_channels_from_yaml(Path("channel-1980-complete.yml"), validate=False)
```

### API Import with Validation

```bash
POST /import/channels/yaml?validate=true
Content-Type: multipart/form-data

# Upload and import with validation
curl -X POST "http://localhost:8410/import/channels/yaml?validate=true" \
  -F "yaml_file=@channel-1980-complete.yml"
```

## YAML to JSON Conversion

### API Endpoint

Convert YAML files to JSON for programmatic access:

```bash
POST /import/convert/yaml-to-json
Content-Type: multipart/form-data

curl -X POST http://localhost:8410/import/convert/yaml-to-json \
  -F "yaml_file=@channel-1980-complete.yml"
```

**Response:**
```json
{
  "filename": "channel-1980-complete.yml",
  "json": {
    "channels": [
      {
        "number": "1980",
        "name": "Channel Name",
        "streams": [...]
      }
    ]
  }
}
```

### Programmatic Conversion

```python
from streamtv.utils.yaml_to_json import yaml_to_json
from pathlib import Path

# Convert YAML file to JSON
json_data = yaml_to_json(Path("channel-1980-complete.yml"))
print(json_data)
```

## Error Handling

Validation errors provide detailed information:

```python
try:
    result = validator.validate_channel_file(file_path)
except ValidationError as e:
    print(f"Message: {e.message}")
    print(f"Errors: {e.errors}")
    # Errors is a list of specific validation failures
```

**Example Error:**
```
Validation failed for channel-1980-complete.yml (channel):
  - channels -> 0 -> streams -> 0 -> url: 'invalid-url' is not a valid URI
  - channels -> 0 -> streams -> 1 -> broadcast_date: '1980/02/13' does not match pattern '^\\d{4}-\\d{2}-\\d{2}$'
```

## Benefits

1. **Type Safety**: Catch errors before import
2. **Format Validation**: Ensure dates, URLs, durations are correct
3. **Documentation**: Schemas serve as documentation
4. **IDE Support**: JSON schemas enable autocomplete in editors
5. **API Compatibility**: Easy conversion to JSON for APIs
6. **Human Readable**: YAML remains easy to edit

## Schema Customization

Schemas can be customized in `schemas/` directory:

- `channel.schema.json` - Channel configuration validation
- `schedule.schema.json` - Schedule file validation

Edit schemas to add new fields or adjust validation rules. The validator automatically reloads schemas on initialization.

## Integration with ErsatzTV

The schedule schema is compatible with ErsatzTV's YAML format, ensuring:
- Import compatibility with ErsatzTV schedules
- Support for all ErsatzTV directives (padToNext, waitUntil, etc.)
- Validation of complex sequence structures

## Best Practices

1. **Always validate before import** - Catch errors early
2. **Use validation in CI/CD** - Automate checks
3. **Keep schemas updated** - Reflect new fields
4. **Use YAML for editing** - Human-readable format
5. **Use JSON for APIs** - Standard web format

