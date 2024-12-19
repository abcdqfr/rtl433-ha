# RTL433-HA Development Guide

## Project Architecture

### Core Components

1. **RTL433Coordinator** (`coordinator.py`)
   - Heart of the integration
   - Manages RTL-SDR device communication
   - Handles device discovery and data processing
   - Implements signal quality monitoring
   - Manages process lifecycle and error recovery

### Key Data Structures

```python
# Device Data Format
{
    "unique_id": {  # e.g., "LaCrosse-TX141W_377406"
        "device_info": {
            "identifiers": {(DOMAIN, unique_id)},
            "name": str,
            "manufacturer": str,
            "model": str,
            "via_device": (DOMAIN, device_id)
        },
        "sensor_data": {
            "temperature_C": float,
            "humidity": float,
            "battery_ok": bool,
            "pressure_mbar": float,
            "wind_speed_m_s": float,
            "wind_direction_deg": float,
            "rain_mm": float
        },
        "signal_quality": {
            "rssi": float,  # dBm
            "snr": float,   # dB
            "noise": float, # dBm
            "quality": str  # excellent/good/fair/poor/unusable
        }
    }
}
```

### Signal Quality Thresholds

```python
SIGNAL_EXCELLENT = -10  # dBm
SIGNAL_GOOD = -20      # dBm
SIGNAL_FAIR = -30      # dBm
SIGNAL_POOR = -40      # dBm

SNR_EXCELLENT = 30     # dB
SNR_GOOD = 20         # dB
SNR_FAIR = 10         # dB
SNR_POOR = 5          # dB

NOISE_EXCELLENT = -40  # dBm
NOISE_GOOD = -35      # dBm
NOISE_FAIR = -30      # dBm
NOISE_POOR = -25      # dBm
```

## Process Management

### RTL-433 Process Lifecycle

1. **Initialization**
   ```python
   # Device reset sequence
   rtl_eeprom -d {device_id} -t  # Reset EEPROM
   rtl_test -d {device_id} -t    # Test device
   ```

2. **Process Start**
   ```bash
   rtl_433 -d {device_id} \
           -f {frequency} \
           -g {gain} \
           -F json \
           -M level \
           -C si \
           -M time:iso \
           -M protocol \
           -M stats \
           -v
   ```

3. **Error Recovery**
   - Automatic process restart on failure
   - USB device reset on communication errors
   - Configurable retry attempts and delays

### Critical Sections

1. **Device Initialization**
   - USB device claiming
   - Driver reset sequence
   - Permission handling

2. **Data Processing**
   - JSON parsing and validation
   - Signal quality assessment
   - Device state updates

3. **Process Monitoring**
   - STDERR monitoring for critical errors
   - Process health checks
   - Resource cleanup

## Development Workflow

### Local Development Setup

1. **Environment Setup**
   ```bash
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **RTL-SDR Setup**
   ```bash
   # Install required packages
   sudo apt-get install rtl-sdr librtlsdr-dev rtl-433

   # Add udev rules (adjust path according to your system)
   sudo tee $UDEV_RULES_DIR/rtl-sdr.rules <<EOF
   SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="plugdev", MODE="0666"
   EOF

   # Reload rules
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

### Testing

1. **Test Structure**
   ```
   tests/
   ├── conftest.py           # Pytest fixtures
   ├── test_coordinator.py   # Coordinator tests
   ├── test_init.py         # Integration tests
   └── test_sensor.py       # Sensor entity tests
   ```

2. **Key Test Cases**
   - Device initialization sequence
   - Process management
   - Data parsing and validation
   - Signal quality assessment
   - Error recovery mechanisms
   - Entity state management

### Debugging

1. **Process Debugging**
   ```bash
   # Direct RTL-433 debugging
   rtl_433 -d 0 -f 433.92M -g 40 -v -F json | tee debug.log

   # Monitor USB traffic
   sudo usbmon
   ```

2. **Common Issues**
   - USB device permissions
   - Process zombie states
   - Memory leaks in long-running processes
   - Signal interference patterns

## Development Tools & Scripts

### Debug Script (debug.sh)
```bash
#!/bin/bash
# Location: ./debug.sh
# Purpose: Development environment launcher with debug logging

# Usage:
./debug.sh                    # Basic debug mode
DEBUG_LEVEL=INFO ./debug.sh   # Adjust log level
DEVICE_ID=1 ./debug.sh       # Specify RTL-SDR device

# What it does:
1. Kills existing Home Assistant and rtl_433 processes
2. Waits for cleanup
3. Starts HA with debug logging
4. Filters out noise (bluetooth, dbus messages)
```

### Development Environment Setup

1. **VSCode Configuration**
   ```json
   // .vscode/launch.json
   {
     "version": "0.2.0",
     "configurations": [
       {
         "name": "Home Assistant",
         "type": "python",
         "request": "launch",
         "module": "homeassistant",
         "args": ["-c", "./config", "--debug"],
         "justMyCode": false,
         "env": {
           "PYTHONPATH": "${workspaceFolder}"
         }
       }
     ]
   }
   ```

2. **Pre-commit Hooks**
   ```bash
   # .pre-commit-config.yaml
   repos:
   - repo: https://github.com/pre-commit/pre-commit-hooks
     rev: v4.4.0
     hooks:
     - id: trailing-whitespace
     - id: end-of-file-fixer
     - id: check-yaml
     - id: check-json
   - repo: https://github.com/psf/black
     rev: 23.3.0
     hooks:
     - id: black
   - repo: https://github.com/charliermarsh/ruff-pre-commit
     rev: v0.0.261
     hooks:
     - id: ruff
   ```

### Development Commands

```bash
# Start development environment
./debug.sh

# Run tests with coverage
pytest tests/ --cov=custom_components.rtl433 --cov-report=xml

# Run specific test file
pytest tests/test_coordinator.py -v

# Run tests matching pattern
pytest -k "test_signal_quality" -v

# Generate coverage report
coverage html

# Lint code
ruff check custom_components/rtl433/
black custom_components/rtl433/

# Type checking
mypy custom_components/rtl433/
```

## Advanced Debugging Techniques

### RTL-SDR Debugging

1. **Device Information**
   ```bash
   # List USB devices
   lsusb | grep RTL
   
   # Get detailed device info
   rtl_eeprom -d 0
   
   # Test device with various gain settings
   for gain in 0 20 40 60; do
     echo "Testing gain: $gain"
     rtl_test -d 0 -g $gain
   done
   ```

2. **Signal Analysis**
   ```bash
   # Raw signal capture
   rtl_sdr -d 0 -f 433.92M -s 2048000 -g 40 -n 8192000 signal.bin
   
   # Analyze with rtl_433
   rtl_433 -r signal.bin -A
   
   # Continuous monitoring with stats
   rtl_433 -d 0 -f 433.92M -g 40 -S all -M level
   ```

3. **Protocol Analysis**
   ```bash
   # Monitor specific protocol
   rtl_433 -d 0 -R 73 -M level -M stats
   
   # Analyze all protocols
   rtl_433 -d 0 -G -M level
   
   # Save raw data for analysis
   rtl_433 -d 0 -w data.cu8
   ```

### Python Debugging

1. **Interactive Debugging**
   ```python
   # Add breakpoint in code
   import pdb; pdb.set_trace()
   
   # Or use breakpoint() function
   breakpoint()
   ```

2. **Logging Setup**
   ```python
   # In coordinator.py
   import logging
   _LOGGER = logging.getLogger(__name__)
   
   # Debug decorator
   def debug_call(func):
       def wrapper(*args, **kwargs):
           _LOGGER.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
           result = func(*args, **kwargs)
           _LOGGER.debug(f"{func.__name__} returned {result}")
           return result
       return wrapper
   ```

3. **Memory Profiling**
   ```python
   # Install memory_profiler
   pip install memory_profiler
   
   # Add decorator to function
   from memory_profiler import profile
   
   @profile
   def memory_intensive_function():
       pass
   ```

### Process Monitoring

1. **RTL-433 Process**
   ```bash
   # Monitor process
   ps aux | grep rtl_433
   
   # Check resource usage
   top -p $(pgrep rtl_433)
   
   # Monitor file descriptors
   lsof -p $(pgrep rtl_433)
   ```

2. **USB Monitoring**
   ```bash
   # Monitor USB events
   sudo udevadm monitor --udev --property
   
   # Check USB bandwidth
   cat /sys/kernel/debug/usb/devices
   
   # Monitor USB errors
   dmesg | grep -i usb
   ```

### Network Analysis

1. **Signal Quality**
   ```bash
   # Monitor signal strength
   rtl_433 -d 0 -M level -M stats | grep "RSSI"
   
   # Track packet loss
   rtl_433 -d 0 -M stats | grep "packets"
   ```

2. **Interference Detection**
   ```bash
   # Scan for interference
   rtl_power -f 433M:434M:8k -g 40 -i 1s -e 1h power.csv
   
   # Monitor noise floor
   rtl_433 -d 0 -M level | grep "noise"
   ```

## Development Workflows

### Feature Development

1. **New Feature Workflow**
   ```bash
   # Create feature branch
   git checkout -b feature/new-feature
   
   # Start development environment
   ./debug.sh
   
   # Run tests continuously
   ptw tests/
   
   # Check coverage
   pytest --cov=custom_components.rtl433 tests/
   ```

2. **Testing Workflow**
   ```bash
   # Create test file
   touch tests/test_new_feature.py
   
   # Run specific test with debug
   pytest tests/test_new_feature.py -v --pdb
   
   # Check test coverage
   pytest --cov=custom_components.rtl433 tests/test_new_feature.py --cov-report=term-missing
   ```

### Debugging Workflow

1. **Issue Investigation**
   ```bash
   # Enable debug logging
   echo "custom_components.rtl433: debug" >> config/custom_components/logger.yaml
   
   # Start with verbose output
   DEBUG=1 ./debug.sh
   
   # Monitor logs
   tail -f home-assistant.log | grep rtl433
   ```

2. **Performance Analysis**
   ```bash
   # Profile code
   python -m cProfile -o profile.stats coordinator.py
   
   # Analyze results
   python -m pstats profile.stats
   
   # Memory usage
   mprof run coordinator.py
   mprof plot
   ```

### Release Workflow

1. **Pre-release Checks**
   ```bash
   # Run all tests
   pytest tests/
   
   # Check coverage
   pytest --cov=custom_components.rtl433 tests/ --cov-report=xml
   
   # Lint code
   ruff check custom_components/rtl433/
   black --check custom_components/rtl433/
   
   # Type check
   mypy custom_components/rtl433/
   ```

2. **Release Process**
   ```bash
   # Update version
   bump2version patch  # or minor/major
   
   # Generate changelog
   git-changelog .
   
   # Create release
   gh release create v1.0.0 -t "Release v1.0.0" -n "Release notes..."
   ```

## Common Development Tasks

### Adding New Device Support

1. **Protocol Analysis**
   ```bash
   # Capture device data
   rtl_433 -d 0 -F json -M level > device_data.json
   
   # Analyze protocol
   rtl_433 -d 0 -G -A
   ```

2. **Implementation Steps**
   - Add protocol to `const.py`
   - Create device-specific parser
   - Add test data
   - Update documentation

### Signal Quality Improvements

1. **Data Collection**
   ```bash
   # Collect signal data
   rtl_433 -d 0 -M level -M stats > signal_data.log
   
   # Analyze patterns
   awk '/RSSI/ {print $0}' signal_data.log | sort -n
   ```

2. **Implementation**
   - Update thresholds in `const.py`
   - Add signal quality tracking
   - Implement quality-based filtering

### Performance Optimization

1. **Profiling**
   ```bash
   # CPU profiling
   python -m cProfile -o profile.stats coordinator.py
   
   # Memory profiling
   mprof run coordinator.py
   
   # Analyze results
   snakeviz profile.stats
   ```

2. **Optimization Areas**
   - Process management
   - Data parsing
   - State updates
   - Memory usage
   - Error handling

## Future Development

### Planned Features

1. **Enhanced Signal Processing**
   - Advanced noise filtering
   - Automatic frequency scanning
   - Multi-device support

2. **Device Management**
   - Dynamic protocol loading
   - Custom protocol support
   - Device grouping

3. **Performance Optimization**
   - Memory usage reduction
   - Process monitoring improvements
   - Signal quality algorithms

### Known Limitations

1. **Hardware**
   - Single device support
   - Fixed gain settings
   - USB bandwidth constraints

2. **Software**
   - Process restart overhead
   - Memory usage in long runs
   - Limited protocol customization

3. **Integration**
   - Manual protocol filtering
   - Basic signal processing
   - Limited device configuration

## Development Environment Setup

### Method 1: Development Install (Recommended)
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Start Home Assistant with debug logging
./debug.sh
```

### Method 2: Direct Copy (Alternative)
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# The debug.sh script will:
# 1. Copy component files to config/custom_components/
# 2. Start Home Assistant with debug logging
./debug.sh
```

### Why Two Methods?

1. **Development Install (`pip install -e .`)**
   - Creates proper Python package installation
   - Automatically handles Python path
   - Better for IDE integration
   - Standard Python development practice
   - Easier dependency management
   - Works with multiple HA instances

2. **Direct Copy**
   - Simpler to understand
   - Mirrors real-world manual installation
   - Good for testing installation procedures
   - Useful for final integration testing

Choose the method that best suits your workflow. The development install is recommended for active development, while the direct copy method is useful for installation testing.