#!/bin/bash

# Kill any existing Home Assistant processes
pkill -f "hass" || true

# Kill any existing rtl_433 processes
pkill -f "rtl_433" || true

# Wait for processes to clean up
sleep 2

# Start Home Assistant with debug logging and filter out unwanted messages
hass -c ./config --debug 2>&1 | grep -v -E "bluetooth|dbus|bleak|TypeError|habluetooth"