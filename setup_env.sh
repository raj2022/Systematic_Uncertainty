#!/usr/bin/env bash
# Sets up a Python virtual environment for Systematic_Uncertainty.
# Run from the repo root: bash setup_env.sh

set -e

python3 -m venv .systematic_uncertainty_env
source .systematic_uncertainty_env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Done. Activate with: source .systematic_uncertainty_env/bin/activate"