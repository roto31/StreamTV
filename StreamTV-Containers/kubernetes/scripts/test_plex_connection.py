#!/usr/bin/env python3
"""
Test Plex API connection and verify token works
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamtv.config import config
from streamtv.streaming.plex_api_client import PlexAPIClient


async def test_plex_connection():
    """Test connection to Plex server"""
    print("="*60)
    print("Testing Plex API Connection")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  Base URL: {config.plex.base_url}")
    print(f"  Token: {config.plex.token[:10] + '...' if config.plex.token else 'Not configured'}")
    print(f"  Enabled: {config.plex.enabled}")
    print(f"  Use for EPG: {config.plex.use_for_epg}")
    
    if not config.plex.enabled:
        print("\n❌ Plex integration is disabled in config.yaml")
        return False
    
    if not config.plex.base_url:
        print("\n❌ Plex base_url is not configured")
        return False
    
    if not config.plex.token:
        print("\n❌ Plex token is not configured")
        return False
    
    print("\n" + "="*60)
    print("Connecting to Plex server...")
    print("="*60)
    
    try:
        async with PlexAPIClient(
            base_url=config.plex.base_url,
            token=config.plex.token
        ) as client:
            # Test server connection
            print("\n1. Testing server connection...")
            server_info = await client.get_server_info()
            
            if server_info:
                print("   ✅ Successfully connected to Plex server!")
                print(f"   Server Name: {server_info.get('friendlyName', 'Unknown')}")
                print(f"   Version: {server_info.get('version', 'Unknown')}")
                print(f"   Machine ID: {server_info.get('machineIdentifier', 'Unknown')[:20]}...")
            else:
                print("   ❌ Could not get server information")
                print("   Check your base_url and token")
                return False
            
            # Test DVR endpoints (if available)
            print("\n2. Testing DVR endpoints...")
            dvrs = await client.get_dvrs()
            if dvrs:
                print(f"   ✅ Found {len(dvrs)} DVR(s):")
                for dvr in dvrs:
                    print(f"      - {dvr.get('title', 'Unknown')} (ID: {dvr.get('id', 'Unknown')})")
            else:
                print("   ℹ️  No DVRs found (this is normal if DVR is not set up)")
            
            # Test countries endpoint
            print("\n3. Testing EPG endpoints...")
            countries = await client.get_countries()
            if countries:
                print(f"   ✅ EPG service accessible (found {len(countries)} countries)")
            else:
                print("   ⚠️  Could not access EPG countries (may require DVR setup)")
            
            print("\n" + "="*60)
            print("✅ Plex API Connection Test: SUCCESS")
            print("="*60)
            print("\nYour Plex integration is working correctly!")
            print("EPG enhancements will now use Plex API for:")
            print("  - Channel mapping")
            print("  - Metadata enrichment")
            print("  - DVR compatibility")
            print("\n" + "="*60)
            return True
            
    except Exception as e:
        print(f"\n❌ Error connecting to Plex server: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify Plex server is running")
        print("  2. Check base_url is correct")
        print("  3. Verify token is valid")
        print("  4. Check network connectivity")
        print("\n" + "="*60)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_plex_connection())
    sys.exit(0 if success else 1)

