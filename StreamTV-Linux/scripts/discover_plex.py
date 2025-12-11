#!/usr/bin/env python3
"""
Discover Plex Media Server and help configure StreamTV integration
"""

import asyncio
import httpx
import socket
from typing import Optional, Dict, Any
from xml.etree import ElementTree as ET
import sys


async def discover_plex_servers() -> list[Dict[str, Any]]:
    """Discover Plex servers on the local network"""
    servers = []
    
    # Common Plex server locations
    locations = [
        "http://localhost:32400",
        "http://127.0.0.1:32400",
        "http://192.168.1.100:32400",
        "http://192.168.0.100:32400",
    ]
    
    # Get local IP addresses
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip.startswith("192.168.") or local_ip.startswith("10."):
            # Add local IP variants
            base_ip = ".".join(local_ip.split(".")[:-1])
            locations.append(f"http://{base_ip}.100:32400")
            locations.append(f"http://{local_ip}:32400")
    except:
        pass
    
    async with httpx.AsyncClient(timeout=2.0) as client:
        for url in locations:
            try:
                response = await client.get(f"{url}/", headers={
                    'Accept': 'application/json',
                    'X-Plex-Product': 'StreamTV',
                    'X-Plex-Version': '1.0.0',
                })
                if response.status_code == 200:
                    # Parse XML response
                    root = ET.fromstring(response.text)
                    server_info = {
                        'url': url,
                        'friendlyName': root.get('friendlyName', 'Unknown'),
                        'machineIdentifier': root.get('machineIdentifier', ''),
                        'version': root.get('version', ''),
                    }
                    servers.append(server_info)
                    print(f"✓ Found Plex server: {server_info['friendlyName']} at {url}")
            except Exception as e:
                pass
    
    return servers


async def get_plex_info(base_url: str) -> Optional[Dict[str, Any]]:
    """Get information about a Plex server"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/", headers={
                'Accept': 'application/json',
                'X-Plex-Product': 'StreamTV',
                'X-Plex-Version': '1.0.0',
            })
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                return {
                    'friendlyName': root.get('friendlyName', 'Unknown'),
                    'machineIdentifier': root.get('machineIdentifier', ''),
                    'version': root.get('version', ''),
                }
    except Exception as e:
        print(f"Error connecting to {base_url}: {e}")
    return None


def print_token_instructions():
    """Print instructions for getting Plex token"""
    print("\n" + "="*60)
    print("How to Get Your Plex Authentication Token")
    print("="*60)
    print("\nMethod 1: From Plex Web App")
    print("  1. Open Plex Web App in your browser")
    print("  2. Open browser Developer Tools (F12 or Cmd+Option+I)")
    print("  3. Go to Network tab")
    print("  4. Refresh the page")
    print("  5. Look for requests to plex.tv or your Plex server")
    print("  6. Check request headers for 'X-Plex-Token' parameter")
    print("\nMethod 2: From Plex Server Settings")
    print("  1. Go to Plex Web App")
    print("  2. Settings → Network")
    print("  3. Check the URL for token parameter")
    print("\nMethod 3: Using Plex Token Script")
    print("  Visit: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/")
    print("\nMethod 4: From Browser")
    print("  1. Log into Plex Web App")
    print("  2. View page source")
    print("  3. Search for 'token' in the source")
    print("  4. Look for a long alphanumeric string")
    print("="*60)


async def main():
    print("="*60)
    print("Plex Server Discovery for StreamTV")
    print("="*60)
    print("\nScanning for Plex Media Servers...\n")
    
    servers = await discover_plex_servers()
    
    if not servers:
        print("❌ No Plex servers found automatically.")
        print("\nPlease manually configure your Plex server:")
        print("  1. Find your Plex server IP address")
        print("     - Usually: http://YOUR_SERVER_IP:32400")
        print("     - Or: http://localhost:32400 if running locally")
        print("  2. Get your Plex authentication token (see below)")
        print_token_instructions()
        return
    
    print(f"\n✓ Found {len(servers)} Plex server(s):\n")
    for i, server in enumerate(servers, 1):
        print(f"{i}. {server['friendlyName']}")
        print(f"   URL: {server['url']}")
        print(f"   Version: {server['version']}")
        print(f"   ID: {server['machineIdentifier']}")
    
    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60)
    print("\n1. Choose one of the servers above")
    print("2. Get your Plex authentication token")
    print_token_instructions()
    print("\n3. Update config.yaml with:")
    print("   plex:")
    print(f"     enabled: true")
    print(f"     base_url: \"{servers[0]['url']}\"")
    print("     token: \"YOUR_PLEX_TOKEN_HERE\"")
    print("     use_for_epg: true")
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(main())

