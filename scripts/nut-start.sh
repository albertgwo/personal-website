#!/bin/bash

# Start NUT services in proper order
echo "Starting NUT services..."

# Clean up any stale files
rm -f /opt/homebrew/var/state/ups/*

# Start the UPS driver
echo "Starting UPS driver..."
/opt/homebrew/bin/usbhid-ups -a river3plus -u root &
sleep 3

# Start upsd
echo "Starting upsd..."
/opt/homebrew/sbin/upsd -u root &
sleep 2

# Start upsmon
echo "Starting upsmon..."
/opt/homebrew/sbin/upsmon -u root &

echo "NUT services started successfully"
echo "Test with: sudo /opt/homebrew/bin/upsc river3plus@localhost"
