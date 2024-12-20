#!/bin/bash

# Check for Python 3.7+ and pip
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install it and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(sys.version_info[:2] >= (3, 7))')
if [ "$PYTHON_VERSION" != "True" ]; then
    echo "Python 3.7 or higher is required. Please update Python and try again."
    exit 1
fi

if ! command -v pip &> /dev/null; then
    echo "pip is not installed. Please install it and try again."
    exit 1
fi

# Check for --uninstall option
if [ "$1" == "--uninstall" ]; then
    echo "Uninstalling mr-crypter..."
    sudo rm -f /usr/local/bin/mr-crypter
    rm -rf .venv
    rm -rf ~/.file_encryptor
    echo "mr-crypter has been uninstalled."
    exit 0
fi

# Check if mr-crypter is already installed
if [ -f "/usr/local/bin/mr-crypter" ]; then
    read -p "mr-crypter is already installed. Do you want to overwrite it? (y/n): " choice
    case "$choice" in 
      y|Y ) echo "Overwriting existing mr-crypter...";;
      n|N ) echo "Installation aborted."; exit 1;;
      * ) echo "Invalid choice. Installation aborted."; exit 1;;
    esac
fi

# Define the virtual environment directory
VENV_DIR=".venv"

# Create a virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating a virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate and install dependencies
source "$VENV_DIR/bin/activate"
echo "Installing required Python packages..."
pip install -r requirements.txt

# Configure main script
VENV_PYTHON_PATH="#!$(pwd)/$VENV_DIR/bin/python3"
if ! grep -q "^#!" main.py; then
    sed -i "1i $VENV_PYTHON_PATH" main.py
else
    sed -i "1c $VENV_PYTHON_PATH" main.py
fi

# Make the script executable
echo "Making main.py executable..."
chmod +x main.py

# Rename the script
echo "Renaming main.py to mr-crypter..."
mv main.py mr-crypter

# Move the script to /usr/local/bin
echo "Moving mr-crypter to /usr/local/bin..."
if ! sudo mv mr-crypter /usr/local/bin/; then
    echo "Error: Could not move script to /usr/local/bin/"
    echo "Please run with sudo or move manually"
    exit 1
fi

# Deactivate the virtual environment
deactivate

echo "Installation complete. You can now use 'mr-crypter' from anywhere."
echo "Virtual environment created at $(pwd)/$VENV_DIR"

# Add update functionality
if [ "$1" == "--update" ]; then
    echo "Updating mr-crypter..."
    if [ -d ".git" ]; then
        # If it's a git repo, just pull
        git pull
    else
        # Clone fresh
        TEMP_DIR="../mr-crypter-temp"
        git clone "https://github.com/Marcus-Peterson/mr-crypter.git" "$TEMP_DIR"
        cp -r "$TEMP_DIR"/* .
        rm -rf "$TEMP_DIR"
    fi
    
    # Reinstall dependencies
    source "$VENV_DIR/bin/activate"
    pip install -r requirements.txt
    deactivate
    
    echo "Update completed successfully!"
    echo "Please restart your terminal for any changes to take effect."
    exit 0
fi
