#!/bin/bash

# Colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default installation directory
INSTALL_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/code-historian"

# Create installation directory if it doesn't exist
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# Copy the main script
cp code-historian.sh "$INSTALL_DIR/code-historian"
chmod +x "$INSTALL_DIR/code-historian"

# Create default config
cat > "$CONFIG_DIR/config.sh" << 'EOL'
# Code Historian Configuration

# Default directories
HISTORY_DIR=".history"
SOURCE_DIR="src"
OUTPUT_DIR="docs/changes"

# Default file patterns to ignore
IGNORE_PATTERNS=(
    "*/__pycache__/*"
    "*.pyc"
    "*.pyo"
    "*.pyd"
    ".git/*"
    ".venv/*"
)

# Default categories to track
CATEGORIES=(
    "Entity Management"
    "Device Registry"
    "State Updates"
    "Configuration Flow"
    "Platform Setup"
    "Error Handling"
    "Logging"
    "Documentation"
)
EOL

echo -e "${GREEN}Code Historian installed successfully!${NC}"
echo -e "Main script: ${BLUE}$INSTALL_DIR/code-historian${NC}"
echo -e "Config file: ${BLUE}$CONFIG_DIR/config.sh${NC}"
echo
echo "Add this to your .bashrc or .zshrc:"
echo -e "${BLUE}export PATH=\$PATH:$INSTALL_DIR${NC}"
echo
echo "Usage:"
echo "  code-historian --help" 