#!/usr/bin/env bash

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_SCRIPT="$APP_DIR/run.sh"
ALIAS_CMD="alias watch=\"$RUN_SCRIPT\""

SHELL_NAME=$(basename "$SHELL")

if [ "$SHELL_NAME" = "zsh" ]; then
    CONFIG_FILE="$HOME/.zshrc"
elif [ "$SHELL_NAME" = "bash" ]; then
    CONFIG_FILE="$HOME/.bashrc"
else
    echo "Could not detect zsh or bash. Defaulting to .bashrc"
    CONFIG_FILE="$HOME/.bashrc"
fi

if grep -q "alias watch=" "$CONFIG_FILE"; then
    echo "Alias 'watch' already exists in $CONFIG_FILE"
else
    echo "" >> "$CONFIG_FILE"
    echo "Vidking CLI Alias" >> "$CONFIG_FILE"
    echo "$ALIAS_CMD" >> "$CONFIG_FILE"
    echo "Added alias to $CONFIG_FILE"
    echo "Please run: source $CONFIG_FILE"
fi
