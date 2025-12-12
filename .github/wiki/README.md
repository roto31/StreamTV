# StreamTV Wiki

This directory contains the wiki pages for StreamTV. These pages can be used to populate the GitHub wiki.

## Wiki Structure

The wiki is organized into the following sections:

### Getting Started
- **Home** - Main wiki landing page
- **Installation** - Installation guides for all platforms
- **Quick Start** - Get up and running in 5 minutes

### Core Documentation
- **Configuration** - Complete configuration reference
- **API Reference** - Full API documentation
- **Schedules** - Schedule file format and creation

### Additional Pages

To add new wiki pages, create markdown files in this directory following the naming convention:
- Use `Title-Case-With-Hyphens.md` for page names
- Link to other pages using `[Page Name](Page-Name)` format

## Uploading to GitHub Wiki

GitHub wikis are stored in a separate git repository. To upload these pages:

1. Clone the wiki repository:
   ```bash
   git clone https://github.com/yourusername/streamtv.wiki.git
   ```

2. Copy wiki pages:
   ```bash
   cp .github/wiki/*.md streamtv.wiki/
   ```

3. Commit and push:
   ```bash
   cd streamtv.wiki
   git add .
   git commit -m "Add wiki pages"
   git push
   ```

## Wiki Page Template

```markdown
# Page Title

Brief description of the page.

## Section 1

Content here.

## Section 2

More content.

## Related Pages

- [Related Page 1](Related-Page-1)
- [Related Page 2](Related-Page-2)
```

## Maintenance

- Keep pages up to date with code changes
- Update links when pages are renamed
- Add new pages as features are added
- Remove outdated information

