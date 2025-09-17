# Network UPS Tools Configuration for EcoFlow River 3 Plus

## Summary

This repository contains the complete NUT (Network UPS Tools) configuration for the EcoFlow River 3 Plus UPS on macOS with Homebrew. The configuration was successfully tested and resolves common startup issues by:

- Running services as root to avoid permission problems
- Starting services in the correct order (driver → upsd → upsmon)
- Cleaning up stale socket files automatically
- Using proper EcoFlow vendor/product IDs for USB HID detection

## Quick Setup

1. **Install NUT via Homebrew:**
```bash
brew install nut
```

2. **Clone this repository:**
```bash
git clone https://github.com/albertgwo/Network-UPS-Tools.git
cd Network-UPS-Tools
```

3. **Copy configuration files:**
```bash
sudo cp config/*.conf /opt/homebrew/etc/nut/
sudo cp scripts/nut-start.sh /opt/homebrew/bin/
sudo chmod +x /opt/homebrew/bin/nut-start.sh
```

4. **Set proper permissions:**
```bash
sudo chown root:wheel /opt/homebrew/etc/nut/upsd.users /opt/homebrew/etc/nut/upsmon.conf
sudo chmod 640 /opt/homebrew/etc/nut/upsd.users /opt/homebrew/etc/nut/upsmon.conf
sudo chmod 770 /opt/homebrew/var/state/ups
sudo chgrp wheel /opt/homebrew/var/state/ups
```

5. **Start NUT services:**
```bash
sudo /opt/homebrew/bin/nut-start.sh
```

6. **Test connection:**
```bash
sudo /opt/homebrew/bin/upsc river3plus@localhost
```

## Running NUT

To start NUT services after setup:
```bash
sudo /opt/homebrew/bin/nut-start.sh
```

To test if it's working:
```bash
sudo /opt/homebrew/bin/upsc river3plus@localhost
```

You should see UPS status information including battery level, voltage, and power status.

## Configuration Details

- **UPS**: EcoFlow River 3 Plus (USB HID)
- **Mode**: Network server (netserver)
- **Driver**: usbhid-ups with EcoFlow subdriver
- **Port**: 3493 (standard NUT port)
- **Users**: admin (full access), observer (monitoring only)

## Files Included

- `config/nut.conf` - Main NUT configuration (netserver mode)
- `config/ups.conf` - UPS device configuration with EcoFlow IDs
- `config/upsd.conf` - UPS daemon network configuration
- `config/upsd.users` - User authentication for admin/observer
- `config/upsmon.conf` - UPS monitoring configuration
- `scripts/nut-start.sh` - Service startup script with proper ordering

## Troubleshooting

If services fail to start:
1. **Clean up stale files:** `sudo rm -f /opt/homebrew/var/state/ups/*`
2. **Check USB connection** to EcoFlow device
3. **Restart services:** `sudo /opt/homebrew/bin/nut-start.sh`
4. **Check processes:** `ps aux | grep -E "(usbhid-ups|upsd|upsmon)"`
