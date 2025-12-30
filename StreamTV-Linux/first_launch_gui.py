#!/usr/bin/env python3
"""
First Launch GUI for StreamTV Linux
Handles dependency extraction and setup on first launch
"""

import os
import sys
import shutil
import json
import subprocess
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    # Try GTK as fallback
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, GLib
        GTK_AVAILABLE = True
        TKINTER_AVAILABLE = False
    except ImportError:
        print("Neither tkinter nor GTK available. Please install python3-tk or python3-gi.")
        sys.exit(1)
else:
    TKINTER_AVAILABLE = True
    GTK_AVAILABLE = False


if TKINTER_AVAILABLE:
    class FirstLaunchGUI:
        def __init__(self, root):
            self.root = root
            self.root.title("StreamTV Setup")
            self.root.geometry("600x500")
            self.root.resizable(False, False)
            
            # State variables
            self.python_installed = False
            self.ffmpeg_installed = False
            self.extracting = False
            self.extraction_progress = 0.0
            
            # Paths
            self.app_dir = Path(__file__).parent.resolve()
            self.bundled_dir = self.app_dir / "bundled"
            self.app_support = Path.home() / ".streamtv"
            self.app_support.mkdir(exist_ok=True)
            
            self.setup_ui()
            self.check_dependencies()
        
        def setup_ui(self):
            # Title
            title_frame = tk.Frame(self.root)
            title_frame.pack(pady=20)
            
            title_label = tk.Label(
                title_frame,
                text="StreamTV Setup",
                font=("Arial", 24, "bold")
            )
            title_label.pack()
            
            subtitle_label = tk.Label(
                title_frame,
                text="StreamTV requires the following dependencies:",
                font=("Arial", 12)
            )
            subtitle_label.pack(pady=(10, 0))
            
            # Dependencies frame
            deps_frame = tk.Frame(self.root)
            deps_frame.pack(pady=20, padx=30, fill=tk.BOTH, expand=True)
            
            # Python status
            self.python_frame = tk.Frame(deps_frame)
            self.python_frame.pack(fill=tk.X, pady=5)
            
            self.python_status = tk.Label(
                self.python_frame,
                text="❌",
                font=("Arial", 16)
            )
            self.python_status.pack(side=tk.LEFT, padx=10)
            
            self.python_label = tk.Label(
                self.python_frame,
                text="Python 3.10+",
                font=("Arial", 11)
            )
            self.python_label.pack(side=tk.LEFT)
            
            # FFmpeg status
            self.ffmpeg_frame = tk.Frame(deps_frame)
            self.ffmpeg_frame.pack(fill=tk.X, pady=5)
            
            self.ffmpeg_status = tk.Label(
                self.ffmpeg_frame,
                text="❌",
                font=("Arial", 16)
            )
            self.ffmpeg_status.pack(side=tk.LEFT, padx=10)
            
            self.ffmpeg_label = tk.Label(
                self.ffmpeg_frame,
                text="FFmpeg 7.1.1+",
                font=("Arial", 11)
            )
            self.ffmpeg_label.pack(side=tk.LEFT)
            
            # Progress bar
            self.progress_frame = tk.Frame(self.root)
            self.progress_frame.pack(pady=10, padx=30, fill=tk.X)
            
            self.progress_var = tk.DoubleVar()
            self.progress_bar = ttk.Progressbar(
                self.progress_frame,
                variable=self.progress_var,
                maximum=100,
                length=400
            )
            self.progress_bar.pack(fill=tk.X)
            
            self.status_label = tk.Label(
                self.progress_frame,
                text="",
                font=("Arial", 9),
                fg="gray"
            )
            self.status_label.pack(pady=(5, 0))
            
            # Buttons
            button_frame = tk.Frame(self.root)
            button_frame.pack(pady=20)
            
            self.cancel_button = tk.Button(
                button_frame,
                text="Cancel",
                command=self.cancel,
                width=12
            )
            self.cancel_button.pack(side=tk.LEFT, padx=5)
            
            self.continue_button = tk.Button(
                button_frame,
                text="Continue",
                command=self.continue_setup,
                width=12,
                state=tk.DISABLED
            )
            self.continue_button.pack(side=tk.LEFT, padx=5)
        
        def check_dependencies(self):
            """Check for Python and FFmpeg dependencies"""
            # Check Python
            python_path = self.check_python()
            if python_path:
                self.python_installed = True
                self.python_status.config(text="✅")
                self.python_label.config(text=f"Python 3.10+ ({python_path})")
            else:
                # Try to extract bundled Python
                if (self.bundled_dir / "python" / "python3").exists():
                    self.extract_python()
                else:
                    self.status_label.config(
                        text="Python not found. Please install Python 3.10+",
                        fg="red"
                    )
            
            # Check FFmpeg
            ffmpeg_path = self.check_ffmpeg()
            if ffmpeg_path:
                self.ffmpeg_installed = True
                self.ffmpeg_status.config(text="✅")
                self.ffmpeg_label.config(text=f"FFmpeg 7.1.1+ ({ffmpeg_path})")
            else:
                # Try to extract bundled FFmpeg
                if (self.bundled_dir / "ffmpeg" / "ffmpeg").exists():
                    self.extract_ffmpeg()
                else:
                    self.status_label.config(
                        text="FFmpeg not found. Please install FFmpeg 7.1.1+",
                        fg="red"
                    )
            
            self.update_continue_button()
        
        def check_python(self):
            """Check if Python is installed"""
            try:
                result = subprocess.run(
                    ["python3", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version = result.stdout.strip()
                    # Check if version is 3.10+
                    version_parts = version.split()[1].split(".")
                    if int(version_parts[0]) >= 3 and int(version_parts[1]) >= 10:
                        return shutil.which("python3")
            except Exception:
                pass
            
            # Check bundled Python
            bundled_python = self.app_support / "python" / "python3"
            if bundled_python.exists():
                return str(bundled_python)
            
            return None
        
        def check_ffmpeg(self):
            """Check if FFmpeg is installed"""
            try:
                result = subprocess.run(
                    ["ffmpeg", "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Check version (minimum 7.1.1)
                    version_line = result.stdout.split("\n")[0]
                    if "ffmpeg version" in version_line:
                        version_str = version_line.split("ffmpeg version")[1].strip().split()[0]
                        if self.compare_version(version_str, "7.1.1"):
                            return shutil.which("ffmpeg")
            except Exception:
                pass
            
            # Check bundled FFmpeg
            bundled_ffmpeg = self.app_support / "ffmpeg" / "ffmpeg"
            if bundled_ffmpeg.exists():
                return str(bundled_ffmpeg)
            
            return None
        
        def compare_version(self, version1, version2):
            """Compare version strings (returns True if version1 >= version2)"""
            v1_parts = [int(x) for x in version1.split(".")]
            v2_parts = [int(x) for x in version2.split(".")]
            
            for i in range(max(len(v1_parts), len(v2_parts))):
                v1_val = v1_parts[i] if i < len(v1_parts) else 0
                v2_val = v2_parts[i] if i < len(v2_parts) else 0
                
                if v1_val > v2_val:
                    return True
                elif v1_val < v2_val:
                    return False
            
            return True  # Equal
        
        def extract_python(self):
            """Extract bundled Python"""
            if self.extracting:
                return
            
            self.extracting = True
            self.status_label.config(text="Extracting Python...", fg="blue")
            self.progress_var.set(20)
            self.root.update()
            
            try:
                bundled_python_dir = self.bundled_dir / "python"
                extracted_python_dir = self.app_support / "python"
                
                if extracted_python_dir.exists():
                    shutil.rmtree(extracted_python_dir)
                
                shutil.copytree(bundled_python_dir, extracted_python_dir)
                
                # Make executable
                python_bin = extracted_python_dir / "python3"
                if python_bin.exists():
                    os.chmod(python_bin, 0o755)
                    
                    # Store path
                    with open(self.app_support / "python_path.json", "w") as f:
                        json.dump({"path": str(python_bin)}, f)
                    
                    self.python_installed = True
                    self.python_status.config(text="✅")
                    self.python_label.config(text=f"Python (Bundled: {python_bin})")
                    self.status_label.config(text="Python extracted successfully", fg="green")
            except Exception as e:
                self.status_label.config(text=f"Failed to extract Python: {e}", fg="red")
                messagebox.showerror("Error", f"Failed to extract Python: {e}")
            finally:
                self.extracting = False
                self.progress_var.set(50)
                self.update_continue_button()
        
        def extract_ffmpeg(self):
            """Extract bundled FFmpeg"""
            if self.extracting:
                return
            
            self.extracting = True
            self.status_label.config(text="Extracting FFmpeg...", fg="blue")
            self.progress_var.set(60)
            self.root.update()
            
            try:
                bundled_ffmpeg_dir = self.bundled_dir / "ffmpeg"
                extracted_ffmpeg_dir = self.app_support / "ffmpeg"
                
                if extracted_ffmpeg_dir.exists():
                    shutil.rmtree(extracted_ffmpeg_dir)
                
                extracted_ffmpeg_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy ffmpeg
                ffmpeg_bin = bundled_ffmpeg_dir / "ffmpeg"
                if ffmpeg_bin.exists():
                    shutil.copy2(ffmpeg_bin, extracted_ffmpeg_dir / "ffmpeg")
                    os.chmod(extracted_ffmpeg_dir / "ffmpeg", 0o755)
                
                # Copy ffprobe
                ffprobe_bin = bundled_ffmpeg_dir / "ffprobe"
                if ffprobe_bin.exists():
                    shutil.copy2(ffprobe_bin, extracted_ffmpeg_dir / "ffprobe")
                    os.chmod(extracted_ffmpeg_dir / "ffprobe", 0o755)
                
                # Store path
                extracted_ffmpeg = extracted_ffmpeg_dir / "ffmpeg"
                if extracted_ffmpeg.exists():
                    with open(self.app_support / "ffmpeg_path.json", "w") as f:
                        json.dump({"path": str(extracted_ffmpeg)}, f)
                    
                    self.ffmpeg_installed = True
                    self.ffmpeg_status.config(text="✅")
                    self.ffmpeg_label.config(text=f"FFmpeg (Bundled: {extracted_ffmpeg})")
                    self.status_label.config(text="FFmpeg extracted successfully", fg="green")
            except Exception as e:
                self.status_label.config(text=f"Failed to extract FFmpeg: {e}", fg="red")
                messagebox.showerror("Error", f"Failed to extract FFmpeg: {e}")
            finally:
                self.extracting = False
                self.progress_var.set(100)
                self.update_continue_button()
        
        def update_continue_button(self):
            """Update continue button state"""
            if self.python_installed and self.ffmpeg_installed and not self.extracting:
                self.continue_button.config(state=tk.NORMAL)
            else:
                self.continue_button.config(state=tk.DISABLED)
        
        def continue_setup(self):
            """Continue with setup"""
            self.root.destroy()
        
        def cancel(self):
            """Cancel setup"""
            if messagebox.askyesno("Cancel Setup", "Are you sure you want to cancel?"):
                self.root.destroy()
                sys.exit(0)


def main():
    if TKINTER_AVAILABLE:
        root = tk.Tk()
        app = FirstLaunchGUI(root)
        root.mainloop()
    else:
        print("GTK implementation not yet available. Please install python3-tk.")
        sys.exit(1)


if __name__ == "__main__":
    main()

