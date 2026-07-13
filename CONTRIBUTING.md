# Contributing to StreamTV

Thank you for your interest in contributing to StreamTV! This document provides guidelines and instructions for contributing.

## How to Contribute

### Reporting Bugs
- Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md)
- Include platform and version information
- Provide steps to reproduce
- Include relevant logs

### Suggesting Features
- Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md)
- Explain the use case
- Describe your proposed solution
- Consider alternatives

### Code Contributions

**This repository (StreamTV-source) accepts macOS contributions only.** Linux port work belongs in the separate [StreamTV-linux](https://github.com/roto31/StreamTV-linux) repository. See [macOS tree protection](docs/MACOS_TREE_PROTECTION.md) and [Linux repo workflow](docs/LINUX_REPO_WORKFLOW.md).

1. Install git hooks (required):
   ```bash
   bash scripts/install_git_hooks.sh
   ```
2. Fork or branch from `main`
3. Create a feature branch (`git checkout -b feature/amazing-feature`)
4. Make your changes — **do not** modify `streamtv/`, `StreamTVMac/`, or `packaging/macos/` unless you are an owner with bedrock approval
5. Commit (`git commit -m 'Add amazing feature'`) — pre-commit enforces forbidden paths
6. Push and open a Pull Request against **StreamTV-source**

## Development Setup

### Prerequisites
- Python 3.8 or higher
- FFmpeg
- Git

### Setup Steps
1. Clone your fork:
   ```bash
   git clone https://github.com/your-username/StreamTV.git
   cd StreamTV
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy example config:
   ```bash
   cp config.example.yaml config.yaml
   ```

5. Run the server:
   ```bash
   python3 -m streamtv.main
   ```

See the [Expert Guide](https://github.com/roto31/StreamTV/wiki/Expert-Guide) for detailed development setup.

## Code Style

### Python
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and small
- Maximum line length: 100 characters

### Shell Scripts
- Use shellcheck for validation
- Follow POSIX compliance where possible
- Add comments for complex logic

### Documentation
- Use Markdown for documentation
- Follow existing documentation style
- Update relevant docs when adding features

## Testing

### Before Submitting
- Test on your target platform
- Test install scripts if modified
- Ensure existing functionality still works
- Check for linting errors

### Test Checklist
- [ ] Code runs without errors
- [ ] Install scripts work correctly
- [ ] Documentation is updated
- [ ] No breaking changes (or documented if intentional)

## Documentation

### When to Update Documentation
- Adding new features
- Changing API endpoints
- Modifying installation process
- Adding new scripts or tools

### Documentation Locations
- Main docs: `docs/` directory
- Wiki: GitHub Wiki (use `create-wiki.sh` to update)
- README: Update if adding major features
- API docs: Update `docs/API.md` for API changes

## Pull Request Process

1. **Update Documentation**: Ensure all documentation is up to date
2. **Update CHANGELOG**: Add entry for your changes
3. **Test Thoroughly**: Test on multiple platforms if possible
4. **Follow Template**: Use the PR template provided
5. **Be Responsive**: Respond to review comments promptly

### PR Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Tests pass
- [ ] No new warnings

## Distribution Updates

If updating distribution files:
- Test install scripts on target platform
- Update platform-specific documentation
- Verify all files are included in commit
- Test the distribution package

### Building distributions

Assemble platform packages from the canonical tree:

```bash
python3 scripts/build_distributions.py macos linux
```

Overlays live under `packaging/macos/` and `packaging/linux/`. Windows and container targets were removed; community ports are welcome under MIT.

## Questions?

Feel free to:
- Open an issue with the [Question template](.github/ISSUE_TEMPLATE/question.md)
- Ask in discussions (if enabled)
- Review existing documentation

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Help others learn

Thank you for contributing to StreamTV! 🎉
