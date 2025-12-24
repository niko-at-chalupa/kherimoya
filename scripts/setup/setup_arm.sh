#!/bin/bash

if [ "$(uname -m)" != "aarch64" ]; then

    echo "This script is intended for aarch64 only!" # only tested on aarch64, if you want to try on other archs, feel free to modify
    exit 1
fi

echo "This script is under development!"
exit 1

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

read -r -p "This will set up an ARM development environment with an x64 emulation layer. This will also delete any directories called 'venv' and 'x64_env' within Kherimoya's root. Continue? (y/n) " choice
if [[ "$choice" != "y" && "$choice" != "Y" ]]; then
    echo "Aborting."
    exit 0
fi

rm -rf venv x64_env

# ----- ARM venv setup ----- #
# A venv with native ARM packages, used for Kherimoya itself
# Endstone does NOT need to be installed here, only Kherimoya's *(other)* dependencies
echo "Creating ARM venv..."
$PYTHON_CMD -m venv venv
# shellcheck source=/dev/null
source "venv/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# ----- qemu-user setup ----- #
echo "Installing qemu-user for ARM->x64 emulation..."
if command -v apt &> /dev/null; then
    sudo apt update && sudo apt install -y qemu-user
elif command -v dnf &> /dev/null; then
    sudo dnf install -y qemu-user
else
    echo "Please install qemu-user manually, and return"
    exit 1
fi

# ----- x64 env setup ----- #


mkdir -p x64_env # x64_env only exists on aarch64 setups
echo "Setting up x64 environment..."

# TODO: make it get the x64 python

chmod +x ./python

# create the x64 venv under qemu
qemu-x86_64 ./python -m venv x64_venv

# upgrade pip and install endstone inside x64 venv
qemu-x86_64 x64_venv/bin/python -m pip install --upgrade pip
qemu-x86_64 x64_venv/bin/python -m pip install endstone