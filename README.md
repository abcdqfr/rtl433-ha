# RTL-433 Home Assistant Integration

A Home Assistant integration for RTL-433 devices, providing direct local connection and management of 433MHz sensors.

## Quick Start

1. Install RTL-SDR and rtl_433:
```bash
sudo apt-get install rtl-sdr librtlsdr-dev rtl-433
```

2. Add the integration to Home Assistant:
   - Copy the `src/custom_components/rtl433` directory to your Home Assistant configuration directory
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

## Project Structure

```
rtl433-ha/
├── src/                    # Source code
│   └── custom_components/  # Home Assistant component
│       └── rtl433/        # RTL-433 integration
├── tests/                  # Test suite
├── docs/                   # Documentation
├── tools/                  # Development tools
└── config/                # Test configuration
```

## Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [API Documentation](docs/API.md)
- [Supported Protocols](docs/PROTOCOLS.md)
- [Contributing](docs/CONTRIBUTING.md)

## Development

Two methods are available for development:

### Method 1: Development Install (Recommended)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
tools/debug.sh
```

### Method 2: Direct Copy
```bash
python -m venv .venv
source .venv/bin/activate
INSTALL_METHOD=copy tools/debug.sh
```

## Support

- [GitHub Issues](https://github.com/abcdqfr/rtl433-ha/issues)
- [Home Assistant Community](https://community.home-assistant.io/tag/rtl433)
- [RTL-433 Documentation](https://triq.org/rtl_433)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
