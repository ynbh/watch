#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f ".env" ]]; then
  echo "Missing .env file. Please read the README to set up your API key before running this script."
  exit 1
fi

uv run main.py
