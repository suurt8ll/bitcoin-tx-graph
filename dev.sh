#!/bin/bash

# Get the directory of the script using realpath
SCRIPT_DIR=$(dirname "$(realpath "$0")")

# Construct the target directory
TARGET_DIR="$SCRIPT_DIR/frontend/"

# Check if the target directory exists
if [ ! -d "$TARGET_DIR" ]; then
  echo "Error: Target directory '$TARGET_DIR' does not exist."
  exit 1
fi

# Change to the target directory
cd "$TARGET_DIR" || { echo "Failed to cd into '$TARGET_DIR'"; exit 1; }

# TODO check if Node version is correct.

# Check if npm install is needed
needs_install=false
if [ ! -d "node_modules" ]; then
  needs_install=true
elif [ -f "package-lock.json" ]; then
  if [[ "package-lock.json" -nt "node_modules" ]]; then
    needs_install=true
  fi
elif [ -f "package.json" ]; then
    if [[ "package.json" -nt "node_modules" ]]; then
        needs_install = true;
    fi
else
  echo "Warning: Neither package.json nor package-lock.json found."
fi

# Run npm install if needed
if $needs_install; then
  echo "Installing dependencies..."
  npm install || { echo "npm install failed"; exit 1; }
  echo "Dependencies installed."
else
  echo "Dependencies are up to date."
fi

# --- tmux logic ---

# Check if tmux is already running
if [ -n "$TMUX" ]; then
    echo "Already inside a tmux session.  Skipping tmux launch."
    exit 0
fi

# Start a new tmux session, detached (-d), with a session name (-s)
tmux new-session -d -s tx_dev

# Rename the first window
tmux rename-window -t tx_dev:0 "backend"

# Send commands to the first window
tmux send-keys -t tx_dev:0 "cd $SCRIPT_DIR/backend" Enter
tmux send-keys -t tx_dev:0 ". .venv/bin/activate" Enter
tmux send-keys -t tx_dev:0 "pip install -r requirements.txt" Enter
tmux send-keys -t tx_dev:0 "cd .." Enter
tmux send-keys -t tx_dev:0 "python -m backend.app.main" Enter

# Create a new window for function_updater.py
tmux new-window -t tx_dev -n "frontend"

# Send commands to the second window
tmux send-keys -t tx_dev:1 "cd $SCRIPT_DIR/frontend" Enter
tmux send-keys -t tx_dev:1 "npm run dev" Enter

# Switch back to the first window (index 0)
tmux select-window -t tx_dev:0

# Enable mouse scrolling.
tmux set-option -g mouse on

# Attach to the tmux session
tmux attach-session -t tx_dev
