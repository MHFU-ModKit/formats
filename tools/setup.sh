#!/bin/bash
# MHFU Modding Tools Setup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== MHFU Modding Tools Setup ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# Check Python version
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "ERROR: Python not found. Please install Python 3.x"
    exit 1
fi

$PYTHON --version

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
$PYTHON -m venv "$PROJECT_ROOT/venv"

# Activate venv
source "$PROJECT_ROOT/venv/bin/activate"

# Install requirements
echo ""
echo "Installing Python requirements..."
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

# Install mhef in development mode
echo ""
echo "Installing mhef library..."
cd "$SCRIPT_DIR/mhef"
pip install -e .

# Install mhff in development mode (if setup.py exists)
echo ""
echo "Setting up mhff library..."
cd "$SCRIPT_DIR/mhff"
if [ -f setup.py ]; then
    pip install -e .
else
    echo "Note: mhff doesn't have setup.py, use scripts directly from psp/ folder"
fi

# Check for xdelta3
echo ""
echo "Checking for xdelta3..."
if command -v xdelta3 &> /dev/null; then
    echo "xdelta3 found: $(which xdelta3)"
else
    echo "WARNING: xdelta3 not found. Install via:"
    echo "  macOS: brew install xdelta"
    echo "  Linux: apt install xdelta3"
    echo "  Windows: Download from https://github.com/jmacd/xdelta-gpl/releases"
fi

# Create working directories
echo ""
echo "Creating working directories..."
mkdir -p "$PROJECT_ROOT/workspace/iso"
mkdir -p "$PROJECT_ROOT/workspace/extracted"
mkdir -p "$PROJECT_ROOT/workspace/modified"
mkdir -p "$PROJECT_ROOT/workspace/output"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To activate the environment, run:"
echo "  source $PROJECT_ROOT/venv/bin/activate"
echo ""
echo "Place your MHP2G/MHFU ISO in:"
echo "  $PROJECT_ROOT/workspace/iso/"
echo ""
echo "See CLAUDE.md for next steps."
