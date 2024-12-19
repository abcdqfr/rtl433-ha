#!/bin/bash

# Kill any existing Home Assistant processes
pkill -f "hass" || true

# Kill any existing rtl_433 processes
pkill -f "rtl_433" || true

# Wait for processes to clean up
sleep 2

# Determine installation method
if [ "$INSTALL_METHOD" = "copy" ]; then
    echo "Using direct copy method..."
    # Ensure config directory exists
    mkdir -p config/custom_components

    # Copy current component files to config directory
    echo "Copying component files to config directory..."
    rm -rf config/custom_components/rtl433
    cp -r src/custom_components/rtl433 config/custom_components/
else
    echo "Using development install method..."
    # Create symlink if it doesn't exist
    if [ ! -L "config/custom_components/rtl433" ]; then
        echo "Creating symlink for development..."
        mkdir -p config/custom_components
        rm -rf config/custom_components/rtl433
        ln -sf "$(pwd)/src/custom_components/rtl433" config/custom_components/rtl433
    fi
fi

# Start Home Assistant with debug logging and filter out unwanted messages
echo "Starting Home Assistant..."
PYTHONPATH="${PYTHONPATH}:${PWD}/src" hass -c ./config --debug 2>&1 | grep -v -E "bluetooth|dbus|bleak|TypeError|habluetooth"