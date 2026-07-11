#!/usr/bin/env python3
"""
Check Ports
Checks if required ports are available
"""

import socket
import sys
from pathlib import Path

# Add parent directory to path to import streamtv modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

def check_port(port, name):
    """Check if a port is in use"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def main():
    print("Port Availability Check")
    print("=" * 50)
    print()
    
    try:
        from streamtv.config import config
        server_port = config.server.port
    except:
        server_port = 8410
        print("⚠ Could not load config, using default port 8410")
        print()
    
    ports_to_check = [
        (server_port, "StreamTV Server"),
        (5004, "HDHomeRun (if enabled)"),
    ]
    
    all_available = True
    
    for port, name in ports_to_check:
        in_use = check_port(port, name)
        if in_use:
            print(f"⚠ Port {port} ({name}) is IN USE")
            print(f"   This may prevent StreamTV from starting")
            all_available = False
        else:
            print(f"✓ Port {port} ({name}) is available")
    
    print()
    
    if not all_available:
        print("Solutions:")
        print("  1. Stop the process using the port")
        print("  2. Change the port in config.yaml:")
        print(f"     server:")
        print(f"       port: {server_port + 1}  # Use different port")
        print()
        return 1
    
    print("All required ports are available!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
