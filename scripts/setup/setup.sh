#!/bin/bash

set -e

if [ "$(uname -m)" == "aarch64" ]; then
    echo "This script is intended for for x86_64 only! Use setup_arm.sh instead"
    exit 1
fi
if [ "$(uname -m)" != "x86_64" ]; then
    echo "This script is intended for x86_64 only!"
    exit 1
fi

if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "No python interpreter found"
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_DIR" || exit 1

read -r -p "This will set up a Python virtual environment within Kherimoya's root (will delete any directory named venv/ within Kherimoya's root). Continue? (y/n)" choice
if [[ "$choice" != "y" && "$choice" != "Y" ]]; then
    echo "Aborting."
    exit 0
fi

rm -rf venv

# ----- venv setup ----- #
# A venv with native packages, used for Kherimoya itself
# Endstone does NOT need to be installed here, only Kherimoya's *(other)* dependencies
echo "Creating venv..."
$PYTHON_CMD -m venv venv
# shellcheck source=/dev/null
source "venv/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete! Activate the venv with: source venv/bin/activate"