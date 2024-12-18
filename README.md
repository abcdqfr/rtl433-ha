# RTL-433 Home Assistant Integration

A Home Assistant integration for RTL-433 devices, providing direct local connection and management of 433MHz sensors.

## Quick Start

1. Install RTL-SDR and rtl_433:
```bash
sudo apt-get install rtl-sdr librtlsdr-dev rtl-433
```

2. Add the integration to Home Assistant:
   - Copy the `custom_components/rtl433` directory to your Home Assistant configuration directory
   - Restart Home Assistant
   - Add the integration through the UI: Configuration -> Integrations -> Add Integration -> RTL-433

## Features

- 🔌 Direct USB connection to RTL-SDR devices
- 🔍 Automatic device discovery
- 📊 Rich sensor data collection
- 🔋 Battery status monitoring
- 📡 Signal quality tracking
- 🛡️ Robust error handling
- 📝 Detailed logging

## Supported Devices

The integration supports over 200 different device protocols, including:

- Temperature/Humidity Sensors
- Weather Stations
- Rain Gauges
- Wind Sensors
- Pool Thermometers
- Soil Moisture Sensors
- Door/Window Sensors
- And many more...

[View Full Device List](https://triq.org/rtl_433/SUPPORTED_DEVICES.html)

## Configuration

### Basic Configuration
```yaml
# Example configuration.yaml entry
rtl433:
  device_id: 0           # USB device index
  frequency: 433.92M     # Frequency in MHz
  gain: 40              # Gain in dB (or "auto")
  protocol_filter:      # Optional: list of protocol numbers to include
    - 73               # LaCrosse TX141-Bv2
    - 40               # Acurite 592TXR
```

### Advanced Options
```yaml
rtl433:
  device_id: 0
  frequency: 433.92M
  gain: 40
  protocol_filter: [73, 40]
  options:
    convert_units: si          # Use SI units
    report_meta: true          # Include metadata
    signal_quality: true       # Track signal quality
    device_timeout: 3600       # Mark device unavailable after 1 hour
```

## Device Discovery

The integration automatically discovers supported 433MHz devices. Each device is identified by:
- Unique ID: `{model}_{device_id}` (e.g., `LaCrosse-TX141W_377406`)
- Protocol number
- Signal characteristics

### Example Device Data
```json
{
    "time": "2024-12-18T13:35:10",
    "protocol": 73,
    "model": "LaCrosse-TX141W",
    "id": 377406,
    "channel": 0,
    "battery_ok": 1,
    "temperature_C": 19.4,
    "humidity": 24,
    "rssi": -2.217,
    "snr": 32.146
}
```

## Troubleshooting

### Common Issues

1. **Device Not Found**
   ```bash
   # Check USB device
   lsusb | grep RTL
   
   # Test device
   rtl_test -d 0
   ```

2. **Permission Issues**
   ```bash
   # Add user to required groups
   sudo usermod -a -G plugdev,dialout $USER
   
   # Create udev rule (adjust path according to your system)
   # Common locations:
   # - Debian/Ubuntu: /etc/udev/rules.d/
   # - Arch: /usr/lib/udev/rules.d/
   # - Custom: Set UDEV_RULES_DIR environment variable
   
   sudo tee "${UDEV_RULES_DIR:-/etc/udev/rules.d}/rtl-sdr.rules" <<EOF
   SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="plugdev", MODE="0666"
   EOF
   ```

3. **Signal Issues**
   - Check antenna connection
   - Try different gain settings
   - Adjust device position
   - Use `-v` flag for verbose output:
   ```bash
   rtl_433 -d 0 -f 433.92M -g 40 -v
   ```

4. **Protocol Filtering**
   ```bash
   # List all protocols
   rtl_433 -R help
   
   # Enable specific protocols
   rtl_433 -R 73 -R 40
   ```

### Debug Mode

Enable debug logging in Home Assistant:
```yaml
logger:
  default: info
  logs:
    custom_components.rtl433: debug
```

### Signal Quality

Monitor signal quality metrics:
- RSSI (Received Signal Strength Indicator)
- SNR (Signal-to-Noise Ratio)
- Noise floor

Good values:
- RSSI: -60 to 0 dBm
- SNR: > 20 dB
- Noise: < -40 dBm

### Device Timeouts

Devices are marked unavailable after:
- No data received for configured timeout period
- Signal quality below threshold
- Battery status low

## Advanced Usage

### Command Line Testing
```bash
# Basic test with common options
rtl_433 -d 0 -f 433.92M -g 40 -F json -M level -C si

# Debug output
rtl_433 -d 0 -f 433.92M -g 40 -F json -M level -v

# Protocol specific
rtl_433 -d 0 -f 433.92M -g 40 -R 73 -F json
```

### Custom Protocols
```yaml
rtl433:
  device_id: 0
  frequency: 433.92M
  protocols:
    - id: 73
      name: "LaCrosse"
      filter: true
    - id: 40
      name: "Acurite"
      filter: true
```

## Entity Management

### Naming Convention
- Entity ID: `sensor.{model}_{id}_{measurement}`
- Example: `sensor.lacrosse_tx141w_377406_temperature`

### Available Entities
Each device creates multiple entities based on available sensors:
- Temperature (`temperature_C`, `temperature_F`)
- Humidity (`humidity`)
- Battery (`battery_ok`)
- Wind (`wind_speed_kph`, `wind_dir_deg`)
- Signal (`rssi`, `snr`, `noise`)

### Customization
```yaml
# Example customization
homeassistant:
  customize:
    sensor.lacrosse_tx141w_377406_temperature:
      friendly_name: "Outdoor Temperature"
      device_class: temperature
      unit_of_measurement: "°C"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

### Development Setup
```bash
# Clone repository
git clone https://github.com/abcdqfr/rtl433-ha.git
cd rtl433-ha

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/
```

## Support

- [GitHub Issues](https://github.com/abcdqfr/rtl433-ha/issues)
- [Home Assistant Community](https://community.home-assistant.io/tag/rtl433)
- [RTL-433 Documentation](https://triq.org/rtl_433)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
