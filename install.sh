#!/bin/bash

# Absolute Paths
REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_PATH="$REPO_DIR/venv/bin/activate"
AGENT_PY="$REPO_DIR/agent_simoes.py"
BIN_DIR="$HOME/.local/bin"
TARGET_SCRIPT="$BIN_DIR/agent_simoes"

# Create bin directory if it doesn't exist
mkdir -p "$BIN_DIR"

echo "Installing agent from: $REPO_DIR"

# Create the wrapper content (Use /bin/sh for maximum compatibility)
cat << EOF > "$TARGET_SCRIPT"
#!/bin/sh
# Activate the virtual environment and run the script
. "$VENV_PATH"
exec python3 "$AGENT_PY" "\$@"
EOF

chmod +x "$TARGET_SCRIPT"

# Add to PATH automatically
# Detects which shell the user is using
CURRENT_SHELL=$(basename "$SHELL")
SHELL_RC=""

case "$CURRENT_SHELL" in
    zsh)  SHELL_RC="$HOME/.zshrc" ;;
    bash) SHELL_RC="$HOME/.bashrc" ;;
    *)    SHELL_RC="$HOME/.profile" ;; # Fallback for other shells
esac

# Check if BIN_DIR is already in the system PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "Adicionando $BIN_DIR ao PATH em $SHELL_RC"
    
    # Append the export to the end of the shell config file
    echo "" >> "$SHELL_RC"
    echo "# Agent Simoes Path" >> "$SHELL_RC"
    echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$SHELL_RC"
    
    echo "---"
    echo "IMPORTANT: Run 'source $SHELL_RC' or restart the terminal."
else
    echo "$BIN_DIR is already in your PATH."
fi

echo "Success! The 'agent' command is ready to use."
