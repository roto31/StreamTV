#!/usr/bin/env python3
"""
Helper script to get Plex authentication token
Opens browser with instructions and helps extract token from Plex Web App
"""

import webbrowser
import sys
import os

def print_instructions():
    """Print detailed instructions for getting Plex token"""
    print("="*70)
    print("Get Your Plex Authentication Token")
    print("="*70)
    print("\n📋 Follow these steps:\n")
    print("1. Open Plex Web App:")
    print("   → http://localhost:32400/web")
    print("   OR")
    print("   → https://app.plex.tv/desktop\n")
    print("2. Open Browser Developer Tools:")
    print("   - macOS: Cmd + Option + I")
    print("   - Windows/Linux: F12 or Ctrl + Shift + I\n")
    print("3. Go to Network Tab in Developer Tools\n")
    print("4. Refresh the page (Cmd+R or F5)\n")
    print("5. Look for requests to:")
    print("   - plex.tv")
    print("   - localhost:32400")
    print("   - Your Plex server IP\n")
    print("6. Click on any request and check:")
    print("   - Headers tab → Request Headers")
    print("   - Look for 'X-Plex-Token' parameter\n")
    print("7. Copy the token value (long alphanumeric string)\n")
    print("="*70)
    print("\nAlternative Method (Browser Console):\n")
    print("1. Open Developer Tools → Console tab")
    print("2. Type and press Enter:")
    print("   window.localStorage.getItem('token')\n")
    print("3. Copy the returned value\n")
    print("="*70)
    print("\nAfter getting your token:")
    print("  1. Update config.yaml:")
    print("     plex:")
    print("       token: \"YOUR_TOKEN_HERE\"")
    print("  2. Restart StreamTV server\n")
    print("="*70)


def main():
    print_instructions()
    
    # Try to open Plex Web App
    print("\n🌐 Opening Plex Web App in your browser...\n")
    try:
        # Try localhost first
        webbrowser.open("http://localhost:32400/web")
        print("✓ Opened http://localhost:32400/web")
    except:
        try:
            # Try web app
            webbrowser.open("https://app.plex.tv/desktop")
            print("✓ Opened https://app.plex.tv/desktop")
        except:
            print("⚠️  Could not automatically open browser")
            print("   Please manually open: http://localhost:32400/web")
    
    print("\n" + "="*70)
    print("Once you have your token, update config.yaml and restart StreamTV.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

