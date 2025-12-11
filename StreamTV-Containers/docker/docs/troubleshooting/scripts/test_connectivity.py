#!/usr/bin/env python3
"""
Network Diagnostics Troubleshooting Script
Tests DNS resolution, network connectivity, and media source accessibility
"""

import sys
import socket
import subprocess
import platform
import time
from pathlib import Path
from urllib.parse import urlparse
import json
import asyncio

def print_section(title):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_result(test_name, success, message, details=None):
    """Print a test result"""
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"{status} {test_name}")
    print(f"    {message}")
    if details:
        for detail in details:
            print(f"    {detail}")
    return success

def test_dns_resolution():
    """Test DNS resolution for critical domains"""
    print_section("DNS Resolution Tests")
    
    domains = [
        "youtube.com",
        "www.youtube.com",
        "googlevideo.com",
        "archive.org",
        "www.archive.org",
        "google.com",
        "8.8.8.8"  # Google DNS
    ]
    
    results = []
    for domain in domains:
        try:
            ip = socket.gethostbyname(domain)
            results.append(print_result(
                f"DNS: {domain}",
                True,
                f"Resolved to {ip}",
                []
            ))
        except socket.gaierror as e:
            results.append(print_result(
                f"DNS: {domain}",
                False,
                f"Failed to resolve: {e}",
                ["This is likely the cause of your YouTube errors"]
            ))
        except Exception as e:
            results.append(print_result(
                f"DNS: {domain}",
                False,
                f"Error: {e}",
                []
            ))
    
    return all(results)

def test_basic_connectivity():
    """Test basic network connectivity"""
    print_section("Basic Connectivity Tests")
    
    results = []
    
    # Test ping to Google DNS
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(
                ["ping", "-c", "3", "8.8.8.8"],
                capture_output=True,
                text=True,
                timeout=10
            )
        else:  # Linux
            result = subprocess.run(
                ["ping", "-c", "3", "8.8.8.8"],
                capture_output=True,
                text=True,
                timeout=10
            )
        
        if result.returncode == 0:
            results.append(print_result(
                "Ping to 8.8.8.8",
                True,
                "Network connectivity OK",
                []
            ))
        else:
            results.append(print_result(
                "Ping to 8.8.8.8",
                False,
                "Cannot reach internet",
                ["Check your network connection", "Check firewall settings"]
            ))
    except subprocess.TimeoutExpired:
        results.append(print_result(
            "Ping to 8.8.8.8",
            False,
            "Ping timed out",
            ["Network may be slow or unreachable"]
        ))
    except FileNotFoundError:
        results.append(print_result(
            "Ping to 8.8.8.8",
            False,
            "ping command not found",
            ["Cannot test connectivity"]
        ))
    except Exception as e:
        results.append(print_result(
            "Ping to 8.8.8.8",
            False,
            f"Error: {e}",
            []
        ))
    
    # Test HTTP connectivity
    try:
        import urllib.request
        response = urllib.request.urlopen("https://www.google.com", timeout=10)
        if response.status == 200:
            results.append(print_result(
                "HTTP to google.com",
                True,
                "HTTP connectivity OK",
                []
            ))
        else:
            results.append(print_result(
                "HTTP to google.com",
                False,
                f"Unexpected status: {response.status}",
                []
            ))
    except Exception as e:
        results.append(print_result(
            "HTTP to google.com",
            False,
            f"Cannot connect: {e}",
            ["Check firewall", "Check proxy settings"]
        ))
    
    return all(results)

def test_youtube_accessibility():
    """Test YouTube API accessibility"""
    print_section("YouTube Accessibility Tests")
    
    results = []
    
    # Test YouTube domains
    youtube_domains = [
        "youtube.com",
        "www.youtube.com",
        "googlevideo.com",
        "youtubei.googleapis.com"
    ]
    
    for domain in youtube_domains:
        try:
            ip = socket.gethostbyname(domain)
            # Try to connect to port 443 (HTTPS)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((ip, 443))
            sock.close()
            
            if result == 0:
                results.append(print_result(
                    f"YouTube: {domain}",
                    True,
                    f"Resolved to {ip}, port 443 accessible",
                    []
                ))
            else:
                results.append(print_result(
                    f"YouTube: {domain}",
                    False,
                    f"Resolved to {ip}, but port 443 not accessible",
                    ["Firewall may be blocking HTTPS"]
                ))
        except socket.gaierror as e:
            results.append(print_result(
                f"YouTube: {domain}",
                False,
                f"DNS resolution failed: {e}",
                ["This is the cause of your YouTube errors", "Try flushing DNS cache"]
            ))
        except Exception as e:
            results.append(print_result(
                f"YouTube: {domain}",
                False,
                f"Error: {e}",
                []
            ))
    
    # Test YouTube Data API v3 (if configured)
    try:
        # Try to import from the project
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from streamtv.config import config
        from streamtv.streaming.youtube_api_client import YouTubeAPIClient
        
        if config.youtube.api_key:
            import asyncio
            async def test_api():
                api_client = YouTubeAPIClient(api_key=config.youtube.api_key)
                validation = await api_client.validate_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
                await api_client.__aexit__(None, None, None)
                return validation
            
            validation = asyncio.run(test_api())
            if validation['valid'] and validation['available']:
                results.append(print_result(
                    "YouTube Data API v3",
                    True,
                    "API key configured and working",
                    [f"Video validated: {validation['info'].get('title', 'N/A')[:50]}"]
                ))
            elif validation['valid']:
                results.append(print_result(
                    "YouTube Data API v3",
                    False,
                    f"API key configured but video unavailable: {validation.get('error', 'Unknown')}",
                    []
                ))
            else:
                results.append(print_result(
                    "YouTube Data API v3",
                    False,
                    f"API validation failed: {validation.get('error', 'Unknown')}",
                    []
                ))
        else:
            results.append(print_result(
                "YouTube Data API v3",
                False,
                "API key not configured (optional but recommended)",
                ["Add api_key to config.yaml for better reliability"]
            ))
    except ImportError as e:
        # Project modules not available - this is OK if running standalone
        pass
    except Exception as e:
        # API test failed but that's OK - it's optional
        pass
    
    # Test yt-dlp can reach YouTube (check venv first, then system)
    ytdlp_working = False
    ytdlp_installed = False
    
    # First try venv Python
    venv_python = Path(__file__).parent.parent / "venv" / "bin" / "python3"
    if venv_python.exists():
        try:
            result = subprocess.run(
                [str(venv_python), "-c", "import yt_dlp; yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}).extract_info('https://www.youtube.com/watch?v=dQw4w9WgXcQ', download=False)"],
                capture_output=True,
                timeout=30,
                text=True
            )
            if result.returncode == 0:
                ytdlp_installed = True
                ytdlp_working = True
                results.append(print_result(
                    "yt-dlp YouTube API (venv)",
                    True,
                    "Successfully connected to YouTube via yt-dlp",
                    []
                ))
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
    
    # If venv test didn't work, try system Python
    if not ytdlp_working:
        try:
            import yt_dlp
            ytdlp_installed = True
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Try to extract info from a known video
                info = ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False)
                if info:
                    ytdlp_working = True
                    results.append(print_result(
                        "yt-dlp YouTube API (system)",
                        True,
                        "Successfully connected to YouTube API",
                        []
                    ))
                else:
                    results.append(print_result(
                        "yt-dlp YouTube API (system)",
                        False,
                        "Connected but no data returned",
                        []
                    ))
        except ImportError:
            if not ytdlp_installed:
                results.append(print_result(
                    "yt-dlp YouTube API",
                    False,
                    "yt-dlp not installed in system Python",
                    ["Install in venv: venv/bin/pip install yt-dlp", "Or install system-wide: pip install yt-dlp"]
                ))
        except Exception as e:
            error_msg = str(e)
            if "nodename" in error_msg.lower() or "servname" in error_msg.lower():
                results.append(print_result(
                    "yt-dlp YouTube API",
                    False,
                    f"DNS resolution error: {e}",
                    ["This matches your error!", "DNS cache may need flushing"]
                ))
            else:
                results.append(print_result(
                    "yt-dlp YouTube API",
                    False,
                    f"Error: {e}",
                    []
                ))
    
    return all(results)

def test_archive_org_accessibility():
    """Test Archive.org accessibility"""
    print_section("Archive.org Accessibility Tests")
    
    results = []
    
    try:
        ip = socket.gethostbyname("archive.org")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, 443))
        sock.close()
        
        if result == 0:
            results.append(print_result(
                "Archive.org",
                True,
                f"Resolved to {ip}, port 443 accessible",
                []
            ))
        else:
            results.append(print_result(
                "Archive.org",
                False,
                f"Resolved to {ip}, but port 443 not accessible",
                []
            ))
    except socket.gaierror as e:
        results.append(print_result(
            "Archive.org",
            False,
            f"DNS resolution failed: {e}",
            []
        ))
    except Exception as e:
        results.append(print_result(
            "Archive.org",
            False,
            f"Error: {e}",
            []
        ))
    
    return all(results)

def check_dns_configuration():
    """Check DNS configuration"""
    print_section("DNS Configuration")
    
    results = []
    
    # Get DNS servers (macOS)
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["scutil", "--dns"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                dns_output = result.stdout
                # Extract nameservers
                nameservers = []
                for line in dns_output.split('\n'):
                    if 'nameserver' in line.lower() and '[' in line:
                        # Extract IP from line like "nameserver[0] : 192.168.1.1"
                        parts = line.split(':')
                        if len(parts) > 1:
                            nameservers.append(parts[1].strip())
                
                if nameservers:
                    results.append(print_result(
                        "DNS Servers",
                        True,
                        f"Configured DNS servers: {', '.join(nameservers[:3])}",
                        nameservers[:5]  # Show first 5
                    ))
                else:
                    results.append(print_result(
                        "DNS Servers",
                        False,
                        "No DNS servers found",
                        ["DNS may not be configured correctly"]
                    ))
        except Exception as e:
            results.append(print_result(
                "DNS Servers",
                False,
                f"Error checking DNS: {e}",
                []
            ))
    
    # Check system time (DNS can fail if time is wrong)
    try:
        import datetime
        system_time = datetime.datetime.now()
        results.append(print_result(
            "System Time",
            True,
            f"Current time: {system_time.strftime('%Y-%m-%d %H:%M:%S')}",
            []
        ))
    except Exception as e:
        results.append(print_result(
            "System Time",
            False,
            f"Error: {e}",
            []
        ))
    
    return all(results)

def provide_recommendations(dns_ok, connectivity_ok, youtube_ok):
    """Provide recommendations based on test results"""
    print_section("Recommendations")
    
    recommendations = []
    
    if not dns_ok:
        recommendations.append("DNS Resolution Issues Detected:")
        recommendations.append("  1. Flush DNS cache:")
        if platform.system() == "Darwin":
            recommendations.append("     sudo dscacheutil -flushcache")
            recommendations.append("     sudo killall -HUP mDNSResponder")
        recommendations.append("  2. Check DNS servers in System Preferences")
        recommendations.append("  3. Try using Google DNS (8.8.8.8, 8.8.4.4)")
        recommendations.append("  4. Restart network services")
    
    if not connectivity_ok:
        recommendations.append("Network Connectivity Issues:")
        recommendations.append("  1. Check internet connection")
        recommendations.append("  2. Check firewall settings")
        recommendations.append("  3. Disable VPN temporarily")
        recommendations.append("  4. Check proxy settings")
    
    if not youtube_ok:
        recommendations.append("YouTube Access Issues:")
        recommendations.append("  1. The error '[Errno 8] nodename nor servname provided' is a DNS error")
        recommendations.append("  2. Flush DNS cache (see above)")
        recommendations.append("  3. Check if YouTube is accessible in browser")
        recommendations.append("  4. Update yt-dlp: pip install --upgrade yt-dlp")
        recommendations.append("  5. Check system time is correct")
    
    if dns_ok and connectivity_ok and youtube_ok:
        recommendations.append("All tests passed! Network connectivity appears normal.")
        recommendations.append("If you're still seeing errors, they may be:")
        recommendations.append("  - Temporary YouTube API issues")
        recommendations.append("  - Rate limiting (wait and retry)")
        recommendations.append("  - Video-specific issues (video may be unavailable)")
    else:
        recommendations.append("")
        recommendations.append("After applying fixes, restart StreamTV server.")
    
    for rec in recommendations:
        print(f"  {rec}")

def main():
    """Main diagnostic function"""
    print("="*60)
    print("  StreamTV Network Diagnostics")
    print("="*60)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    dns_ok = test_dns_resolution()
    connectivity_ok = test_basic_connectivity()
    youtube_ok = test_youtube_accessibility()
    archive_ok = test_archive_org_accessibility()
    dns_config_ok = check_dns_configuration()
    
    # Summary
    print_section("Summary")
    print(f"DNS Resolution:      {'✓ PASS' if dns_ok else '✗ FAIL'}")
    print(f"Basic Connectivity: {'✓ PASS' if connectivity_ok else '✗ FAIL'}")
    print(f"YouTube Access:      {'✓ PASS' if youtube_ok else '✗ FAIL'}")
    print(f"Archive.org Access:  {'✓ PASS' if archive_ok else '✗ FAIL'}")
    print(f"DNS Configuration:  {'✓ PASS' if dns_config_ok else '✗ FAIL'}")
    
    overall = dns_ok and connectivity_ok and youtube_ok
    print(f"\nOverall Status: {'✓ ALL TESTS PASSED' if overall else '✗ ISSUES DETECTED'}")
    
    # Provide recommendations
    provide_recommendations(dns_ok, connectivity_ok, youtube_ok)
    
    # Return exit code
    return 0 if overall else 1

if __name__ == "__main__":
    sys.exit(main())

