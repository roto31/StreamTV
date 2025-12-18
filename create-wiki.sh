#!/bin/bash
#
# Create GitHub Wiki for StreamTV
# Consolidates all documentation from distribution folders into wiki pages
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WIKI_DIR="$SCRIPT_DIR/.wiki-temp"
GITHUB_USER="${GITHUB_USER:-roto31}"
REPO_NAME="${REPO_NAME:-StreamTV}"

# Keep wiki files for manual push if script fails
# (We'll clean up manually at the end if successful)

# Convert markdown links for wiki (remove .md, fix paths)
convert_markdown_for_wiki() {
    local input_file="$1"
    local output_file="$2"
    
    if [ ! -f "$input_file" ]; then
        return 1
    fi
    
    # Convert markdown for wiki:
    # - Remove .md extensions from links
    # - Convert relative paths to wiki page names
    # - Fix image paths
    sed -E \
        -e 's|\[([^\]]+)\]\(([^)]+)\.md\)|[\1](\2)|g' \
        -e 's|\[([^\]]+)\]\(docs/([^)]+)\)|[\1](\2)|g' \
        -e 's|\[([^\]]+)\]\(\.\./docs/([^)]+)\)|[\1](\2)|g' \
        -e 's|\[([^\]]+)\]\(\.\./\.\./docs/([^)]+)\)|[\1](\2)|g' \
        -e 's|docs/installation/||g' \
        -e 's|docs/||g' \
        "$input_file" > "$output_file"
}

# Create wiki page from platform documentation
create_platform_wiki() {
    local platform_name="$1"
    local platform_dir="$2"
    local wiki_file="$3"
    
    print_info "Creating $platform_name wiki page..."
    
    {
        echo "# $platform_name Platform"
        echo ""
        echo "Complete documentation for StreamTV on $platform_name."
        echo ""
        
        # Main README
        if [ -f "$platform_dir/README.md" ]; then
            echo "## Overview"
            echo ""
            convert_markdown_for_wiki "$platform_dir/README.md" "$WIKI_DIR/temp.md"
            tail -n +2 "$WIKI_DIR/temp.md" | head -n 100
            echo ""
        fi
        
        # Installation docs
        if [ -d "$platform_dir/docs/installation" ]; then
            echo "## Installation"
            echo ""
            
            # Platform-specific install guide
            local install_file=""
            case "$platform_name" in
                macOS) install_file="$platform_dir/docs/installation/INSTALL_MACOS.md" ;;
                Windows) install_file="$platform_dir/docs/installation/INSTALL_WINDOWS.md" ;;
                Linux) install_file="$platform_dir/docs/installation/INSTALL_LINUX.md" ;;
            esac
            
            if [ -f "$install_file" ]; then
                convert_markdown_for_wiki "$install_file" "$WIKI_DIR/temp.md"
                cat "$WIKI_DIR/temp.md" | head -n 200
                echo ""
            fi
            
            # Quick Start
            if [ -f "$platform_dir/docs/installation/QUICK_START.md" ]; then
                echo "### Quick Start"
                echo ""
                convert_markdown_for_wiki "$platform_dir/docs/installation/QUICK_START.md" "$WIKI_DIR/temp.md"
                cat "$WIKI_DIR/temp.md" | head -n 150
                echo ""
            fi
        fi
        
        # Additional documentation
        if [ -d "$platform_dir/docs" ]; then
            echo "## Additional Documentation"
            echo ""
            
            # API
            if [ -f "$platform_dir/docs/API.md" ]; then
                echo "### API Reference"
                echo ""
                convert_markdown_for_wiki "$platform_dir/docs/API.md" "$WIKI_DIR/temp.md"
                head -n 100 "$WIKI_DIR/temp.md"
                echo ""
                echo "*[Full API documentation available in distribution]*"
                echo ""
            fi
            
            # Troubleshooting
            if [ -d "$platform_dir/docs/troubleshooting" ]; then
                echo "### Troubleshooting"
                echo ""
                if [ -f "$platform_dir/docs/troubleshooting/README.md" ]; then
                    convert_markdown_for_wiki "$platform_dir/docs/troubleshooting/README.md" "$WIKI_DIR/temp.md"
                    head -n 80 "$WIKI_DIR/temp.md"
                    echo ""
                fi
            fi
            
            # Guides
            for guide in BEGINNER_GUIDE.md INTERMEDIATE_GUIDE.md EXPERT_GUIDE.md; do
                if [ -f "$platform_dir/docs/$guide" ]; then
                    local guide_name=$(echo "$guide" | sed 's/_/ /g' | sed 's/\.md//')
                    echo "### $guide_name"
                    echo ""
                    convert_markdown_for_wiki "$platform_dir/docs/$guide" "$WIKI_DIR/temp.md"
                    head -n 60 "$WIKI_DIR/temp.md"
                    echo ""
                    echo "*[Full guide available in distribution]*"
                    echo ""
                fi
            done
        fi
        
        echo "---"
        echo ""
        echo "## Related Pages"
        echo ""
        echo "- [Home](Home)"
        echo "- [Windows](Windows) (if applicable)"
        echo "- [Linux](Linux) (if applicable)"
        echo "- [macOS](macOS) (if applicable)"
        echo "- [Containers](Containers)"
        
    } > "$wiki_file"
}

# Create containers wiki page
create_containers_wiki() {
    local containers_dir="$1"
    local wiki_file="$2"
    
    print_info "Creating Containers wiki page..."
    
    {
        echo "# Container Platforms"
        echo ""
        echo "Complete documentation for deploying StreamTV using container platforms."
        echo ""
        
        # Main README
        if [ -f "$containers_dir/README.md" ]; then
            echo "## Overview"
            echo ""
            convert_markdown_for_wiki "$containers_dir/README.md" "$WIKI_DIR/temp.md"
            cat "$WIKI_DIR/temp.md"
            echo ""
        fi
        
        # Docker
        if [ -d "$containers_dir/docker" ]; then
            echo "## Docker"
            echo ""
            if [ -f "$containers_dir/docker/README.md" ]; then
                convert_markdown_for_wiki "$containers_dir/docker/README.md" "$WIKI_DIR/temp.md"
                head -n 150 "$WIKI_DIR/temp.md"
                echo ""
            fi
        fi
        
        # Docker Compose
        if [ -d "$containers_dir/docker-compose" ]; then
            echo "## Docker Compose"
            echo ""
            if [ -f "$containers_dir/docker-compose/README.md" ]; then
                convert_markdown_for_wiki "$containers_dir/docker-compose/README.md" "$WIKI_DIR/temp.md"
                head -n 120 "$WIKI_DIR/temp.md"
                echo ""
            fi
        fi
        
        # Kubernetes
        if [ -d "$containers_dir/kubernetes" ]; then
            echo "## Kubernetes"
            echo ""
            if [ -f "$containers_dir/kubernetes/README.md" ]; then
                convert_markdown_for_wiki "$containers_dir/kubernetes/README.md" "$WIKI_DIR/temp.md"
                head -n 150 "$WIKI_DIR/temp.md"
                echo ""
            fi
        fi
        
        # Podman
        if [ -d "$containers_dir/podman" ]; then
            echo "## Podman"
            echo ""
            if [ -f "$containers_dir/podman/README.md" ]; then
                convert_markdown_for_wiki "$containers_dir/podman/README.md" "$WIKI_DIR/temp.md"
                head -n 120 "$WIKI_DIR/temp.md"
                echo ""
            fi
        fi
        
        echo "---"
        echo ""
        echo "## Related Pages"
        echo ""
        echo "- [Home](Home)"
        echo "- [macOS](macOS)"
        echo "- [Windows](Windows)"
        echo "- [Linux](Linux)"
        
    } > "$wiki_file"
}

# Create documentation index page
create_documentation_index() {
    local wiki_file="$1"
    local docs_dir="$SCRIPT_DIR/docs"
    
    print_info "Creating Documentation Index..."
    
    {
        echo "# Complete Documentation Index"
        echo ""
        echo "Complete guide to all StreamTV documentation, organized by topic."
        echo ""
        
        if [ -f "$docs_dir/INDEX.md" ]; then
            convert_markdown_for_wiki "$docs_dir/INDEX.md" "$WIKI_DIR/temp.md"
            cat "$WIKI_DIR/temp.md"
        else
            echo "## Core Documentation"
            echo ""
            echo "- [API Reference](API-Reference)"
            echo "- [Troubleshooting](Troubleshooting)"
            echo "- [Schedules](Schedules)"
            echo "- [Authentication](Authentication)"
            echo ""
        fi
    } > "$wiki_file"
}

# Create scripts documentation page
create_scripts_documentation() {
    local wiki_file="$1"
    local scripts_dir="$SCRIPT_DIR/scripts"
    
    print_info "Creating Scripts Documentation..."
    
    {
        echo "# Scripts and Tools"
        echo ""
        echo "Complete documentation for all StreamTV utility scripts and tools."
        echo ""
        
        # Scripts README
        if [ -f "$scripts_dir/README.md" ]; then
            convert_markdown_for_wiki "$scripts_dir/README.md" "$WIKI_DIR/temp.md"
            cat "$WIKI_DIR/temp.md"
            echo ""
        fi
        
        echo "## Available Scripts"
        echo ""
        
        # Shell scripts
        echo "### Shell Scripts"
        echo ""
        echo "#### Installation & Setup"
        echo "- \`install_macos.sh\` - macOS installation"
        echo "- \`start_server.sh\` - Start StreamTV server"
        echo "- \`verify-installation.sh\` - Verify installation"
        echo ""
        echo "#### Channel Management"
        echo "- \`create_channel.sh\` - Create channels via API"
        echo "- \`create_schedule.sh\` - Create schedule files"
        echo ""
        echo "#### Archive.org Parser"
        echo "- \`archive_collection_parser_dialog.sh\` - Interactive GUI parser"
        echo ""
        echo "#### Troubleshooting"
        echo "- \`view-logs.sh\` - View application logs"
        echo "- \`troubleshoot_streamtv.sh\` - StreamTV diagnostics"
        echo "- \`troubleshoot_plex.sh\` - Plex integration diagnostics"
        echo "- \`stop_server.sh\` - Stop running server"
        echo ""
        echo "#### GitHub & Distribution"
        echo "- \`upload-to-github.sh\` - Upload distributions to GitHub"
        echo "- \`create-wiki.sh\` - Create GitHub wiki"
        echo "- \`fix-unrelated-histories.sh\` - Fix git history issues"
        echo "- \`push-distributions.sh\` - Push distributions to GitHub"
        echo ""
        
        # Python scripts
        echo "### Python Scripts"
        echo ""
        echo "#### Channel Management"
        echo "- \`create_channel.py\` - Create channels programmatically"
        echo "- \`import_channels.py\` - Import channels from YAML"
        echo "- \`import_collections.py\` - Import collections"
        echo "- \`rename_channels.py\` - Rename existing channels"
        echo "- \`remove_tpt_channels.py\` - Remove specific channels"
        echo ""
        echo "#### Archive.org Integration"
        echo "- \`archive_collection_parser.py\` - Parse Archive.org collections"
        echo "- \`create_sesame_street_channel.py\` - Create Sesame Street channel"
        echo "- \`create_mister_rogers_channel.py\` - Create Mister Rogers channel"
        echo ""
        echo "#### Channel Rebuilding"
        echo "- \`rebuild_1980_channel.py\` - Rebuild 1980 channel"
        echo "- \`recreate_1980_channel.py\` - Recreate 1980 channel"
        echo "- \`recreate_1992_channel.py\` - Recreate 1992 channel"
        echo "- \`full_rebuild_1980.py\` - Full rebuild of 1980 channel"
        echo "- \`complete_rebuild_1980.py\` - Complete rebuild of 1980 channel"
        echo ""
        echo "#### Metadata & Data"
        echo "- \`enrich_metadata.py\` - Enrich media metadata"
        echo "- \`update_metadata.py\` - Update existing metadata"
        echo "- \`import_olympics_data.py\` - Import Olympics data"
        echo "- \`cleanup_placeholders.py\` - Clean up placeholder entries"
        echo ""
        echo "#### Plex Integration"
        echo "- \`discover_plex.py\` - Discover Plex servers"
        echo "- \`get_plex_token.py\` - Get Plex authentication token"
        echo "- \`test_plex_connection.py\` - Test Plex connectivity"
        echo ""
        echo "#### Utilities"
        echo "- \`health_check.py\` - System health check"
        echo "- \`hardware_detection.py\` - Detect hardware capabilities"
        echo "- \`test_logging.py\` - Test logging system"
        echo "- \`test_connectivity.py\` - Test network connectivity"
        echo "- \`auto_heal.py\` - Auto-healing system"
        echo "- \`add_playout_mode_migration.py\` - Database migration"
        echo ""
        
        echo "## Usage Examples"
        echo ""
        echo "### Create a Channel"
        echo "\`\`\`bash"
        echo "# Using shell script (requires API server)"
        echo "./scripts/create_channel.sh --year 1980"
        echo ""
        echo "# Using Python script (direct database)"
        echo "python3 scripts/create_channel.py --year 1980"
        echo "\`\`\`"
        echo ""
        echo "### Parse Archive.org Collection"
        echo "\`\`\`bash"
        echo "# Interactive GUI (recommended)"
        echo "./scripts/archive_collection_parser_dialog.sh"
        echo ""
        echo "# Command-line"
        echo "python3 scripts/archive_collection_parser.py \"https://archive.org/details/...\""
        echo "\`\`\`"
        echo ""
        echo "### View Logs"
        echo "\`\`\`bash"
        echo "# Live view"
        echo "./scripts/view-logs.sh"
        echo ""
        echo "# Search for errors"
        echo "./scripts/view-logs.sh search ERROR"
        echo "\`\`\`"
        echo ""
        echo "### Import Channels"
        echo "\`\`\`bash"
        echo "python3 scripts/import_channels.py data/channels.yaml"
        echo "\`\`\`"
        echo ""
        echo "## Related Pages"
        echo ""
        echo "- [Home](Home)"
        echo "- [Archive Parser](Archive-Parser)"
        echo "- [Logging](Logging)"
        echo "- [Plex Integration](Plex-Integration)"
        
    } > "$wiki_file"
}

# Create archive parser documentation
create_archive_parser_docs() {
    local wiki_file="$1"
    local docs_dir="$SCRIPT_DIR/docs/archive-parser"
    
    print_info "Creating Archive Parser Documentation..."
    
    {
        echo "# Archive.org Channel Parser"
        echo ""
        echo "Create channels from Archive.org collections automatically."
        echo ""
        
        if [ -d "$docs_dir" ]; then
            # Quick reference
            if [ -f "$docs_dir/QUICK_REFERENCE_ARCHIVE_PARSER.md" ]; then
                echo "## Quick Reference"
                echo ""
                convert_markdown_for_wiki "$docs_dir/QUICK_REFERENCE_ARCHIVE_PARSER.md" "$WIKI_DIR/temp.md"
                cat "$WIKI_DIR/temp.md"
                echo ""
            fi
            
            # All other docs
            for doc in "$docs_dir"/*.md; do
                if [ -f "$doc" ] && [ "$(basename "$doc")" != "README.md" ]; then
                    local docname=$(basename "$doc" .md | tr '_' ' ' | sed 's/\b\w/\u&/g')
                    echo "## $docname"
                    echo ""
                    convert_markdown_for_wiki "$doc" "$WIKI_DIR/temp.md"
                    head -n 200 "$WIKI_DIR/temp.md"
                    echo ""
                    echo "---"
                    echo ""
                fi
            done
        else
            echo "Documentation directory not found."
        fi
        
        echo "## Related Pages"
        echo ""
        echo "- [Scripts and Tools](Scripts-and-Tools)"
        echo "- [Home](Home)"
        
    } > "$wiki_file"
}

# Create logging documentation
create_logging_docs() {
    local wiki_file="$1"
    local docs_dir="$SCRIPT_DIR/docs/logging"
    
    print_info "Creating Logging Documentation..."
    
    {
        echo "# Logging System"
        echo ""
        echo "Comprehensive logging system for StreamTV."
        echo ""
        
        if [ -d "$docs_dir" ]; then
            # Quick start
            if [ -f "$docs_dir/LOGGING_QUICKSTART.md" ]; then
                echo "## Quick Start"
                echo ""
                convert_markdown_for_wiki "$docs_dir/LOGGING_QUICKSTART.md" "$WIKI_DIR/temp.md"
                cat "$WIKI_DIR/temp.md"
                echo ""
            fi
            
            # All other docs
            for doc in "$docs_dir"/*.md; do
                if [ -f "$doc" ] && [ "$(basename "$doc")" != "README.md" ] && [ "$(basename "$doc")" != "LOGGING_QUICKSTART.md" ]; then
                    local docname=$(basename "$doc" .md | tr '_' ' ' | sed 's/\b\w/\u&/g')
                    echo "## $docname"
                    echo ""
                    convert_markdown_for_wiki "$doc" "$WIKI_DIR/temp.md"
                    head -n 150 "$WIKI_DIR/temp.md"
                    echo ""
                    echo "---"
                    echo ""
                fi
            done
        fi
        
        echo "## Related Pages"
        echo ""
        echo "- [Scripts and Tools](Scripts-and-Tools)"
        echo "- [Home](Home)"
        
    } > "$wiki_file"
}

# Create Plex integration documentation
create_plex_docs() {
    local wiki_file="$1"
    local docs_dir="$SCRIPT_DIR/docs/plex"
    
    print_info "Creating Plex Integration Documentation..."
    
    {
        echo "# Plex Integration"
        echo ""
        echo "Complete Plex Media Server integration documentation."
        echo ""
        
        if [ -d "$docs_dir" ]; then
            # Setup guide first
            if [ -f "$docs_dir/PLEX_SETUP_COMPLETE.md" ]; then
                echo "## Setup Guide"
                echo ""
                convert_markdown_for_wiki "$docs_dir/PLEX_SETUP_COMPLETE.md" "$WIKI_DIR/temp.md"
                head -n 200 "$WIKI_DIR/temp.md"
                echo ""
                echo "---"
                echo ""
            fi
            
            # All other docs
            for doc in "$docs_dir"/*.md; do
                if [ -f "$doc" ] && [ "$(basename "$doc")" != "README.md" ] && [ "$(basename "$doc")" != "PLEX_SETUP_COMPLETE.md" ]; then
                    local docname=$(basename "$doc" .md | tr '_' ' ' | sed 's/\b\w/\u&/g')
                    echo "## $docname"
                    echo ""
                    convert_markdown_for_wiki "$doc" "$WIKI_DIR/temp.md"
                    head -n 150 "$WIKI_DIR/temp.md"
                    echo ""
                    echo "---"
                    echo ""
                fi
            done
        fi
        
        echo "## Related Pages"
        echo ""
        echo "- [Scripts and Tools](Scripts-and-Tools)"
        echo "- [Home](Home)"
        
    } > "$wiki_file"
}

# Create installation documentation
create_installation_docs() {
    local wiki_file="$1"
    local docs_dir="$SCRIPT_DIR/docs/installation"
    
    print_info "Creating Installation Documentation..."
    
    {
        echo "# Installation Guide"
        echo ""
        echo "Complete installation documentation for all platforms."
        echo ""
        
        if [ -d "$docs_dir" ]; then
            # Quick start first
            if [ -f "$docs_dir/QUICK_START.md" ]; then
                echo "## Quick Start"
                echo ""
                convert_markdown_for_wiki "$docs_dir/QUICK_START.md" "$WIKI_DIR/temp.md"
                head -n 150 "$WIKI_DIR/temp.md"
                echo ""
                echo "---"
                echo ""
            fi
            
            # All other docs
            for doc in "$docs_dir"/*.md; do
                if [ -f "$doc" ] && [ "$(basename "$doc")" != "README.md" ] && [ "$(basename "$doc")" != "QUICK_START.md" ]; then
                    local docname=$(basename "$doc" .md | tr '_' ' ' | sed 's/\b\w/\u&/g')
                    echo "## $docname"
                    echo ""
                    convert_markdown_for_wiki "$doc" "$WIKI_DIR/temp.md"
                    head -n 150 "$WIKI_DIR/temp.md"
                    echo ""
                    echo "---"
                    echo ""
                fi
            done
        fi
        
        echo "## Related Pages"
        echo ""
        echo "- [macOS](macOS)"
        echo "- [Windows](Windows)"
        echo "- [Linux](Linux)"
        echo "- [Home](Home)"
        
    } > "$wiki_file"
}

# Create SwiftUI documentation
create_swiftui_docs() {
    local wiki_file="$1"
    local docs_dir="$SCRIPT_DIR/docs/swiftui"
    
    print_info "Creating SwiftUI Documentation..."
    
    {
        echo "# SwiftUI Applications"
        echo ""
        echo "Documentation for StreamTV SwiftUI applications and installers."
        echo ""
        
        if [ -d "$docs_dir" ]; then
            for doc in "$docs_dir"/*.md; do
                if [ -f "$doc" ]; then
                    local docname=$(basename "$doc" .md | tr '_' ' ' | sed 's/\b\w/\u&/g')
                    echo "## $docname"
                    echo ""
                    convert_markdown_for_wiki "$doc" "$WIKI_DIR/temp.md"
                    cat "$WIKI_DIR/temp.md"
                    echo ""
                    echo "---"
                    echo ""
                fi
            done
        fi
        
        echo "## Related Pages"
        echo ""
        echo "- [Installation Guide](Installation-Guide)"
        echo "- [Home](Home)"
        
    } > "$wiki_file"
}

# Create core documentation page
create_core_doc_page() {
    local title="$1"
    local doc_file="$2"
    local wiki_file="$3"
    
    if [ ! -f "$doc_file" ]; then
        return 1
    fi
    
    print_info "Creating $title page..."
    
    {
        echo "# $title"
        echo ""
        convert_markdown_for_wiki "$doc_file" "$WIKI_DIR/temp.md"
        cat "$WIKI_DIR/temp.md"
        echo ""
        echo "---"
        echo ""
        echo "## Related Pages"
        echo ""
        echo "- [Documentation Index](Documentation-Index)"
        echo "- [Home](Home)"
        
    } > "$wiki_file"
}

# Create implementation documentation
create_implementation_docs() {
    local wiki_file="$1"
    local docs_dir="$SCRIPT_DIR/docs/implementation"
    
    print_info "Creating Implementation Documentation..."
    
    {
        echo "# Implementation & Technical Details"
        echo ""
        echo "Technical implementation documentation for developers and engineers."
        echo ""
        
        if [ -d "$docs_dir" ]; then
            for doc in "$docs_dir"/*.md; do
                if [ -f "$doc" ] && [ "$(basename "$doc")" != "README.md" ]; then
                    local docname=$(basename "$doc" .md | tr '_' ' ' | sed 's/\b\w/\u&/g')
                    echo "## $docname"
                    echo ""
                    convert_markdown_for_wiki "$doc" "$WIKI_DIR/temp.md"
                    head -n 200 "$WIKI_DIR/temp.md"
                    echo ""
                    echo "*[Full document available in repository]*"
                    echo ""
                    echo "---"
                    echo ""
                fi
            done
        fi
        
        echo "## Related Pages"
        echo ""
        echo "- [Documentation Index](Documentation-Index)"
        echo "- [Home](Home)"
        
    } > "$wiki_file"
}

# Create wiki Home page
create_wiki_home() {
    local wiki_file="$1"
    
    print_info "Creating wiki Home page..."
    
    cat > "$wiki_file" << 'EOF'
# StreamTV Platform Documentation

Welcome to the StreamTV platform documentation wiki. This wiki contains comprehensive documentation for all platform distributions.

## 📦 Platform Distributions

### Desktop Platforms

- **[macOS](macOS)** - Native macOS distribution with full documentation
- **[Windows](Windows)** - Windows distribution with PowerShell and Batch scripts
- **[Linux](Linux)** - Linux distribution with systemd integration

### Container Platforms

- **[Containers](Containers)** - Docker, Docker Compose, Kubernetes, and Podman deployments

## 🚀 Quick Links

### Getting Started
- Choose your platform above for installation instructions
- Each platform includes Quick Start guides
- Platform-specific troubleshooting guides available

### Documentation
- Complete API documentation in each distribution
- Beginner, Intermediate, and Expert guides
- Authentication and security documentation
- HDHomeRun and Plex integration guides

## 📚 Documentation Structure

Each platform distribution includes:
- **Installation Guides** - Step-by-step setup instructions
- **Quick Start** - Get running in minutes
- **API Reference** - Complete API documentation
- **Troubleshooting** - Common issues and solutions
- **Advanced Guides** - For power users and developers

## 🔗 Repository

Main repository: [https://github.com/roto31/StreamTV](https://github.com/roto31/StreamTV)

## 📖 Platform Pages

- [macOS Platform](macOS)
- [Windows Platform](Windows)
- [Linux Platform](Linux)
- [Container Platforms](Containers)

## 📚 Complete Documentation

### Documentation Index
- **[Documentation Index](Documentation-Index)** - Complete guide to all documentation

### Core Documentation
- **[API Reference](API-Reference)** - Complete API documentation
- **[Troubleshooting](Troubleshooting)** - Common issues and solutions
- **[Schedules](Schedules)** - Schedule creation and management
- **[Authentication](Authentication)** - Authentication setup
- **[Authentication System](Authentication-System)** - Advanced authentication

### User Guides
- **[Beginner Guide](Beginner-Guide)** - For new users
- **[Intermediate Guide](Intermediate-Guide)** - For technicians
- **[Expert Guide](Expert-Guide)** - For developers

### Tools & Scripts
- **[Scripts and Tools](Scripts-and-Tools)** - All utility scripts and how to use them
- **[Archive Parser](Archive-Parser)** - Create channels from Archive.org
- **[Logging](Logging)** - Logging system documentation

### Integrations
- **[Plex Integration](Plex-Integration)** - Plex Media Server integration

### Platform-Specific
- **[Installation Guide](Installation-Guide)** - Installation for all platforms
- **[SwiftUI](SwiftUI)** - SwiftUI applications and installers

### Technical
- **[Implementation](Implementation)** - Technical implementation details
EOF
}

# Main function
main() {
    print_header "Create GitHub Wiki for StreamTV"
    
    # Check prerequisites
    print_info "Repository: $GITHUB_USER/$REPO_NAME"
    print_info "Wiki URL: https://github.com/$GITHUB_USER/$REPO_NAME/wiki"
    echo ""
    
    # Check if wiki is enabled
    print_warning "IMPORTANT: Wiki must be enabled in repository settings!"
    print_info "Go to: https://github.com/$GITHUB_USER/$REPO_NAME/settings"
    print_info "Scroll to 'Features' → Enable 'Wikis'"
    echo ""
    read -p "Is wiki enabled? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_error "Please enable wiki first, then run this script again"
        print_info "Settings URL: https://github.com/$GITHUB_USER/$REPO_NAME/settings"
        exit 1
    fi
    
    # Check distribution folders
    print_header "Checking Distribution Folders"
    
    if [ ! -d "$SCRIPT_DIR/StreamTV-macOS" ]; then
        print_error "StreamTV-macOS not found"
        exit 1
    fi
    if [ ! -d "$SCRIPT_DIR/StreamTV-Windows" ]; then
        print_error "StreamTV-Windows not found"
        exit 1
    fi
    if [ ! -d "$SCRIPT_DIR/StreamTV-Linux" ]; then
        print_error "StreamTV-Linux not found"
        exit 1
    fi
    if [ ! -d "$SCRIPT_DIR/StreamTV-Containers" ]; then
        print_error "StreamTV-Containers not found"
        exit 1
    fi
    
    print_success "All distribution folders found"
    
    # Clean up and create wiki directory
    print_header "Preparing Wiki"
    rm -rf "$WIKI_DIR"
    mkdir -p "$WIKI_DIR"
    
    # Clone or create wiki repository
    local wiki_url="https://github.com/$GITHUB_USER/$REPO_NAME.wiki.git"
    print_info "Wiki repository URL: $wiki_url"
    echo ""
    
    print_info "Attempting to clone wiki repository..."
    if git clone "$wiki_url" "$WIKI_DIR" 2>/dev/null; then
        print_success "Wiki repository cloned"
        cd "$WIKI_DIR"
    else
        print_warning "Wiki repository doesn't exist yet (this is normal for new wikis)"
        print_info "GitHub will create it when we push the first page"
        print_info "Creating new wiki repository locally..."
        mkdir -p "$WIKI_DIR"
        cd "$WIKI_DIR"
        git init -b main
        git remote add origin "$wiki_url" 2>/dev/null || git remote set-url origin "$wiki_url"
        print_info "Local wiki repository initialized"
    fi
    
    # Create wiki pages
    print_header "Creating Wiki Pages"
    
    create_wiki_home "$WIKI_DIR/Home.md"
    print_success "Created Home.md"
    
    create_platform_wiki "macOS" "$SCRIPT_DIR/StreamTV-macOS" "$WIKI_DIR/macOS.md"
    print_success "Created macOS.md"
    
    create_platform_wiki "Windows" "$SCRIPT_DIR/StreamTV-Windows" "$WIKI_DIR/Windows.md"
    print_success "Created Windows.md"
    
    create_platform_wiki "Linux" "$SCRIPT_DIR/StreamTV-Linux" "$WIKI_DIR/Linux.md"
    print_success "Created Linux.md"
    
    create_containers_wiki "$SCRIPT_DIR/StreamTV-Containers" "$WIKI_DIR/Containers.md"
    print_success "Created Containers.md"
    
    # Create comprehensive documentation pages
    print_header "Creating Documentation Pages"
    
    create_documentation_index "$WIKI_DIR/Documentation-Index.md"
    print_success "Created Documentation-Index.md"
    
    create_scripts_documentation "$WIKI_DIR/Scripts-and-Tools.md"
    print_success "Created Scripts-and-Tools.md"
    
    create_archive_parser_docs "$WIKI_DIR/Archive-Parser.md"
    print_success "Created Archive-Parser.md"
    
    create_logging_docs "$WIKI_DIR/Logging.md"
    print_success "Created Logging.md"
    
    create_plex_docs "$WIKI_DIR/Plex-Integration.md"
    print_success "Created Plex-Integration.md"
    
    create_installation_docs "$WIKI_DIR/Installation-Guide.md"
    print_success "Created Installation-Guide.md"
    
    create_swiftui_docs "$WIKI_DIR/SwiftUI.md"
    print_success "Created SwiftUI.md"
    
    create_implementation_docs "$WIKI_DIR/Implementation.md"
    print_success "Created Implementation.md"
    
    # Create core documentation pages
    print_header "Creating Core Documentation Pages"
    
    create_core_doc_page "API" "$SCRIPT_DIR/docs/API.md" "$WIKI_DIR/API-Reference.md"
    print_success "Created API-Reference.md"
    
    create_core_doc_page "Troubleshooting" "$SCRIPT_DIR/docs/TROUBLESHOOTING.md" "$WIKI_DIR/Troubleshooting.md"
    print_success "Created Troubleshooting.md"
    
    create_core_doc_page "Schedules" "$SCRIPT_DIR/docs/SCHEDULES.md" "$WIKI_DIR/Schedules.md"
    print_success "Created Schedules.md"
    
    create_core_doc_page "Authentication" "$SCRIPT_DIR/docs/AUTHENTICATION.md" "$WIKI_DIR/Authentication.md"
    print_success "Created Authentication.md"
    
    create_core_doc_page "Authentication System" "$SCRIPT_DIR/docs/AUTHENTICATION_SYSTEM.md" "$WIKI_DIR/Authentication-System.md"
    print_success "Created Authentication-System.md"
    
    create_core_doc_page "Beginner Guide" "$SCRIPT_DIR/docs/BEGINNER_GUIDE.md" "$WIKI_DIR/Beginner-Guide.md"
    print_success "Created Beginner-Guide.md"
    
    create_core_doc_page "Intermediate Guide" "$SCRIPT_DIR/docs/INTERMEDIATE_GUIDE.md" "$WIKI_DIR/Intermediate-Guide.md"
    print_success "Created Intermediate-Guide.md"
    
    create_core_doc_page "Expert Guide" "$SCRIPT_DIR/docs/EXPERT_GUIDE.md" "$WIKI_DIR/Expert-Guide.md"
    print_success "Created Expert-Guide.md"
    
    # Add and commit
    print_header "Committing Wiki Pages"
    
    git add -A 2>/dev/null || true
    
    if git diff --staged --quiet 2>/dev/null; then
        print_warning "No changes to commit"
    else
        git commit -m "Add StreamTV platform documentation wiki" || true
        print_success "Wiki pages committed"
    fi
    
    # Push
    print_header "Pushing Wiki to GitHub"
    print_info "Wiki URL: https://github.com/$GITHUB_USER/$REPO_NAME/wiki"
    echo ""
    
    read -p "Push wiki now? (Y/n): " -n 1 -r
    echo
    echo ""
    
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_info "Wiki files are ready in: $WIKI_DIR"
        print_info "Push manually with:"
        print_info "  cd $WIKI_DIR"
        print_info "  git push -u origin master"
        print_info "  # or: git push -u origin main"
        exit 0
    fi
    
    # Try to push
    print_info "Pushing wiki..."
    print_info "Note: If this is the first push, GitHub will create the wiki repository"
    echo ""
    
    # Determine which branch to use
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
    print_info "Current branch: $CURRENT_BRANCH"
    
    # Try pushing to current branch first
    PUSH_OUTPUT=$(git push -u origin "$CURRENT_BRANCH" 2>&1)
    PUSH_EXIT=$?
    
    if [ $PUSH_EXIT -eq 0 ]; then
        print_success "Wiki pushed successfully to $CURRENT_BRANCH branch!"
    else
        # Try master (GitHub wikis sometimes use master)
        print_info "Trying master branch..."
        git checkout -b master 2>/dev/null || git checkout master 2>/dev/null || true
        PUSH_OUTPUT=$(git push -u origin master 2>&1)
        PUSH_EXIT=$?
        
        if [ $PUSH_EXIT -eq 0 ]; then
            print_success "Wiki pushed successfully to master branch!"
        else
            # Try main
            print_info "Trying main branch..."
            git checkout -b main 2>/dev/null || git checkout main 2>/dev/null || true
            PUSH_OUTPUT=$(git push -u origin main 2>&1)
            PUSH_EXIT=$?
            
            if [ $PUSH_EXIT -eq 0 ]; then
                print_success "Wiki pushed successfully to main branch!"
            else
                # Show error
                print_error "All push attempts failed"
                
                if echo "$PUSH_OUTPUT" | grep -qiE "authentication|permission|denied|401|403"; then
                print_error "Authentication required"
                echo ""
                print_info "Authenticate with GitHub CLI:"
                print_info "  gh auth login"
                echo ""
                print_info "Or use personal access token:"
                print_info "  1. Create token: https://github.com/settings/tokens"
                print_info "  2. Use in URL: https://TOKEN@github.com/$GITHUB_USER/$REPO_NAME.wiki.git"
                print_info "  3. Push manually: cd $WIKI_DIR && git push -u origin master"
            elif echo "$PUSH_OUTPUT" | grep -qiE "not found|404"; then
                print_error "Wiki repository not found (404)"
                print_info "Wiki may not be enabled. Enable it at:"
                print_info "  https://github.com/$GITHUB_USER/$REPO_NAME/settings"
                print_info "  Features → Wikis → Enable"
            else
                print_error "Push failed"
                print_info "Error:"
                echo "$PUSH_OUTPUT" | head -5
                echo ""
                print_info "Wiki files are ready in: $WIKI_DIR"
                print_info "Push manually:"
                print_info "  cd $WIKI_DIR"
                print_info "  git push -u origin master"
                fi
                exit 1
            fi
        fi
    fi
    
    # Success!
    print_header "Wiki Created Successfully!"
    
    echo ""
    print_success "Wiki is now available at:"
    print_info "  https://github.com/$GITHUB_USER/$REPO_NAME/wiki"
    echo ""
    print_info "Pages created:"
    echo ""
    print_info "Platform Pages:"
    print_info "  - Home"
    print_info "  - macOS"
    print_info "  - Windows"
    print_info "  - Linux"
    print_info "  - Containers"
    echo ""
    print_info "Documentation Pages:"
    print_info "  - Documentation-Index"
    print_info "  - Scripts-and-Tools"
    print_info "  - Archive-Parser"
    print_info "  - Logging"
    print_info "  - Plex-Integration"
    print_info "  - Installation-Guide"
    print_info "  - SwiftUI"
    print_info "  - Implementation"
    echo ""
    print_info "Core Documentation:"
    print_info "  - API-Reference"
    print_info "  - Troubleshooting"
    print_info "  - Schedules"
    print_info "  - Authentication"
    print_info "  - Authentication-System"
    print_info "  - Beginner-Guide"
    print_info "  - Intermediate-Guide"
    print_info "  - Expert-Guide"
    echo ""
    print_info "Visit the wiki to verify:"
    print_info "  https://github.com/$GITHUB_USER/$REPO_NAME/wiki/Home"
    
    # Clean up on success
    cd "$SCRIPT_DIR"
    rm -rf "$WIKI_DIR"
    print_info "Temporary files cleaned up"
}

# Run main function
main "$@"
