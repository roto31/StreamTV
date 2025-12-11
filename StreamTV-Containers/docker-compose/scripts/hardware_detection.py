#!/usr/bin/env python3
"""
Hardware Detection Utilities for Ollama Model Recommendations
Detects system resources to recommend appropriate Ollama models
"""

import platform
import subprocess
import sys
import os
from typing import Dict, List, Optional
import json

def get_system_info() -> Dict:
    """Get system information"""
    system = platform.system()
    info = {
        "system": system,
        "machine": platform.machine(),
        "processor": platform.processor(),
    }
    
    if system == "Darwin":  # macOS
        try:
            # Get RAM
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                ram_bytes = int(result.stdout.strip())
                info["ram_gb"] = ram_bytes / (1024 ** 3)
            
            # Get CPU cores
            result = subprocess.run(
                ["sysctl", "-n", "hw.ncpu"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                info["cpu_cores"] = int(result.stdout.strip())
            
            # Get disk space
            result = subprocess.run(
                ["df", "-g", "."],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        info["disk_free_gb"] = int(parts[3])
        except Exception as e:
            print(f"Warning: Could not get all system info: {e}", file=sys.stderr)
    
    elif system == "Linux":
        try:
            # Get RAM
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        ram_kb = int(line.split()[1])
                        info["ram_gb"] = ram_kb / (1024 ** 2)
                        break
            
            # Get CPU cores
            result = subprocess.run(
                ["nproc"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                info["cpu_cores"] = int(result.stdout.strip())
            
            # Get disk space
            result = subprocess.run(
                ["df", "-BG", "."],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        info["disk_free_gb"] = int(parts[3].rstrip('G'))
        except Exception as e:
            print(f"Warning: Could not get all system info: {e}", file=sys.stderr)
    
    elif system == "Windows":
        try:
            import psutil
            info["ram_gb"] = psutil.virtual_memory().total / (1024 ** 3)
            info["cpu_cores"] = psutil.cpu_count()
            info["disk_free_gb"] = psutil.disk_usage('.').free / (1024 ** 3)
        except ImportError:
            # Fallback without psutil
            try:
                # Get RAM using wmic
                result = subprocess.run(
                    ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        ram_bytes = int(lines[1].strip())
                        info["ram_gb"] = ram_bytes / (1024 ** 3)
                
                # Get CPU cores
                result = subprocess.run(
                    ["wmic", "cpu", "get", "NumberOfCores"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        info["cpu_cores"] = int(lines[1].strip())
            except Exception as e:
                print(f"Warning: Could not get all system info: {e}", file=sys.stderr)
    
    return info

def check_ollama_installed() -> bool:
    """Check if Ollama is installed"""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def get_installed_ollama_models() -> List[str]:
    """Get list of installed Ollama models"""
    if not check_ollama_installed():
        return []
    
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            models = []
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if parts:
                        model_name = parts[0]
                        models.append(model_name)
            return models
    except Exception:
        pass
    
    return []

# Ollama model definitions
OLLAMA_MODELS = {
    "llama3.2:3b": {
        "name": "Llama 3.2 (3B)",
        "size_gb": 2.0,
        "ram_required_gb": 4,
        "description": "Lightweight, fast, good for simple troubleshooting",
        "recommended_for": "Systems with limited RAM (4GB+)"
    },
    "mistral:7b": {
        "name": "Mistral (7B)",
        "size_gb": 4.1,
        "ram_required_gb": 8,
        "description": "Balanced performance and quality, recommended default",
        "recommended_for": "Most systems (8GB+ RAM)"
    },
    "llama3.1:8b": {
        "name": "Llama 3.1 (8B)",
        "size_gb": 4.7,
        "ram_required_gb": 8,
        "description": "Good reasoning capabilities, better than Mistral",
        "recommended_for": "Systems with 8GB+ RAM"
    },
    "codellama:7b": {
        "name": "CodeLlama (7B)",
        "size_gb": 3.8,
        "ram_required_gb": 8,
        "description": "Excellent for code debugging and technical issues",
        "recommended_for": "Developers, code-focused troubleshooting"
    },
    "llama3.1:13b": {
        "name": "Llama 3.1 (13B)",
        "size_gb": 7.3,
        "ram_required_gb": 16,
        "description": "High quality reasoning, best for complex issues",
        "recommended_for": "Systems with 16GB+ RAM"
    },
    "codellama:13b": {
        "name": "CodeLlama (13B)",
        "size_gb": 7.3,
        "ram_required_gb": 16,
        "description": "Best code analysis, excellent for debugging",
        "recommended_for": "Developers with 16GB+ RAM"
    }
}

def get_recommended_models(system_info: Optional[Dict] = None) -> List[Dict]:
    """Get recommended Ollama models based on system hardware"""
    if system_info is None:
        system_info = get_system_info()
    
    ram_gb = system_info.get("ram_gb", 8)  # Default to 8GB
    disk_free_gb = system_info.get("disk_free_gb", 20)  # Default to 20GB
    
    recommended = []
    
    for model_id, model_info in OLLAMA_MODELS.items():
        # Check if system meets requirements
        if ram_gb >= model_info["ram_required_gb"] and disk_free_gb >= (model_info["size_gb"] + 5):
            recommended.append({
                "id": model_id,
                **model_info,
                "can_install": True
            })
        else:
            recommended.append({
                "id": model_id,
                **model_info,
                "can_install": False,
                "reason": f"Requires {model_info['ram_required_gb']}GB RAM and {model_info['size_gb'] + 5:.1f}GB free disk space"
            })
    
    # Sort by recommended order (smallest to largest)
    recommended.sort(key=lambda x: x["size_gb"])
    
    return recommended

def get_default_recommended_model(system_info: Optional[Dict] = None) -> str:
    """Get the default recommended model for the system"""
    if system_info is None:
        system_info = get_system_info()
    
    ram_gb = system_info.get("ram_gb", 8)
    
    # Recommend based on RAM
    if ram_gb >= 16:
        return "llama3.1:13b"
    elif ram_gb >= 8:
        return "mistral:7b"  # Default recommendation
    else:
        return "llama3.2:3b"

def install_ollama_macos() -> bool:
    """Install Ollama on macOS using Homebrew or direct download"""
    try:
        # Try Homebrew first
        result = subprocess.run(
            ["brew", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Install via Homebrew
            result = subprocess.run(
                ["brew", "install", "ollama"],
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode == 0
        
        # Fallback: Direct download
        print("Homebrew not found, downloading Ollama directly...")
        result = subprocess.run(
            ["curl", "-fsSL", "https://ollama.com/install.sh"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            install_script = result.stdout
            # Execute install script
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(install_script)
                f.flush()
                os.chmod(f.name, 0o755)
                result = subprocess.run(
                    ["bash", f.name],
                    timeout=300
                )
                return result.returncode == 0
    except Exception as e:
        print(f"Error installing Ollama: {e}", file=sys.stderr)
        return False
    
    return False

def install_ollama_linux() -> bool:
    """Install Ollama on Linux"""
    try:
        # Use official install script
        result = subprocess.run(
            ["curl", "-fsSL", "https://ollama.com/install.sh"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            install_script = result.stdout
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(install_script)
                f.flush()
                os.chmod(f.name, 0o755)
                result = subprocess.run(
                    ["bash", f.name],
                    timeout=300
                )
                return result.returncode == 0
    except Exception as e:
        print(f"Error installing Ollama: {e}", file=sys.stderr)
        return False
    
    return False

def install_ollama_windows() -> bool:
    """Install Ollama on Windows"""
    try:
        # Download and run Ollama installer
        import urllib.request
        import tempfile
        
        installer_url = "https://ollama.com/download/OllamaSetup.exe"
        installer_path = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
        
        print(f"Downloading Ollama installer to {installer_path}...")
        urllib.request.urlretrieve(installer_url, installer_path)
        
        # Run installer
        result = subprocess.run(
            [installer_path, "/S"],  # Silent install
            timeout=300
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error installing Ollama: {e}", file=sys.stderr)
        return False

def install_ollama() -> bool:
    """Install Ollama based on platform"""
    system = platform.system()
    
    if system == "Darwin":
        return install_ollama_macos()
    elif system == "Linux":
        return install_ollama_linux()
    elif system == "Windows":
        return install_ollama_windows()
    else:
        print(f"Unsupported platform: {system}", file=sys.stderr)
        return False

def install_ollama_model(model_id: str) -> bool:
    """Install a specific Ollama model"""
    if not check_ollama_installed():
        return False
    
    try:
        result = subprocess.run(
            ["ollama", "pull", model_id],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error installing model {model_id}: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # CLI interface for testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Hardware detection for Ollama")
    parser.add_argument("--check", action="store_true", help="Check if Ollama is installed")
    parser.add_argument("--models", action="store_true", help="List installed models")
    parser.add_argument("--recommend", action="store_true", help="Get recommended models")
    parser.add_argument("--info", action="store_true", help="Show system info")
    
    args = parser.parse_args()
    
    if args.check:
        installed = check_ollama_installed()
        print(f"Ollama installed: {installed}")
        sys.exit(0 if installed else 1)
    
    if args.models:
        models = get_installed_ollama_models()
        if models:
            print("Installed models:")
            for model in models:
                print(f"  - {model}")
        else:
            print("No models installed")
        sys.exit(0)
    
    if args.recommend:
        system_info = get_system_info()
        recommended = get_recommended_models(system_info)
        default = get_default_recommended_model(system_info)
        
        print(f"System: {system_info.get('system', 'Unknown')}")
        print(f"RAM: {system_info.get('ram_gb', 0):.1f} GB")
        print(f"Free Disk: {system_info.get('disk_free_gb', 0):.1f} GB")
        print(f"\nDefault Recommendation: {default}")
        print("\nAvailable Models:")
        for model in recommended:
            status = "✓" if model["can_install"] else "✗"
            print(f"{status} {model['name']}: {model['size_gb']:.1f}GB ({model['description']})")
            if not model["can_install"]:
                print(f"    Reason: {model.get('reason', 'Unknown')}")
        sys.exit(0)
    
    if args.info:
        info = get_system_info()
        print(json.dumps(info, indent=2))
        sys.exit(0)
    
    parser.print_help()

