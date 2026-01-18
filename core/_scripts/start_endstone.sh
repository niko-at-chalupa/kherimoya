#!/usr/bin/env bash

# ONLY MEANT TO BE USED INTERNALLY!!

set -euo pipefail

python_exec="${1:?python executable required}"
base_path="${2:?base path required}"

unset HISTFILE
HISTCONTROL=ignoreboth

"${python_exec}" -m endstone -y -s "${base_path}/server"
echo __FINISHED__