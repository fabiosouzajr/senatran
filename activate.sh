#!/bin/bash
# Activation script for Senatran automation virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found at $VENV_DIR"
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "Installing dependencies..."
    "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    "$VENV_DIR/bin/playwright" install chromium
    echo "Virtual environment created and dependencies installed!"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo ""
echo "Virtual environment activated!"
echo "Python: $(which python)"
echo "To deactivate, run: deactivate"
echo ""

