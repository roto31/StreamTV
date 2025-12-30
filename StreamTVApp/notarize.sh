#!/bin/bash
#
# Notarize StreamTV.app for distribution
#

set -euo pipefail

if [ $# -lt 4 ]; then
    echo "Usage: $0 <app_path> <apple_id> <app_specific_password> <team_id>"
    echo ""
    echo "Example:"
    echo "  $0 build/export/StreamTV.app user@example.com abcd-efgh-ijkl-mnop ABC123DEFG"
    exit 1
fi

APP_PATH="$1"
APPLE_ID="$2"
APP_SPECIFIC_PASSWORD="$3"
TEAM_ID="$4"

if [ ! -d "$APP_PATH" ]; then
    echo "Error: App not found at $APP_PATH"
    exit 1
fi

echo "Submitting $APP_PATH for notarization..."

# Submit for notarization
xcrun notarytool submit "$APP_PATH" \
    --apple-id "$APPLE_ID" \
    --password "$APP_SPECIFIC_PASSWORD" \
    --team-id "$TEAM_ID" \
    --wait

echo "Notarization complete. Stapling ticket..."

# Staple notarization ticket
xcrun stapler staple "$APP_PATH"

# Verify
echo "Verifying notarization..."
xcrun stapler validate "$APP_PATH"
spctl --assess --verbose "$APP_PATH"

echo "Notarization complete and verified!"

