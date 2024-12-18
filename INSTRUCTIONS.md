# RTL-SDR to Home Assistant Integration Project

## Project Goals
1. Create a direct, local connection between RTL-SDR and Home Assistant
2. Focus on simplicity and reliability
3. Support common 433MHz sensors
4. Minimize dependencies
5. Provide clear error feedback

## Architecture Decision

### Option 1: Home Assistant Add-on
**Pros:**
- Containerized environment
- Direct hardware access
- Easier dependency management
- Simpler installation for users
- Built-in supervisor API

**Cons:**
- Less flexible than custom component
- Additional container overhead
- More complex development setup
- Limited integration with HA core features

### Option 2: Custom Component
**Pros:**
- Direct integration with HA
- Native entity management
- Better device/entity handling
- More flexible configuration
- Native service registration

**Cons:**
- Dependency management more complex
- Requires rtl_433 installation on host
- More complex installation for users
- Potential Python version conflicts

### Decision: Custom Component ✅
Reasons:
1. Better integration with HA core features
2. Native entity management more valuable than containerization
3. Direct access to HA's device registry
4. More flexible future expansion
5. Better user experience post-installation

## Implementation Plan

### Phase 1: Core RTL-SDR Integration
1. Basic component structure
   - Manifest
   - Configuration
   - Core classes
   - Constants

2. RTL-SDR Communication
   - rtl_433 process management
   - JSON output parsing
   - Error handling

3. Device Management
   - Sensor creation
   - State updates
   - Device cleanup

### Phase 2: Configuration & Setup
1. Config Flow
   - Device detection
   - Basic settings
   - Validation

2. Options Flow
   - Advanced settings
   - Runtime configuration

3. Documentation
   - Installation guide
   - Configuration guide
   - Troubleshooting

### Phase 3: Error Handling & Recovery
1. Process monitoring
2. Auto-recovery
3. User feedback
4. Logging

## Development Guidelines

### Code Structure
```
custom_components/rtl433/
├── __init__.py          # Component initialization
├── manifest.json        # Component manifest
├── config_flow.py       # Configuration UI
├── const.py            # Constants
├── coordinator.py      # Data coordinator
├── rtl433.py          # RTL433 process manager
├── sensor.py          # Sensor platform
└── translations/      # UI translations
```

### Dependencies
Required:
- rtl_433 (system package)
- rtl-sdr (system package)

Python:
- homeassistant
- voluptuous
- asyncio

### Testing Strategy
1. Manual testing first
2. Integration tests for core paths
3. Unit tests for complex logic
4. Documentation validation

### Error Handling Priority
1. Device connection issues
2. Process crashes
3. Data parsing errors
4. Configuration errors

## Installation Requirements

### System Requirements
- Home Assistant OS or Supervised
- RTL-SDR USB dongle
- System access for rtl_433 installation

### Required Packages
```bash
# Debian/Ubuntu
sudo apt-get update
sudo apt-get install rtl-sdr librtlsdr-dev rtl-433

# HAOS
Connect via SSH/terminal
Use OS agent to install packages
```

### Component Installation
1. Copy to custom_components
2. Restart Home Assistant
3. Add integration via UI

## Configuration

### Basic Configuration
```yaml
# Example configuration.yaml
rtl433:
  device: "0"    # RTL-SDR device index
```

### Advanced Options
```yaml
rtl433:
  device: "0"
  frequency: 433.92M
  gain: 40
  protocol_filter: [1, 2, 3]  # Specific protocols only
```

## Development Process

### Setup Development Environment
1. Clone repository
2. Install development dependencies
3. Set up pre-commit hooks
4. Configure test environment

### Development Workflow
1. Feature branch
2. Implement core functionality
3. Manual testing
4. Add automated tests
5. Documentation
6. PR review

### Release Process
1. Version bump
2. Changelog update
3. Test release
4. Tag and release
5. Update documentation

## Future Considerations
1. Multiple device support
2. Protocol-specific configurations
3. Advanced filtering options
4. Integration with HA device triggers
5. Custom services for device management

## Support & Maintenance
1. Issue templates
2. Debug logging
3. Common issues documentation
4. Update policy
5. Version compatibility matrix 

# RTL-433 Integration Instructions

## Device Behavior Notes

### Normal RTL-433 Operation
- The "[R82XX] PLL not locked!" message is normal and does not indicate a problem
- Device successfully receives data despite this message
- Observed good signal quality (RSSI between -11 and 0 dB, SNR between 21-39 dB)
- Data packets received approximately every 30 seconds
- JSON output includes comprehensive device data:
  - Protocol information
  - Device model and ID
  - Sensor readings (temperature, humidity, wind)
  - Signal quality metrics (RSSI, SNR, noise)
  - Timestamps and message integrity checks

### Integration Design Considerations
1. Don't treat PLL lock warnings as critical errors
2. Maintain device connection even with PLL messages
3. Process both sensor types from same device ID:
   - Temperature/humidity packets
   - Wind speed/direction packets
4. Use signal quality metrics to assess reception quality
5. Implement graceful reconnection if actual errors occur

### Command Line Parameters
```bash
rtl_433 -f 433.92M -g 40 -F json -M level -M time:iso -M protocol -M stats -v -C si
```
- Frequency: 433.92 MHz
- Gain: 40 dB
- Output: JSON format
- Modifiers: Signal level, ISO timestamps, Protocol info, Statistics
- Units: SI (metric)

### Expected Output Format
```json
{
    "time": "ISO timestamp",
    "protocol": "protocol number",
    "model": "device model",
    "id": "device ID",
    "channel": "channel number",
    "battery_ok": "battery status",
    "temperature_C": "temperature in Celsius",
    "humidity": "relative humidity",
    "wind_avg_km_h": "wind speed in km/h",
    "wind_dir_deg": "wind direction in degrees",
    "test": "test flag",
    "mic": "message integrity check",
    "mod": "modulation type",
    "freq": "exact frequency",
    "rssi": "signal strength",
    "snr": "signal-to-noise ratio",
    "noise": "noise floor"
}
```

## Integration Setup
// ... existing setup instructions ...