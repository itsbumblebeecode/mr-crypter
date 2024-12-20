#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
from pathlib import Path
import winreg
import ctypes
from urllib.parse import urlparse

# Define paths
project_dir = Path(__file__).parent.resolve()
venv_dir = project_dir / ".venv"
main_script = project_dir / "main.py"
mr_crypter_script = project_dir / "mr-crypter"
config_dir = Path.home() / ".file_encryptor"
target_dir = Path("/usr/local/bin") if os.name != "nt" else Path(os.getenv("APPDATA")) / "mr-crypter"

GITHUB_REPO = "https://github.com/Marcus-Peterson/mr-crypter.git"

# Function to check Python and pip versions
def check_python_and_pip():
    if sys.version_info < (3, 7):
        print("Python 3.7 or higher is required. Please update Python and try again.")
        sys.exit(1)
    try:
        subprocess.run(["pip", "--version"], check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("pip is not installed. Please install it and try again.")
        sys.exit(1)

# Handle --uninstall option
def uninstall():
    if target_dir.exists():
        print("Uninstalling mr-crypter...")
        if target_dir.is_dir():
            for item in target_dir.iterdir():
                item.unlink()
            target_dir.rmdir()
        elif target_dir.is_file():
            target_dir.unlink()
        shutil.rmtree(venv_dir, ignore_errors=True)
        shutil.rmtree(config_dir, ignore_errors=True)
        print("mr-crypter has been uninstalled.")
        sys.exit(0)

# Check if mr-crypter is already installed and confirm overwrite
def check_existing_installation():
    if (target_dir / "mr-crypter").exists():
        choice = input("mr-crypter is already installed. Do you want to overwrite it? (y/n): ").strip().lower()
        if choice != "y":
            print("Installation aborted.")
            sys.exit(1)

# Create a virtual environment
def create_virtual_environment():
    if not venv_dir.exists():
        print("Creating a virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])

# Install dependencies in the virtual environment
def install_dependencies():
    print("Installing required Python packages...")
    subprocess.check_call([venv_dir / "bin" / "pip" if os.name != "nt" else venv_dir / "Scripts" / "pip", "install", "-r", "requirements.txt"])

# Add shebang line to main.py for virtual environment
def configure_main_script():
    venv_python = venv_dir / "bin" / "python3" if os.name != "nt" else venv_dir / "Scripts" / "python.exe"
    try:
        # Read with UTF-8 encoding
        with main_script.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Write with UTF-8 encoding
        with main_script.open("w", encoding="utf-8") as f:
            if not lines[0].startswith("#!"):
                f.write(f"#!{venv_python}\n")
            f.writelines(lines)
            
        print(f"Successfully configured {main_script}")
    except Exception as e:
        print(f"Error configuring main script: {str(e)}")
        # Fallback to read in binary mode if UTF-8 fails
        try:
            with main_script.open("rb") as f:
                content = f.read()
            with main_script.open("wb") as f:
                if not content.startswith(b"#!"):
                    f.write(f"#!{venv_python}\n".encode())
                f.write(content)
            print("Successfully configured main script using binary mode")
        except Exception as e:
            print(f"Fatal error configuring main script: {str(e)}")
            raise

def create_windows_batch():
    """Create a batch file to run mr-crypter"""
    batch_content = f"""@echo off
"{venv_dir / 'Scripts' / 'python.exe'}" "{target_dir / 'mr-crypter'}" %*
"""
    batch_path = target_dir / "mr-crypter.bat"
    with open(batch_path, "w") as f:
        f.write(batch_content)

# Rename and move main.py to target directory
def rename_and_move_script():
    if mr_crypter_script.exists():
        mr_crypter_script.unlink()
    shutil.copy(main_script, mr_crypter_script)
    mr_crypter_script.chmod(0o755)
    
    if os.name == "nt":
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(mr_crypter_script), str(target_dir / "mr-crypter"))
        create_windows_batch()  # Create the batch file
        add_to_windows_path()
    else:
        try:
            shutil.move(str(mr_crypter_script), str(target_dir))
            print("mr-crypter installed globally in /usr/local/bin.")
        except PermissionError:
            print(f"Permission denied: Could not move to {target_dir}. Run with elevated permissions or move manually.")

def add_to_windows_path():
    """Add the installation directory to Windows PATH."""
    
    try:
        # Open the registry key for environment variables
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
            # Get the current PATH value
            try:
                path_value, _ = winreg.QueryValueEx(key, "PATH")
            except WindowsError:
                path_value = ""
            
            # Check if our directory is already in PATH
            if str(target_dir) not in path_value:
                # Add our directory to PATH
                new_path = f"{path_value};{target_dir}" if path_value else str(target_dir)
                winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
                
                # Notify the system about the change
                HWND_BROADCAST = 0xFFFF
                WM_SETTINGCHANGE = 0x1A
                SMTO_ABORTIFHUNG = 0x0002
                result = ctypes.c_long()
                ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, 
                    "Environment", SMTO_ABORTIFHUNG, 5000, ctypes.byref(result))
                
                print("Added mr-crypter to system PATH.")
                print("Please restart your terminal for the changes to take effect.")
                return True
            return False
    except Exception as e:
        print(f"Warning: Could not add to PATH automatically: {str(e)}")
        print(f"Please add {target_dir} to your PATH manually.")
        return False

def is_git_repo(path: Path) -> bool:
    """Check if directory is a git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError:
        return False

def update_from_github():
    """Update mr-crypter from GitHub."""
    print("Updating mr-crypter...")
    
    try:
        if is_git_repo(project_dir):
            # If it's already a git repo, just pull
            subprocess.run(["git", "pull"], cwd=project_dir, check=True)
        else:
            # Clone fresh
            temp_dir = project_dir.parent / "mr-crypter-temp"
            subprocess.run(["git", "clone", GITHUB_REPO, str(temp_dir)], check=True)
            
            # Copy files from temp to installation directory
            shutil.copytree(temp_dir, project_dir, dirs_exist_ok=True)
            shutil.rmtree(temp_dir)
        
        # Reinstall dependencies
        install_dependencies()
        
        # Reconfigure and move script
        configure_main_script()
        rename_and_move_script()
        
        print("Update completed successfully!")
        print("Please restart your terminal for any PATH changes to take effect.")
        return True
        
    except Exception as e:
        print(f"Error during update: {str(e)}")
        return False

# Main installation process
def main():
    # Check for update option
    if "--update" in sys.argv:
        update_from_github()
        return
        
    # Check for uninstall option
    if "--uninstall" in sys.argv:
        uninstall()
    
    # Check Python and pip versions
    check_python_and_pip()

    # Check if mr-crypter is already installed
    check_existing_installation()

    # Create virtual environment and install dependencies
    create_virtual_environment()
    install_dependencies()

    # Configure main.py to use virtual environment
    configure_main_script()

    # Rename and move script
    rename_and_move_script()

    # Add to Windows PATH
    add_to_windows_path()

    print("Installation complete. You can now use 'mr-crypter' from anywhere.")
    print(f"Virtual environment created at {venv_dir}")

if __name__ == "__main__":
    main()
