
#!/usr/bin/env bash

set -euo pipefail

if [[ ! -f ".env" ]]; then
  echo "Missing .env file. Please read the README to set up your API key before running this script."
  exit 1
fi

python cli.py
