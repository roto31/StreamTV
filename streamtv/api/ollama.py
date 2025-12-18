"""
Ollama AI Troubleshooting API endpoints
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from pathlib import Path
import subprocess
import logging
import json
import os
import platform
import sys
from typing import Optional, Dict, List
import tempfile
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ollama"])

# Get base directory (project root)
BASE_DIR = Path(__file__).parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"

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
    except Exception as e:
        logger.error(f"Error getting Ollama models: {e}")
    
    return []

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
            logger.warning(f"Could not get all system info: {e}")
    
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
            logger.warning(f"Could not get all system info: {e}")
    
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
                logger.warning(f"Could not get all system info: {e}")
    
    return info

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

@router.get("/ollama/status")
async def get_ollama_status():
    """Get Ollama installation status and system info"""
    installed = check_ollama_installed()
    system_info = get_system_info()
    recommended_models = get_recommended_models(system_info)
    installed_models = get_installed_ollama_models() if installed else []
    
    return {
        "installed": installed,
        "system_info": system_info,
        "recommended_models": recommended_models,
        "installed_models": installed_models
    }

@router.post("/ollama/install")
async def install_ollama():
    """Install Ollama application"""
    if check_ollama_installed():
        return {
            "success": True,
            "message": "Ollama is already installed",
            "installed": True
        }
    
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
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
                    timeout=600
                )
                if result.returncode == 0:
                    return {
                        "success": True,
                        "message": "Ollama installed via Homebrew",
                        "installed": True
                    }
            
            # Fallback: Direct download
            result = subprocess.run(
                ["curl", "-fsSL", "https://ollama.com/install.sh"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                install_script = result.stdout
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                    f.write(install_script)
                    f.flush()
                    os.chmod(f.name, 0o755)
                    result = subprocess.run(
                        ["bash", f.name],
                        capture_output=True,
                        text=True,
                        timeout=600
                    )
                    os.unlink(f.name)
                    if result.returncode == 0:
                        return {
                            "success": True,
                            "message": "Ollama installed successfully",
                            "installed": True
                        }
        
        elif system == "Linux":
            # Use official install script
            result = subprocess.run(
                ["curl", "-fsSL", "https://ollama.com/install.sh"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                install_script = result.stdout
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                    f.write(install_script)
                    f.flush()
                    os.chmod(f.name, 0o755)
                    result = subprocess.run(
                        ["bash", f.name],
                        capture_output=True,
                        text=True,
                        timeout=600
                    )
                    os.unlink(f.name)
                    if result.returncode == 0:
                        return {
                            "success": True,
                            "message": "Ollama installed successfully",
                            "installed": True
                        }
        
        elif system == "Windows":
            # Download and run Ollama installer
            import urllib.request
            installer_url = "https://ollama.com/download/OllamaSetup.exe"
            installer_path = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
            
            urllib.request.urlretrieve(installer_url, installer_path)
            
            # Run installer
            result = subprocess.run(
                [installer_path, "/S"],  # Silent install
                timeout=600
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Ollama installer downloaded and executed",
                    "installed": True,
                    "note": "Please restart your terminal or computer to use Ollama"
                }
        
        return {
            "success": False,
            "message": f"Unsupported platform: {system}",
            "installed": False
        }
    
    except Exception as e:
        logger.error(f"Error installing Ollama: {e}")
        return {
            "success": False,
            "message": f"Installation failed: {str(e)}",
            "installed": False
        }

@router.post("/ollama/models/{model_id}/install")
async def install_ollama_model(model_id: str):
    """Install a specific Ollama model"""
    if not check_ollama_installed():
        raise HTTPException(status_code=400, detail="Ollama is not installed. Please install Ollama first.")
    
    if model_id not in OLLAMA_MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    try:
        result = subprocess.run(
            ["ollama", "pull", model_id],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Model {model_id} installed successfully",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        else:
            return {
                "success": False,
                "message": f"Model installation failed",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Model installation timed out")
    except Exception as e:
        logger.error(f"Error installing model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error installing model: {str(e)}")

@router.delete("/ollama/models/{model_id}")
async def delete_ollama_model(model_id: str):
    """Delete an installed Ollama model"""
    if not check_ollama_installed():
        raise HTTPException(status_code=400, detail="Ollama is not installed")
    
    try:
        result = subprocess.run(
            ["ollama", "rm", model_id],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Model {model_id} deleted successfully"
            }
        else:
            return {
                "success": False,
                "message": f"Failed to delete model",
                "stderr": result.stderr
            }
    except Exception as e:
        logger.error(f"Error deleting model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting model: {str(e)}")

@router.get("/ollama", response_class=HTMLResponse)
async def ollama_page(request: Request):
    """Serve the Ollama management page"""
    from streamtv.main import templates
    
    return templates.TemplateResponse(
        "ollama.html",
        {
            "request": request,
            "title": "AI Troubleshooting Assistant (Ollama)"
        }
    )


def get_streamtv_logs_context(max_lines: int = 200) -> str:
    """Get recent StreamTV logs as context for AI troubleshooting"""
    from ..config import config
    from ..api.logs import get_log_file_path
    
    try:
        log_file = get_log_file_path()
        if not log_file or not log_file.exists():
            return "No StreamTV log file found."
        
        # Read last N lines
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            recent_lines = lines[-max_lines:] if len(lines) > max_lines else lines
        
        # Filter for errors and warnings
        error_lines = []
        warning_lines = []
        for line in recent_lines:
            line_lower = line.lower()
            if 'error' in line_lower or 'exception' in line_lower or 'traceback' in line_lower:
                error_lines.append(line.strip())
            elif 'warning' in line_lower:
                warning_lines.append(line.strip())
        
        # Combine, prioritizing errors
        context_lines = error_lines[-50:] + warning_lines[-30:]  # Last 50 errors, 30 warnings
        
        if not context_lines:
            return f"StreamTV logs: No recent errors or warnings found in last {max_lines} lines."
        
        return f"StreamTV Logs (recent errors/warnings):\n" + "\n".join(context_lines[-80:])  # Limit to 80 lines total
    except Exception as e:
        logger.warning(f"Error reading StreamTV logs: {e}")
        return f"Error reading StreamTV logs: {str(e)}"


def get_plex_logs_context(max_lines: int = 200) -> str:
    """Get recent Plex logs as context for AI troubleshooting"""
    from ..api.logs import get_plex_logs_directory, get_plex_log_files, parse_plex_log_line
    
    try:
        logs_dir = get_plex_logs_directory()
        if not logs_dir:
            return "Plex logs directory not found."
        
        log_files = get_plex_log_files()
        if not log_files:
            return "No Plex log files found."
        
        # Read from most recent log file
        target_file = log_files[0]
        
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            recent_lines = lines[-max_lines:] if len(lines) > max_lines else lines
        
        # Filter for errors and warnings
        error_lines = []
        warning_lines = []
        for line in recent_lines:
            parsed = parse_plex_log_line(line.strip())
            level = parsed.get('level', '').upper()
            if level in ['ERROR', 'FATAL', 'CRITICAL']:
                error_lines.append(line.strip())
            elif level == 'WARN':
                warning_lines.append(line.strip())
        
        # Combine, prioritizing errors
        context_lines = error_lines[-50:] + warning_lines[-30:]
        
        if not context_lines:
            return f"Plex logs: No recent errors or warnings found in {target_file.name}."
        
        return f"Plex Media Server Logs ({target_file.name}, recent errors/warnings):\n" + "\n".join(context_lines[-80:])
    except Exception as e:
        logger.warning(f"Error reading Plex logs: {e}")
        return f"Error reading Plex logs: {str(e)}"


def build_ai_system_prompt() -> str:
    """Build comprehensive system prompt for AI troubleshooting with all context"""
    python_docs = """
Python Documentation References:
- Official Python 3 Documentation: https://docs.python.org/3/
- Python Standard Library: https://docs.python.org/3/library/index.html
- Python Language Reference: https://docs.python.org/3/reference/index.html
- Python GitHub: https://github.com/python

When troubleshooting Python-related issues, refer to these official sources for:
- Syntax errors and language features
- Standard library module usage
- Best practices and coding patterns
- Error handling and exception types
- Type hints and annotations
"""
    
    system_prompt = f"""You are an expert AI troubleshooting assistant for StreamTV, a Python-based IPTV streaming platform.

Your role is to:
1. Analyze errors from StreamTV and Plex Media Server logs
2. Provide clear explanations of what went wrong
3. Suggest specific fixes based on the error context
4. Reference Python documentation when dealing with Python-specific issues
5. Consider the full system context (logs, configuration, environment)

{python_docs}

Data Sources Available:
- StreamTV application logs (errors, warnings, exceptions)
- Plex Media Server logs (playback errors, transcoding issues)
- System configuration and environment

When analyzing issues:
1. Read the error messages carefully from the provided logs
2. Identify the root cause (not just symptoms)
3. Check if it's a Python syntax/runtime error and reference Python docs
4. Consider both StreamTV and Plex logs for related issues
5. Provide step-by-step solutions
6. If Python-related, cite relevant Python documentation sections

Always be specific, actionable, and reference official documentation when appropriate.
"""
    return system_prompt


@router.post("/ollama/query")
async def query_ollama(request: Request):
    """Query Ollama AI with context from StreamTV and Plex logs"""
    # Parse request body
    try:
        body = await request.json()
    except:
        # Fallback to query parameters for compatibility
        body = dict(request.query_params)
    
    query = body.get("query", "")
    model = body.get("model")
    include_streamtv_logs = body.get("include_streamtv_logs", True)
    include_plex_logs = body.get("include_plex_logs", True)
    max_log_lines = int(body.get("max_log_lines", 200))
    
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")
    
    if not check_ollama_installed():
        raise HTTPException(status_code=400, detail="Ollama is not installed. Please install Ollama first.")
    
    # Get installed models
    installed_models = get_installed_ollama_models()
    if not installed_models:
        raise HTTPException(status_code=400, detail="No Ollama models installed. Please install a model first.")
    
    # Use specified model or default to first installed model
    if not model:
        model = installed_models[0]
    elif model not in installed_models:
        raise HTTPException(status_code=404, detail=f"Model {model} is not installed. Available models: {', '.join(installed_models)}")
    
    try:
        # Build context from logs
        context_parts = []
        
        # Add system prompt with Python docs
        context_parts.append(build_ai_system_prompt())
        
        # Add StreamTV logs if requested
        if include_streamtv_logs:
            streamtv_context = get_streamtv_logs_context(max_log_lines)
            context_parts.append(streamtv_context)
        
        # Add Plex logs if requested
        if include_plex_logs:
            plex_context = get_plex_logs_context(max_log_lines)
            context_parts.append(plex_context)
        
        # Combine context
        full_context = "\n\n".join(context_parts)
        
        # Build the prompt for Ollama
        prompt = f"""{full_context}

User Question: {query}

Please analyze the logs and provide a detailed answer with:
1. What the error/issue is
2. Why it's happening (root cause)
3. How to fix it (step-by-step)
4. Relevant Python documentation references if applicable
"""
        
        # Call Ollama API
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                    }
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Ollama API error: {response.status_code} - {response.text}"
                )
            
            result = response.json()
            return {
                "success": True,
                "model": model,
                "response": result.get("response", ""),
                "context_used": {
                    "streamtv_logs": include_streamtv_logs,
                    "plex_logs": include_plex_logs,
                    "log_lines_analyzed": max_log_lines
                }
            }
    
    except httpx.TimeoutException:
        raise HTTPException(status_code=500, detail="Ollama request timed out. The model may be too slow or the query too complex.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Ollama: {str(e)}. Is Ollama running?")
    except Exception as e:
        logger.error(f"Error querying Ollama: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error querying Ollama: {str(e)}")

