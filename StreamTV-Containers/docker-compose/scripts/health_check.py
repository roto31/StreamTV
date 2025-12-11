#!/usr/bin/env python3
"""
Comprehensive StreamTV Health Check Script
Analyzes logs, checks all components, and reports platform health
"""

import sys
import json
import httpx
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_section(text):
    """Print formatted section"""
    print(f"\n--- {text} ---")

def print_status(status, message):
    """Print status with color coding"""
    status_symbols = {
        "healthy": "✓",
        "warning": "⚠",
        "error": "✗",
        "info": "ℹ"
    }
    symbol = status_symbols.get(status, "•")
    print(f"  {symbol} {message}")

def main():
    """Run comprehensive health check"""
    base_url = "http://localhost:8410"
    
    print_header("StreamTV Comprehensive Health Check")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Server URL: {base_url}")
    
    try:
        # Run detailed health check via API
        print_section("Fetching Health Check from API")
        response = httpx.get(f"{base_url}/api/health/detailed", timeout=10.0)
        
        if response.status_code != 200:
            print_status("error", f"Health check API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return 1
        
        health_data = response.json()
        
        # Overall Status
        overall_status = health_data.get("overall_status", "unknown")
        summary = health_data.get("summary", {})
        
        print_section("Overall Status")
        print_status(overall_status, f"Platform Status: {overall_status.upper()}")
        print(f"  Healthy: {summary.get('healthy', 0)}")
        print(f"  Warnings: {summary.get('warnings', 0)}")
        print(f"  Errors: {summary.get('errors', 0)}")
        print(f"  Total Checks: {summary.get('total_checks', 0)}")
        
        # Detailed Checks
        print_section("Detailed Component Checks")
        checks = health_data.get("checks", {})
        
        for check_name, check_data in checks.items():
            status = check_data.get("status", "unknown")
            message = check_data.get("message", "No message")
            print_status(status, f"{check_name.upper()}: {message}")
            
            # Print additional details for specific checks
            if check_name == "database" and "channels" in check_data:
                print(f"    - Channels: {check_data.get('channels', 0)}")
                print(f"    - Enabled Channels: {check_data.get('enabled_channels', 0)}")
                print(f"    - Media Items: {check_data.get('media_items', 0)}")
                print(f"    - Database Size: {check_data.get('database_size_mb', 0)} MB")
            
            elif check_name == "ffmpeg" and "version" in check_data:
                print(f"    - Version: {check_data.get('version', 'Unknown')}")
                print(f"    - Path: {check_data.get('path', 'Unknown')}")
            
            elif check_name == "channels" and "channels" in check_data:
                channel_list = check_data.get("channels", [])
                for channel in channel_list[:5]:  # Show first 5
                    ch_status = channel.get("status", "unknown")
                    ch_name = channel.get("name", "Unknown")
                    has_sched = "✓" if channel.get("has_schedule") else "✗"
                    print(f"    - Channel {channel.get('number')}: {ch_name} (Schedule: {has_sched})")
                if len(channel_list) > 5:
                    print(f"    - ... and {len(channel_list) - 5} more channels")
            
            elif check_name == "logs" and "error_counts" in check_data:
                error_counts = check_data.get("error_counts", {})
                if error_counts:
                    print(f"    - Error Types Found:")
                    for error_type, count in error_counts.items():
                        print(f"      • {error_type}: {count} occurrences")
                recent_errors = check_data.get("recent_errors", [])
                if recent_errors:
                    print(f"    - Recent Errors (last 5):")
                    for error in recent_errors[-3:]:  # Last 3
                        error_msg = error.get("message", "")[:100]
                        print(f"      • {error.get('type', 'unknown')}: {error_msg}")
            
            elif check_name == "processes":
                print(f"    - FFmpeg Processes: {check_data.get('ffmpeg_processes', 0)}")
                print(f"    - StreamTV Processes: {check_data.get('streamtv_processes', 0)}")
            
            elif check_name == "configuration" and "issues" in check_data:
                issues = check_data.get("issues", [])
                if issues:
                    print(f"    - Configuration Issues:")
                    for issue in issues:
                        print(f"      • {issue}")
        
        # Recommendations
        print_section("Recommendations")
        
        if overall_status == "error":
            print_status("error", "CRITICAL: Platform has errors that need immediate attention")
            print("  - Review error details above")
            print("  - Check logs for more information")
            print("  - Restart StreamTV if needed")
        elif overall_status == "warning":
            print_status("warning", "Platform is operational but has warnings")
            print("  - Review warnings above")
            print("  - Some issues may be temporary (e.g., network connectivity)")
        else:
            print_status("healthy", "Platform is healthy and operating normally")
            print("  - All components are functioning correctly")
            print("  - Continue monitoring logs for any issues")
        
        # Network-specific recommendations
        network_check = checks.get("network", {})
        if network_check:
            youtube_check = network_check.get("youtube", {})
            if youtube_check.get("status") != "healthy":
                print_status("warning", "YouTube connectivity issue detected")
                print("  - This may be temporary")
                print("  - Check internet connection")
                print("  - YouTube rate limiting may be in effect")
        
        # Log-specific recommendations
        logs_check = checks.get("logs", {})
        if logs_check:
            error_counts = logs_check.get("error_counts", {})
            if "youtube_rate_limit" in error_counts:
                print_status("warning", "YouTube rate limiting detected in logs")
                print("  - This is expected behavior when making many requests")
                print("  - StreamTV will automatically retry with delays")
                print("  - Consider reducing channel count or request frequency")
            
            if "network_error" in error_counts:
                print_status("warning", "Network connectivity errors detected")
                print("  - Check internet connection")
                print("  - Verify DNS resolution is working")
                print("  - Some errors may be temporary")
        
        print_header("Health Check Complete")
        
        # Return exit code based on status
        if overall_status == "error":
            return 1
        elif overall_status == "warning":
            return 0  # Warnings are acceptable
        else:
            return 0
            
    except httpx.ConnectError:
        print_status("error", "Cannot connect to StreamTV server")
        print("  - Is StreamTV running?")
        print(f"  - Check if server is accessible at {base_url}")
        return 1
    except Exception as e:
        print_status("error", f"Error running health check: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

