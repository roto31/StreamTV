# Schedule Files

This directory is for your custom schedule YAML files.

## Creating Schedule Files

Schedule files define what content plays on each channel and when. You can create schedule files manually or use the web interface at http://localhost:8410/schedules.

## Schedule File Format

See the main documentation for details on schedule file format, or use the web interface to create schedules interactively.

## Example

A basic schedule file might look like:

```yaml
channel:
  number: "1"
  name: "My Channel"

schedule:
  - title: "Example Video"
    url: "https://example.com/video.mp4"
    duration: 3600
    start_time: "00:00:00"
```

For more examples and detailed documentation, see the main StreamTV documentation.
