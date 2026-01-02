#!/bin/bash
#
# Copy Python files preserving directory structure
# This script copies the streamtv directory to Resources/streamtv/
# while maintaining the full directory hierarchy
# It also removes any Python files that the file system synchronized group
# may have copied to Resources with flattened structure
#

set -euo pipefail

# Source is now outside the synchronized group path to prevent conflicts
SOURCE_DIR="${PROJECT_DIR}/StreamTV/streamtv_source"
# Fallback to hidden version if source doesn't exist
if [ ! -d "${SOURCE_DIR}" ]; then
    SOURCE_DIR="${PROJECT_DIR}/StreamTV/StreamTV/.streamtv_hidden"
fi
# Final fallback to original location
if [ ! -d "${SOURCE_DIR}" ]; then
    SOURCE_DIR="${PROJECT_DIR}/StreamTV/StreamTV/streamtv"
fi
DEST_DIR="${TARGET_BUILD_DIR}/${UNLOCALIZED_RESOURCES_FOLDER_PATH}/streamtv"
RESOURCES_DIR="${TARGET_BUILD_DIR}/${UNLOCALIZED_RESOURCES_FOLDER_PATH}"

echo "Copying Python files with directory structure preserved..."

# First, remove any Python files that the file system synchronized group
# may have copied to Resources with flattened structure during the Resources phase
# This prevents "Multiple commands produce" errors
echo "  Removing any flattened Python files from Resources (from file system sync group)..."
if [ -d "${RESOURCES_DIR}" ]; then
    # Remove all .py files from Resources root (these are from flattened structure)
    find "${RESOURCES_DIR}" -maxdepth 1 -name "*.py" -type f -delete 2>/dev/null || true
    # Also remove any __init__.py that might have been copied
    find "${RESOURCES_DIR}" -maxdepth 1 -name "__init__.py" -type f -delete 2>/dev/null || true
    # Remove any Python files from subdirectories that aren't in streamtv/
    # (in case the sync group created other Python file copies)
    find "${RESOURCES_DIR}" -mindepth 2 -maxdepth 2 -name "*.py" -type f ! -path "*/streamtv/*" -delete 2>/dev/null || true
fi

# Remove old copy if it exists
if [ -d "${DEST_DIR}" ]; then
    rm -rf "${DEST_DIR}"
fi

# Create destination directory
mkdir -p "${DEST_DIR}"

# Check if source directory exists
if [ ! -d "${SOURCE_DIR}" ]; then
    echo "Warning: Source directory ${SOURCE_DIR} does not exist"
    exit 0
fi

# Copy files preserving structure, excluding cache files and duplicates
if command -v rsync &> /dev/null; then
    # Use rsync for efficient copying with exclusions
    rsync -av \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='*.pyo' \
        --exclude='* 2.py' \
        --exclude='* 2.pyc' \
        --exclude='*.html' \
        "${SOURCE_DIR}/" "${DEST_DIR}/"
else
    # Fallback using find and cp
    cd "${SOURCE_DIR}"
    find . -type f \
        -name "*.py" \
        ! -name "* 2.py" \
        ! -path "*/__pycache__/*" \
        ! -name "*.pyc" \
        ! -name "*.pyo" | while read -r file; do
        dest_file="${DEST_DIR}/${file}"
        mkdir -p "$(dirname "${dest_file}")"
        cp "${file}" "${dest_file}"
    done
fi

echo "Python files copied successfully to ${DEST_DIR}"

# Copy bundled dependencies (Python framework and FFmpeg)
echo "Copying bundled dependencies..."

# Copy Python framework if it exists
BUNDLED_PYTHON_SOURCE="${PROJECT_DIR}/StreamTV/StreamTV/Resources/python"
BUNDLED_PYTHON_DEST="${RESOURCES_DIR}/python"
if [ -d "${BUNDLED_PYTHON_SOURCE}" ]; then
    echo "  Copying Python framework..."
    if [ -d "${BUNDLED_PYTHON_DEST}" ]; then
        rm -rf "${BUNDLED_PYTHON_DEST}"
    fi
    mkdir -p "${BUNDLED_PYTHON_DEST}"
    cp -R "${BUNDLED_PYTHON_SOURCE}/"* "${BUNDLED_PYTHON_DEST}/" 2>/dev/null || true
    echo "  Python framework copied to ${BUNDLED_PYTHON_DEST}"
else
    echo "  Warning: Bundled Python framework not found at ${BUNDLED_PYTHON_SOURCE}"
fi

# Copy FFmpeg binaries if they exist
BUNDLED_FFMPEG_SOURCE="${PROJECT_DIR}/StreamTV/StreamTV/Resources/ffmpeg"
BUNDLED_FFMPEG_DEST="${RESOURCES_DIR}/ffmpeg"
if [ -d "${BUNDLED_FFMPEG_SOURCE}" ]; then
    echo "  Copying FFmpeg binaries..."
    if [ -d "${BUNDLED_FFMPEG_DEST}" ]; then
        rm -rf "${BUNDLED_FFMPEG_DEST}"
    fi
    mkdir -p "${BUNDLED_FFMPEG_DEST}"
    cp -R "${BUNDLED_FFMPEG_SOURCE}/"* "${BUNDLED_FFMPEG_DEST}/" 2>/dev/null || true
    # Ensure binaries are executable
    chmod +x "${BUNDLED_FFMPEG_DEST}/ffmpeg" 2>/dev/null || true
    chmod +x "${BUNDLED_FFMPEG_DEST}/ffprobe" 2>/dev/null || true
    
    # Code sign FFmpeg binaries if code signing identity is available
    # This is required for notarization and distribution
    if [ -n "${CODE_SIGN_IDENTITY:-}" ] && [ "${CODE_SIGN_IDENTITY}" != "" ]; then
        echo "  Code signing FFmpeg binaries..."
        if [ -f "${BUNDLED_FFMPEG_DEST}/ffmpeg" ]; then
            codesign --force --sign "${CODE_SIGN_IDENTITY}" \
                --timestamp \
                --options runtime \
                "${BUNDLED_FFMPEG_DEST}/ffmpeg" 2>/dev/null || {
                echo "  Warning: Failed to code sign ffmpeg (may not be critical for development)"
            }
        fi
        if [ -f "${BUNDLED_FFMPEG_DEST}/ffprobe" ]; then
            codesign --force --sign "${CODE_SIGN_IDENTITY}" \
                --timestamp \
                --options runtime \
                "${BUNDLED_FFMPEG_DEST}/ffprobe" 2>/dev/null || {
                echo "  Warning: Failed to code sign ffprobe (may not be critical for development)"
            }
        fi
    else
        echo "  Note: CODE_SIGN_IDENTITY not set, skipping code signing (required for distribution)"
    fi
    
    echo "  FFmpeg binaries copied to ${BUNDLED_FFMPEG_DEST}"
else
    echo "  Warning: Bundled FFmpeg not found at ${BUNDLED_FFMPEG_SOURCE}"
fi

echo "Bundled dependencies copy complete"

# Note: streamtv_source is kept outside the synchronized group path permanently
# No need to restore it - it's in the correct location

