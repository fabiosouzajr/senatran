#!/bin/bash
# Bash script to activate the virtual environment
# Run this script from the project root directory

if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Virtual environment activated!"
else
    echo "Error: Virtual environment not found. Run setup.sh first."
    exit 1
fi

