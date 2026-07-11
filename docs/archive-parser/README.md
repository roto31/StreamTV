# Archive.org Collection Parser Documentation

Tools and guides for creating StreamTV channels from Archive.org collections.

---

## 🚀 Quick Start

**Start here**: [QUICK_REFERENCE_ARCHIVE_PARSER.md](QUICK_REFERENCE_ARCHIVE_PARSER.md)

---

## 📚 Documentation Files

### Quick Reference ⭐
**[QUICK_REFERENCE_ARCHIVE_PARSER.md](QUICK_REFERENCE_ARCHIVE_PARSER.md)**
- Quick start commands
- File locations
- Common usage patterns

### Complete Example
**[MAGNUM_PI_CHANNEL_COMPLETE.md](MAGNUM_PI_CHANNEL_COMPLETE.md)**
- Full Magnum P.I. channel walkthrough
- 298 episodes with 296 enforced breaks
- Configuration examples
- Season breakdown

### Technical Implementation
**[ARCHIVE_PARSER_IMPLEMENTATION_SUMMARY.md](ARCHIVE_PARSER_IMPLEMENTATION_SUMMARY.md)**
- Technical details
- Parser algorithm
- Performance metrics
- Customization options

### Usage Examples
**[USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)**
- 12 practical examples
- Different use cases
- Advanced techniques
- Troubleshooting

### Troubleshooting
**[ARCHIVE_ORG_REDIRECT_FIX.md](ARCHIVE_ORG_REDIRECT_FIX.md)**
- 302 redirect issue fix
- Streaming configuration
- Technical details

### Restart Guide
**[MAGNUM_PI_RESTART_COMPLETE.md](MAGNUM_PI_RESTART_COMPLETE.md)**
- How to restart channel from scratch
- Database cleanup
- Fresh import process

---

## 🛠️ Tools

### GUI Tool (Recommended)
```bash
./scripts/archive_collection_parser_dialog.sh
```

### Command-Line Tool
```bash
python3 scripts/archive_collection_parser.py "URL" [OPTIONS]
```

See [scripts/ARCHIVE_PARSER_README.md](../../scripts/ARCHIVE_PARSER_README.md) for full tool documentation.

---

## 📺 Example: Magnum P.I. Channel

- **Source**: https://archive.org/details/JHiggens
- **Channel**: 80
- **Episodes**: 298
- **Breaks**: 296 (2-5 minutes each)
- **Status**: ✅ Operational

---

## 🔗 Related Documentation

- [Main Documentation Index](../INDEX.md)
- [Schedule Guide](../SCHEDULES.md)
- [API Documentation](../API.md)
- [Tool README](../../scripts/ARCHIVE_PARSER_README.md)

---

**Start Creating Channels**: [QUICK_REFERENCE_ARCHIVE_PARSER.md](QUICK_REFERENCE_ARCHIVE_PARSER.md)
