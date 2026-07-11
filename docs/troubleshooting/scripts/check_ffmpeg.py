#!/usr/bin/env python3
"""
Check FFmpeg Installation
Verifies FFmpeg installation and version
"""

import subprocess
import shutil
import sys

def main():
    print("FFmpeg Installation Check")
    print("=" * 50)
    print()
    
    # Find FFmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    
    if not ffmpeg_path:
        print("❌ ERROR: FFmpeg not found in PATH")
        print()
        print("Installation options:")
        print("  macOS: brew install ffmpeg")
        print("  macOS (Apple Silicon): Download from https://evermeet.cx/ffmpeg/")
        print("  Linux: sudo apt-get install ffmpeg (Ubuntu/Debian)")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        return 1
    
    print(f"✓ FFmpeg found at: {ffmpeg_path}")
    print()
    
    # Check version
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"Version: {version_line}")
            print()
            
            # Check for required codecs
            codec_check = subprocess.run(
                ["ffmpeg", "-codecs"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if codec_check.returncode == 0:
                has_h264 = "h264" in codec_check.stdout.lower()
                has_aac = "aac" in codec_check.stdout.lower() or "libfdk_aac" in codec_check.stdout.lower()
                has_mp2 = "mp2" in codec_check.stdout.lower()
                
                print("Codec Support:")
                print(f"  H.264: {'✓' if has_h264 else '✗'}")
                print(f"  AAC: {'✓' if has_aac else '✗'}")
                print(f"  MP2: {'✓' if has_mp2 else '✗'}")
                print()
                
                if not (has_h264 and (has_aac or has_mp2)):
                    print("⚠ WARNING: Some required codecs may be missing")
                    print("   StreamTV requires H.264 and AAC/MP2 support")
            else:
                print("⚠ WARNING: Could not check codec support")
        else:
            print("⚠ WARNING: Could not get FFmpeg version")
            print(f"   Error: {result.stderr}")
            return 1
            
    except subprocess.TimeoutExpired:
        print("❌ ERROR: FFmpeg command timed out")
        return 1
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1
    
    print("FFmpeg check complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
