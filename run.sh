
#!/usr/bin/env bash

cd "$(dirname "$0")"

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null && python --version 2>&1 | grep -q "Python 3"; then
    PYTHON_CMD="python"
else
    echo "Python 3 is required but not found."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Please install Python 3 via Homebrew: brew install python"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Please install Python 3 via your package manager (e.g., sudo apt install python3)"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
        echo "Please install Python 3 from python.org or via Winget: winget install Python.Python.3"
    else
        echo "Please install Python 3."
    fi
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv .venv
    CREATED_VENV=1
else
    CREATED_VENV=0
fi

if [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Virtual environment not found."
    exit 1
fi

if [ "$CREATED_VENV" -eq 1 ] && [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    python -m pip install -r requirements.txt
fi
set -euo pipefail

if [[ ! -f ".env" ]]; then
  echo "Missing .env file. Please read the README to set up your API key before running this script."
  exit 1
fi

python cli.py
